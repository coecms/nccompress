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
import math
import operator
import numpy as np
import numpy.ma as ma

# A couple of hard-wired executable paths that might need changing

def is_netCDF_compressed(ncfile):
    """ Test to see if ncfile is a valid netCDF file
    """
    isnetCDF=False
    iscompressed=False
    try:
        fh = nc.Dataset(ncfile)
        isnetCDF=True
        iscompressed = is_compressed(fh)
        fh.close
    except:
        # Don't do anything
        pass
    return isnetCDF, iscompressed

def is_compressed(handle):
    """ Test if netcdfile is compressed
    """
    # tmp = nc.Dataset(ncfile)
    compressed=False
    # Classic files have no filters attribute, and no compression
    # should use data_model instead of file_format in future
    if not handle.file_format.startswith("NETCDF3"):
        for varname in handle.variables:
            hdf5_filters = handle.variables[varname].filters()
            if hdf5_filters['complevel'] > 0:
                compressed = True
                break
        # tmp.close()

    return compressed

def parse_args(arglist):
    """
    Parse arguments given as list (arglist)
    """

    def maxcompression_type(x):
        x = int(x)
        if x < 0:
            raise argparse.ArgumentTypeError("Minimum maxcompression is 0")
        return x

    
    parser = argparse.ArgumentParser(description="Find netCDF files. Can discriminate by compression")
    # parser.add_argument("-v","--verbose", help="Verbose output", action='store_true')
    parser.add_argument("-r","--recursive", help="Recursively descend directories to find netCDF files (default False)", action='store_true')

    group = parser.add_mutually_exclusive_group()
    group.add_argument("-u","--uncompressed", help="Find only uncompressed netCDF files (default False)", action='store_true')
    group.add_argument("-c","--compressed", help="Find only compressed netCDF files (default False)", action='store_true')

    parser.add_argument("inputs", help="netCDF files or directories (-r must be specified to recursively descend directories). Can accept piped arguments.", nargs='*', default=sys.stdin)

    return parser.parse_args(arglist)
    
def find_files(args):
    
    # verbose=args.verbose

    findcompressed = args.compressed
    finduncompressed = args.uncompressed

    found_files = []

    # If neither are specified make them both true, find any kind of netCDF file
    if not finduncompressed and not findcompressed:
        findcompressed = True
        finduncompressed = True

    filedict = defaultdict(list)

    # Loop over all the inputs from the command line. These can be either file globs
    # or directory names. In either case we'll group them by directory
    for ncinput in args.inputs:
        # If we pipe files to stdin they may have a trailing newline, so we
        # need to strip it out
        ncinput = ncinput.rstrip('\r\n')
        if not os.path.exists(ncinput):
            sys.stderr.write("Input does not exist: {} .. skipping\n".format(ncinput))
            continue
        if os.path.isdir(ncinput):
            # os.walk will return the entire directory structure
            for root, dirs, files in os.walk(ncinput,topdown=True):
                # Ignore emtpy directories, and our own temp directory, in case we
                # re-run on same tree
                if len(files) == 0: continue
                # if root.endswith(args.tmpdir): continue
                # Only descend into subdirs if we've set the recursive flag
                if (root != ncinput and not args.recursive):
                    sys.stderr.write("Skipping subdirectories :: --recursive option not specified\n")
                    break
                else:
                    # Group by directory
                    filedict[root].extend(files)
        else:
            (root,file) = os.path.split(ncinput)
            if (root == ''): root = "./"
            filedict[root].append(file)

    ncompressed = 0
    nuncompressed = 0
    
    if len(filedict) == 0:
        sys.stderr.write("No files found to process\n")
    else:
        # We only create a temporary directory once,
        # and can then clean up after ourselves. Also makes it easier to run some checks to
        # ensure compression is ok, as all the files are named the same, just in a separate
        # temporary sub directory.
        for directory in filedict:
            if len(filedict[directory]) == 0: continue
            for file in filedict[directory]:
                filepath = os.path.join(directory,file)
                isnetCDF, iscompressed =  is_netCDF_compressed(filepath)
                if isnetCDF:
                    if iscompressed:
                        ncompressed += 1
                        if findcompressed: found_files.append(filepath)
                    else:
                        nuncompressed += 1
                        if finduncompressed: found_files.append(filepath)

    return found_files

def main(args):

    found_files = find_files(args)

    if found_files:
        for file in found_files:
            sys.stdout.write(file+"\n")
                
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
