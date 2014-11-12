#!/usr/bin/env python
import subprocess
import os
import sys
import netCDF4 as nc
import argparse
import re
from warnings import warn
from shutil import move
from collections import defaultdict

# A couple of hard-wired executable paths that might need changing

# Need to use system time command explicitly, otherwise get crippled bash version
timecmd='/usr/bin/time'
nccopy='nccopy'

def maxcompression_type(x):
    x = int(x)
    if x < 0:
        raise argparse.ArgumentTypeError("Minimum maxcompression is 0")
    return x

parser = argparse.ArgumentParser(description="Run nccopy on a number of netCDF files")
parser.add_argument("-d","--dlevel", help="Set deflate level. Valid values 0-9 (default=5)", type=int, default=5, choices=range(0,10), metavar='{1-9}')
parser.add_argument("-l","--limited", help="Change unlimited dimension to fixed size (default is to not squash unlimited)", action='store_true')
parser.add_argument("-n","--noshuffle", help="Don't shuffle on deflation (default is to shuffle)", action='store_true')
parser.add_argument("-t","--tmpdir", help="Specify temporary directory to save compressed files", default='tmp.nc_compress')
parser.add_argument("-v","--verbose", help="Verbose output", action='store_true')
parser.add_argument("-r","--recursive", help="Recursively descend directories compressing all netCDF files (default False)", action='store_true')
parser.add_argument("-o","--overwrite", help="Overwrite original files with compressed versions (default is to not overwrite)", action='store_true')
parser.add_argument("-m","--maxcompress", help="Set a maximum compression as a paranoid check on success of nccopy (default is 10, set to zero for no check)", default=10,type=maxcompression_type)
parser.add_argument("inputs", help="netCDF files or directories (-r must be specified to recursively descend directories)", nargs='*')
args = parser.parse_args()

paranoid = False if args.maxcompress == 0 else True

verbose=args.verbose

def run_nccopy(infile,outfile,level,limited,shuffle,chunking=None):
    # The format string for the time command
    #   %e     (Not in tcsh.) Elapsed real time (in seconds).
    #   %S     Total number of CPU-seconds that the process spent in kernel mode.
    #   %U     Total number of CPU-seconds that the process spent in user mode.
    #   %M     Maximum resident set size of the process during its lifetime, in Kbytes.
    fmt = "%e %S %U %M"
    cmd = ['time','-f',fmt,nccopy,'-d',str(level)]
    if (limited): cmd.append('-u')
    if (shuffle): cmd.append('-s')
    if (chunking):
        cmd.append('-c')
        cmd.append(chunking)
    cmd.append(infile)
    cmd.append(outfile)
    if (verbose): print (' '.join(cmd))
    try:
        output = subprocess.check_output(cmd,stderr=subprocess.STDOUT)
        return {
            'outfile' : outfile,
            'times' : output.split(),
            'comp_size' : os.path.getsize(outfile),
            'orig_size' : os.path.getsize(infile),
            'dlevel' : level,
            'shuffle' : shuffle,
            'limited' : limited
            }
    except:
        raise

def compress_files(path,files,tmpdir,overwrite,paranoid,maxcompress,level,limited,shuffle):

    total_size_new = 0
    total_size_old = 0
    total_files = 0
    skippedlist = []

    # Create our temporary directory
    outdir = os.path.join(path,tmpdir)
    if not os.path.isdir(outdir):
        # Don't try and catch errors, let program stop if there is a problem
        os.mkdir(outdir)

    for file in files:

        infile = os.path.join(path,file)
        outfile = os.path.join(outdir,file)

        if (verbose): print infile,outfile,level,limited,shuffle

        # Try compressing the data
        try:
            copydict = run_nccopy(infile,outfile,level,limited,shuffle)
        except:
            if (verbose): print ("Something went wrong with {}".format(file))
            skippedlist.append(file)
            # Go to next file .. so original will not be overwritten
            continue

        # Move compressed data back to original location
        if overwrite:

            # Serious. We're going to blow away the original file with
            # the compressed version -- do some sanity checks to make
            # sure we're not copying rubbish over our data
            if ( maxcompress != 0 and copydict['orig_size'] > maxcompress*copydict['comp_size'] ):
                # If the compressed version is less than 1/maxcompress we will
                # warn and not overwrite the original
                print("Compression ratio {0} is suspiciously high: {1} not overwritten".format(copydict['orig_size']/copydict['comp_size'],file))
                skippedlist.append(file)
                continue
            
            move(outfile,infile)

        total_size_new = total_size_new + copydict['comp_size']
        total_size_old = total_size_old + copydict['orig_size']
        total_files = total_files + 1

        if verbose:
            print("{} d = {} Conv unlim: {:d} Shuffle: {:d} {} s {} s {} s Mem: {} KB {} B {:0.4}".format(
                file, level, limited, shuffle, 
                copydict['times'][0], copydict['times'][1], copydict['times'][2],
                copydict['times'][3], copydict['comp_size'], float(copydict['orig_size'])/float(copydict['comp_size'])))

    # Make a nice human readable number from the total amount of space we've saved
    total_space_saved = float(total_size_old-total_size_new)
    power = 0
    while (power < 4 and (int(total_space_saved) / 1024 > 0)):
        power = power + 1
        total_space_saved = total_space_saved / 1024. 
        
    units = ['B','KB','MB','GB','TB']

    print("Directory: {0}".format(path))
    print("    Number files compressed: {0}".format(total_files))
    print("    Total space saved: {0:.2f} {1}").format(total_space_saved,units[power])
    print("    Average compression ratio: {0}").format(total_size_old/total_size_new)
    if len(skippedlist) > 0:
        print("    Following files not properly compressed or suspiciously high compression ratio:")
        print ("\n").join(skippedlist)

    try:
        os.rmdir(outdir)
    except OSError:
        print("Failed to remove temporary directory {}".format(outdir))


## MAIN ##
    
filedict = defaultdict(list)

# Loop over all the inputs from the command line. These can be either file globs
# or directory names. In either case we'll group them by directory
for ncinput in args.inputs:
    if not os.path.exists(ncinput):
        print ("Input does not exist: {} .. skipping".format(ncinput))
        continue
    if os.path.isdir(ncinput):
        # os.walk will return the entire directory structure
        for root, dirs, files in os.walk(ncinput):
            # Ignore emtpy directories, and our own temp directory, in case we
            # re-run on same tree
            if len(files) == 0: continue
            if root.endswith(args.tmpdir): continue
            # Only descend into subdirs if we've set the recursive flag
            if (root != ncinput and not args.recursive):
                print("Skipping subdirectory {0} :: --recursive option not specified".format(root))
                continue
            else:
                # Group by directory
                filedict[root].append(files)
    else:
        (root,file) = os.path.split(ncinput)
        if (root == ''): root = "./"
        filedict[root].append(file)

if len(filedict) == 0:
    print "No files found to process"
else:
    # Compress files directory by directory. We only create a temporary directory once,
    # and can then clean up after ourselves. Also makes it easier to run some checks to
    # ensure compression is ok, as all the files are named the same, just in a separate
    # temporary sub directory.
    for directory in filedict:
        if len(filedict[directory]) == 0: continue
        compress_files(directory,filedict[directory],args.tmpdir,args.overwrite,paranoid,args.maxcompress,args.dlevel,args.limited,not args.noshuffle)

                
