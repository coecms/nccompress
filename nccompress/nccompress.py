#!/usr/bin/env python

"""
Copyright 2015 ARC Centre of Excellence for Climate Systems Science

author: Aidan Heerdegen <aidan.heerdegen@anu.edu.au>

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import subprocess
import os
import sys
import netCDF4 as nc
import argparse
import re
from warnings import warn
from shutil import move, which
from collections import defaultdict
import math
import operator
import numpy as np
import numpy.ma as ma
import multiprocessing as mp

if (sys.version_info > (3, 0)):
     # Python 3 code in this block
     netcdf4exception = OSError
else:
     # Python 2 code in this block
     netcdf4exception = IOError

# A couple of hard-wired executable paths that might need changing

# Need to use system time command explicitly, otherwise get crippled bash version
timecmd='/usr/bin/time'
nccopy='nccopy'
nc2nc='nc2nc'
cdocmd='cdo'

cdofound = None

result_list=[]
    
def is_netCDF(ncfile):
    """ Test to see if ncfile is a valid netCDF file
    """
    try:
        tmp = nc.Dataset(ncfile)
        format = tmp.file_format
        compressed = is_compressed(tmp)
        # No need to close, is done in is_compressed
        return (format, compressed)
    except netcdf4exception:
        return (False, None)

def is_compressed(ncfile):
    """ Test if netcdfile is compressed
    """
    if type(ncfile).__name__ == 'Dataset':
        tmp = ncfile
    else:
        tmp = nc.Dataset(ncfile)
    compressed=False
    # netCDF3 files have no filters attribute, and no compression
    # should use data_model instead of file_format in future
    if not tmp.file_format.startswith("NETCDF3"):
        for varname in tmp.variables:
            hdf5_filters = tmp.variables[varname].filters()
            if hdf5_filters['complevel'] > 0:
                compressed = True
                break
        tmp.close()

    return compressed
        
def are_equal(infile,outfile,verbose):
    """ Run cdo diffn on the input and output netCDF files to ensure
        they are identical
    """
    global cdofound
    
    if cdofound is None:
        # None if executable not found
        exepath = which(cdocmd)
        if exepath is None:
            cdofound = False
        else:
            cdofound = True

    if cdofound:
        cmd = [cdocmd,'diffn']
        cmd.append(infile)
        cmd.append(outfile)
        if verbose: print (' '.join(cmd))
        output = ''
        try:
            output = subprocess.check_output(cmd,stderr=subprocess.STDOUT)
        except Exception as e:
            if verbose: print("Problem comparing two netCDF files: {}\n Exception: {}".format(" ".join(cmd), e.output))
            return False
        return True
    else:
        print("cdo not found in PATH. File checks and paranoid mode disabled")
        return None

def nc2nc_cmd(infile,outfile,level,shuffle,verbose,chunksize,buffersize,timing):

    cmd = []
    if timing:
        # The format string for the time command
        #   %e     (Not in tcsh.) Elapsed real time (in seconds).
        #   %S     Total number of CPU-seconds that the process spent in kernel mode.
        #   %U     Total number of CPU-seconds that the process spent in user mode.
        #   %M     Maximum resident set size of the process during its lifetime, in Kbytes.
        fmt = "%e %S %U %M"
        cmd.extend([timecmd,'-f',fmt])
    cmd.extend([nc2nc,'-d',str(level)])
    if (not shuffle): cmd.append('-n')
    # if verbose: cmd.append('-v')
    if chunksize:
        cmd.append('-s')
        # All command line options have to be a string
        cmd.append(str(chunksize))
    if buffersize:
        cmd.append('-b')
        # All command line options have to be a string
        cmd.append(str(buffersize))
    cmd.append(infile)
    cmd.append(outfile)

    return cmd

def nccopy_cmd(infile,outfile,level,shuffle,verbose,buffersize,timing):

    cmd = []
    if timing:
        # The format string for the time command
        #   %e     (Not in tcsh.) Elapsed real time (in seconds).
        #   %S     Total number of CPU-seconds that the process spent in kernel mode.
        #   %U     Total number of CPU-seconds that the process spent in user mode.
        #   %M     Maximum resident set size of the process during its lifetime, in Kbytes.
        fmt = "%e %S %U %M"
        cmd.extend([timecmd,'-f',fmt])
    cmd.extend([nccopy,'-d',str(level)])
    if shuffle: cmd.append('-s')
    if buffersize:
        cmd.append('-m')
        cmd.append(str(buffersize*1000000))
    cmd.append(infile)
    cmd.append(outfile)

    return cmd

def check_and_overwrite(state,verbose,maxcompress):

    # Serious. We're going to blow away the original file with
    # the compressed version -- do some sanity checks to make
    # sure we're not copying rubbish over our data
    if ( maxcompress != 0 and state['orig_size'] > maxcompress*state['comp_size'] ):
        # If the compressed version is less than 1/maxcompress we will
        # warn and not overwrite the original
        if (verbose):
            print("Compression ratio {0}, is greater than max compress ratio {1}: {2} not overwritten. Use -m option to change max compress ratio".format(state['orig_size']/state['comp_size'],maxcompress,state['infile']))
        state['error'] = "Max compress exceeded: {0}".format(state['orig_size']/state['comp_size'])
    else:
        # Overwrite original with compressed version
        if verbose: print("Overwriting {0}".format(state['infile']))
        try:
            move(state['outfile'],state['infile'])
        except Exception as e:
            state['error'] = "Failed to overwrite original file"
        else:
            state['error'] = False

def run_compress(infile,outfile,level=5,shuffle=True,verbose=False,chunksize=64,buffersize=500,paranoid=False,
                 overwrite=False,nccopy=False,maxcompress=10,timing=False):

    # Initialise state container
    state = {
        'infile' : infile, 
        'outfile' : outfile, 
        'times' : [-1,-1,-1,-1], 
        'orig_size' : os.path.getsize(infile), 
        'dlevel' : level, 
        'shuffle' : shuffle, 
        'paranoid' : paranoid,
        'overwrite' : overwrite,
        'error' : False,
    } 

    # Check to see if the output file already exists ...
    if os.path.isfile(outfile):
        # Ok, we're going to be paranoid here, because this could be a left over
        # half compressed file from a previous run. We do not want to copy that
        # over our data

        # Note to self: might need to wrap this in a try/except block for debugging
        identical_files = are_equal(infile, outfile, verbose)

        if identical_files:
            if verbose: sys.stdout.write("Output file %s exists: skipping\n" % outfile)
            state['output'] = "Output file {} exists: skipping".format(outfile)
            state['comp_size'] = os.path.getsize(outfile);
            if overwrite:
                # Perform checks on compressed data, return result in state. Need to make
                # this into an object ...
                check_and_overwrite(state,verbose,maxcompress)
            return state
        else:
            if identical_files is None:
                sys.stdout.write("Output file %s exists, but cannot determine if it is same as the input %s\n" % (outfile,infile))
            else:
                sys.stdout.write("Output file %s exists, but is not the same as the input %s\n" % (outfile,infile))
            sys.stdout.write("Deleting output and recompressing\n")
            # Delete compressed file, will continue and compress afresh
            os.unlink(outfile)

    if nccopy:
        cmd = nccopy_cmd(infile,outfile,level,shuffle,verbose,buffersize,timing)
    else:
        cmd = nc2nc_cmd(infile,outfile,level,shuffle,verbose,chunksize,buffersize,timing)

    output = ''
    if verbose: print (' '.join(cmd))
    try:
        output = subprocess.check_output(cmd,stderr=subprocess.STDOUT)
    except Exception as e:
        state['error'] = "Compression failed: " + str(e)
    else:
        state['times'] =  output.split()
        state['comp_size'] = os.path.getsize(outfile)
        if paranoid and not are_equal(infile,outfile,verbose):
            sys.stdout.write("%s is not the same as %s \n" % (infile,outfile))
            state['error'] = "Compressed file is not the same as original"
        elif overwrite:
            # Perform checks on compressed data, return result in state. Need to make
            # this into an object ...
            check_and_overwrite(state,verbose,maxcompress)

    return state

def log_result(result):
    # Not strictly required, but makes it explicit
    global result_list
    result_list.append(result)

def compress_files(path, files, tmpdir, overwrite, maxcompress, level, shuffle, force, clean, 
                   verbose, chunksize, buffersize, nccopy, paranoid, numproc, timing):

    total_size_new = 0
    total_size_old = 0
    total_files = 0
    skippedlist = []
    jobs = []

    global result_list
    result_list[:] = []

    pool = mp.Pool(processes=numproc,maxtasksperchild=50)

    # Create our temporary directory
    outdir = os.path.join(path,tmpdir)
    if not os.path.isdir(outdir):
        # Don't try and catch errors, let program stop if there is a problem
        os.mkdir(outdir)

    if clean:
        # Choose to clean all the files out of the tmp directory. We could
        # just delete them if we check to see if the output files exists
        # below, but this will only delete the files it is trying to compress.
        # If the program is called with a different list of files there may
        # be left over cruft and the directory won't be removed later. We need
        # a clean (ha ha) way for the user to sure all temporary files have
        # been removed.
        for file in os.listdir(outdir):
            file_path = os.path.join(outdir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)

    for file in files:

        infile = os.path.join(path,file)
        outfile = os.path.join(outdir,file)

        # Make sure we're dealing with a netCDF file
        (ncformat, compressed) = is_netCDF(infile)
        if ncformat:
            if ncformat == 'NETCDF4' and not nccopy:
                sys.stderr.write("Cannot compress {} with nc2nc as it is NETCDF4 format, switching to nccopy\n".format(infile))
                nccopy = True
            if verbose: sys.stdout.write( "Compressing %s, deflate level = %s, shuffle is on: %s\n" % (infile,level,shuffle) )
        else:
            if verbose: print('Not a netCDF file: ' + infile)
            continue

        # Check to see if the input file is already compressed
        if compressed:
            if force:
                if verbose: sys.stdout.write("Already compressed %s but forcing overwrite\n" % infile)
            else:
                if verbose: print('Already compressed skipping ...')
                continue

        # Try compressing the data
        pool.apply_async(run_compress, args=(infile,outfile,level,shuffle,verbose,chunksize,buffersize,paranoid,overwrite,nccopy,maxcompress,timing), callback=log_result)

    pool.close()
    pool.join()

    for result in result_list:

        # print result
        infile = result['infile']
        outfile = result['outfile']

        if result['error']:
            sys.stdout.write("Error with %s :: %s \n" % (infile, result['error']))
            skippedlist.append(infile)
            # Go to next file .. we won't count this one in our summary stats
            continue

        total_size_new += result['comp_size']
        total_size_old += result['orig_size']
        total_files = total_files + 1

        if verbose:
            if timing:
                print("{} d = {} Shuffle: {:d} {} s {} s {} s Mem: {} KB {} B {:0.4}".format(
                    file, level, shuffle, 
                    result['times'][0], result['times'][1], result['times'][2],
                    result['times'][3], result['comp_size'], float(result['orig_size'])/float(result['comp_size'])))
            else:
                print("{} d = {} Shuffle: {:d} {} B {:0.4}".format(
                    file, level, shuffle, result['comp_size'], float(result['orig_size'])/float(result['comp_size'])))

    # Make a nice human readable number from the total amount of space we've saved
    total_space_saved = float(total_size_old-total_size_new)
    power = 0
    while (power < 4 and (int(total_space_saved) / 1000 > 0)):
        power = power + 1
        total_space_saved = total_space_saved / 1000. 
        
    units = ['B','KB','MB','GB','TB']

    if total_files > 0:
        print("Directory: {0}".format(path))
        print("    Number files compressed: {0}".format(total_files))
        print("    Total space saved: {0:.2f} {1}".format(total_space_saved,units[power]))
        print("    Average compression ratio: {0:.2f}".format(float(total_size_old)/total_size_new))
    if len(skippedlist) > 0:
        print("    Following files not properly compressed or suspiciously high compression ratio:")
        print (", ".join(skippedlist))

    if overwrite:
        try:
            os.rmdir(outdir)
        except OSError:
            print("Failed to remove temporary directory {}".format(outdir))


def parse_args(arglist):
    """
    Parse arguments given as list (arglist)
    """

    def maxcompression_type(x):
        x = int(x)
        if x < 0:
            raise argparse.ArgumentTypeError("Minimum maxcompression is 0")
        return x

    parser = argparse.ArgumentParser(description="Run nc2nc (or nccopy) on a number of netCDF files")
    parser.add_argument("-d","--dlevel", help="Set deflate level. Valid values 0-9 (default=5)", type=int, default=5, choices=range(0,10), metavar='{1-9}')
    # parser.add_argument("-l","--limited", help="Change unlimited dimension to fixed size (default is to not squash unlimited)", action='store_true')
    parser.add_argument("-n","--noshuffle", help="Don't shuffle on deflation (default is to shuffle)", action='store_true')
    parser.add_argument("-s","--chunksize", help="Set chunksize - total size of one chunk in KiB (default=64), nc2nc only", type=int, default=64)
    parser.add_argument("-b","--buffersize", help="Set size of copy buffer in MiB (default=500), nc2nc only", type=int, default=500)
    parser.add_argument("-t","--tmpdir", help="Specify temporary directory to save compressed files", default='tmp.nc_compress')
    parser.add_argument("-v","--verbose", help="Verbose output", action='store_true')
    parser.add_argument("-r","--recursive", help="Recursively descend directories compressing all netCDF files (default False)", action='store_true')
    parser.add_argument("-o","--overwrite", help="Overwrite original files with compressed versions (default is to not overwrite)", action='store_true')
    parser.add_argument("-m","--maxcompress", help="Set a maximum compression as a paranoid check on success of nccopy (default is 10, set to zero for no check)", default=10,type=maxcompression_type)
    parser.add_argument("-p","--paranoid", help="Paranoid check : run nco ndiff on the resulting file ensure no data has been altered", action='store_true')
    parser.add_argument("-f","--force", help="Force compression, even if input file is already compressed (default False)", action='store_true')
    parser.add_argument("-c","--clean", help="Clean tmpdir by removing existing compressed files before starting (default False)", action='store_true')
    parser.add_argument("-pa","--parallel", help="Compress files in parallel", action='store_true')
    parser.add_argument("-np","--numproc", help="Specify the number of processes to use in parallel operation", type=int, default=1)
    parser.add_argument("-ff","--fromfile", help="Read files to be compressed from a text file")
    parser.add_argument("--nccopy", help="Use nccopy instead of nc2nc (default False)", action='store_true')
    parser.add_argument("--timing", help="Collect timing statistics when compressing each file (default False)", action='store_true')
    parser.add_argument("inputs", help="netCDF files or directories (-r must be specified to recursively descend directories). Can accept piped arguments.", nargs='*', default=sys.stdin)

    return parser.parse_args(arglist)

def main(args):
    
    # We won't make users specify parallel if they've specified a number of processors
    if args.numproc: args.parallel = True

    if args.parallel:
        if args.numproc is not None:
            numproc = args.numproc
        else:
            numproc = mp.cpu_count()

    filedict = defaultdict(list)

    if args.fromfile:
        args.inputs = open(args.fromfile)

    # Loop over all the inputs from the command line. These can be either file globs
    # or directory names. In either case we'll group them by directory
    for ncinput in args.inputs:
        ncinput = ncinput.rstrip('\r\n')
        if args.tmpdir in ncinput:
            print ("tmpdir in input path: {} .. skipping".format(ncinput))
            continue
        if not os.path.exists(ncinput):
            print ("Input does not exist: {} .. skipping".format(ncinput))
            continue
        if os.path.isdir(ncinput):
            # Check that we haven't been here already
            if ncinput in filedict: continue
            # os.walk will return the entire directory structure
            for root, dirs, files in os.walk(ncinput):
                # Ignore emtpy directories, and our own temp directory, in case we
                # re-run on same tree
                if len(files) == 0: continue
                if root.endswith(args.tmpdir): continue
                # Check that we haven't been here already
                if root in filedict: continue
                # Only descend into subdirs if we've set the recursive flag
                if (root != ncinput and not args.recursive):
                    print("Skipping subdirectories of {0} :: --recursive option not specified".format(ncinput))
                    break
                else:
                    # Compress all the files in this directory
                    compress_files(root,
                                   files,
                                   args.tmpdir,
                                   args.overwrite,
                                   args.maxcompress,
                                   args.dlevel,
                                   not args.noshuffle,
                                   args.force,
                                   args.clean,
                                   args.verbose,
                                   args.chunksize,
                                   args.buffersize,
                                   args.nccopy,
                                   args.paranoid,
                                   numproc,
                                   args.timing)
                    # Note we've traversed this directory but set directory to an empty list
                    filedict[root] = []
        else:
            (root,file) = os.path.split(ncinput)
            if (root == ''): root = "./"
            filedict[root].append(file)

    if args.fromfile:
        args.inputs.close()

    # Files that were specified directly on the command line are compressed by directory.
    # We only create a temporary directory once, and can then clean up after ourselves.
    # Also makes it easier to run some checks to ensure compression is ok, as all the files
    # are named the same, just in a separate temporary sub directory.
    for directory in filedict:
        if len(filedict[directory]) == 0: continue
        compress_files(directory,
                       filedict[directory],
                       args.tmpdir,
                       args.overwrite,
                       args.maxcompress,
                       args.dlevel,
                       not args.noshuffle,
                       args.force,
                       args.clean,
                       args.verbose,
                       args.chunksize,
                       args.buffersize,
                       args.nccopy,
                       args.paranoid,
                       numproc,
                       args.timing)

                
def main_parse_args(arglist):
    """
    Call main with list of arguments. Callable from tests
    """
    # Must return so that check command return value is passed back to calling routine
    # otherwise py.test will fail
    return main(parse_args(arglist))

def main_argv():
    """
    Call main and pass command line arguments. This is required for setup.py entry_points
    """
    main_parse_args(sys.argv[1:])

if __name__ == "__main__":

    main_argv()
