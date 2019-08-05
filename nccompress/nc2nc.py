#!/usr/bin/env python

"""
   Copy one netCDF file to another with compression and sensible
   chunking

   Adapted from nc3tonc4

   https://github.com/Unidata/netcdf4-python/blob/master/utils/nc3tonc4

"""

from netCDF4 import Dataset
import numpy as np
import numpy.ma as ma
import os
import sys
import math
import operator
from warnings import warn
import argparse
import copy
import numbers
from six.moves import reduce
    

dtypes = {
    'f' : 4, # f4, 32-bit floating point
    'd' : 8, # f8, 64-bit floating point
    'e' : 4, # f2, 16-bit floating point
    'i' : 4, # i4, 32-bit signed integer
    'h' : 2, # i2, 16-bit signed integer
    'l' : 8, # i8, 64-bit singed integer
    'b' : 1, # i1, 8-bit signed integer
    'B' : 1, # u1, 8-bit unsigned integer
    'H' : 2, # u2, 16-bit unsigned integer
    'I' : 4, # u4, 32-bit unsigned integer
    'L' : 8, # u8, 64-bit unsigned integer
    'S' : 1 }  # S1, single-character string

class FormatError(Exception):
    '''Unsupported netCDF format'''
    
def numVals(shape):
    """Return number of values in chunk of specified shape, given by a list of dimension lengths.

    shape -- list of variable dimension sizes"""
    if(len(shape) == 0):
        return 1
    return reduce(operator.mul, shape)

def cascadeRounding(array):
    """Implement cascase rounding
    http://stackoverflow.com/questions/792460/how-to-round-floats-to-integers-while-preserving-their-sum
    """

    sort_index = np.argsort(array)
    integer_array = []

    total_float = 0
    total_int = 0

    # We place a hard limit on the total of the array, which keeps
    # the rounded values from exceeding the total of the array
    limit = np.floor(sum(array))
    
    for idx in sort_index:
        total_float += array[idx]
        integer_array.append(min(round(total_float),limit)-total_int)
        total_int += integer_array[-1]

    rounded_array = np.zeros(len(array))

    # Should make this a comprehension, but I couldn't comprehend it
    for i in range(len(sort_index)):
        rounded_array[sort_index[i]] = integer_array[i]

    return rounded_array

def calcChunkShape(chunkVol, varShape):
    """
    Calculate a chunk shape for a given volume/area for the dimensions in varShape.

    chunkVol   -- volume/area of the chunk
    chunkVol   -- array of dimensions for the whole dataset
    """

    return np.array(cascadeRounding(np.asarray(varShape) * (chunkVol / float(numVals(varShape))) ** (1./len(varShape))),dtype="int")

def chunk_shape_nD(varShape, valSize=4, chunkSize=4096, minDim=1):
    """
    Return a 'good shape' for an nD variable, assuming balanced 1D, 2D access

    varShape  -- list of variable dimension sizes
    chunkSize -- minimum chunksize desired, in bytes (default 4096)
    valSize   -- size of each data value, in bytes (default 4)
    minDim    -- mimimum chunk dimension (if var dimension larger
                 than this value, otherwise it is just var dimension)

    Returns integer chunk lengths of a chunk shape that provides
    balanced access of 1D subsets and 2D subsets of a netCDF or HDF5
    variable var. 'Good shape' for chunks means that the number of
    chunks accessed to read any kind of 1D or 2D subset is approximately
    equal, and the size of each chunk (uncompressed) is at least
    chunkSize, which is often a disk block size.
    """

    varShapema = ma.array(varShape)
    
    chunkVals = min(chunkSize / float(valSize),numVals(varShapema)) # ideal number of values in a chunk

    # Make an ideal chunk shape array 
    chunkShape = ma.array(calcChunkShape(chunkVals,varShapema),dtype=int)

    # Short circuit for 1D arrays. Logic below unecessary & can have divide by zero
    if len(varShapema) == 1: return chunkShape.filled(fill_value=1)

    # And a copy where we'll store our final values
    chunkShapeFinal = ma.masked_all(chunkShape.shape,dtype=int)

    if chunkVals < numVals(np.minimum(varShapema,minDim)):
        while chunkVals < numVals(np.minimum(varShapema,minDim)):
            minDim -= 1
        sys.stderr.write('Mindim too large for variable, reduced to : %d\n' % minDim)

    lastChunkCount = -1
    
    while True:

        # Loop over the axes in chunkShape, making sure they are at
        # least minDim in length.
        for i in range(len(chunkShape)):
            if ma.is_masked(chunkShape[i]):
                continue 
            if (chunkShape[i] < minDim):
                # Set the final chunk shape for this dimension
                chunkShapeFinal[i] = min(minDim,varShapema[i])
                # mask it out of the array of possible chunkShapes
                chunkShape[i] = ma.masked

        # Have we fixed any dimensions and filled them in chunkShapeFinal?
        if chunkShapeFinal.count() > 0:
            chunkCount = numVals(chunkShapeFinal[~chunkShapeFinal.mask])
        else:
            if (lastChunkCount == -1):
                # Haven't modified initial guess, break out of
                # this loop and accept chunkShape 
                break

        if chunkCount != lastChunkCount and len(varShapema[~chunkShape.mask]) > 0:
            # Recalculate chunkShape array, with reduced dimensions
            chunkShape[~chunkShape.mask] = calcChunkShape(chunkVals/chunkCount,varShapema[~chunkShape.mask])
            lastChunkCount = chunkCount
        else:
            break

    # This doesn't work when chunkShape has no masked values. Weird.
    # chunkShapeFinal[chunkShapeFinal.mask] = chunkShape[~chunkShape.mask]
    for i in range(len(chunkShapeFinal)):
        if ma.is_masked(chunkShapeFinal[i]):
            chunkShapeFinal[i] = chunkShape[i]

    return chunkShapeFinal.filled(fill_value=1)


def nc2nc(filename_o, filename_d, zlib=True, complevel=5, shuffle=True, fletcher32=False,
    clobber=False, verbose=False, classic=True, lsd_dict=None, vars=None, chunksize=4, buffersize=50, mindim=1,ignoreformat=False):
    """convert a netcdf file (filename_o) to another netcdf file (filename_d)
    The default format is 'NETCDF4_classic', but can be set to NETCDF4 if classic=False.
    If the lsd_dict is not None, variable names corresponding to the keys of the dict
    will be truncated to the decimal place specified by the values of the dict.
    This improves compression by making it 'lossy'..
    If vars is not None, only variable names in the list will be copied (plus all the
    dimension variables). The zlib, complevel and shuffle keywords control
    how the compression is done. buffersize is the size (in KB) of the buffer used to
    copy the data from one file to another. mindim sets a minimum size for a dimension
    of a chunk. In some cases very large variable dimensions will mean chunk sizes for
    the smaller dimensions will be small, with a minimum of at least 1. This can lead to
    slow access times.
    """

    if os.path.isfile(filename_d) and not clobber:
        sys.stderr.write('Output file already exists: %s. Use -o option to overwrite\n' % filename_d)
        return False

    ncfile_o = Dataset(filename_o,'r')

    if ncfile_o.file_format is "NETCDF4":
        if ignoreformat:
            warn('netCDF4 formatted file .. ignoring')
        else:
            raise FormatError('nc2nc is not tested to work with netCDF4 files, only netCDF4 Classic, and netCDF3. See --ignoreformat option to ignore warning')
        
    if classic:
        ncfile_d = Dataset(filename_d,'w',clobber=clobber,format='NETCDF4_CLASSIC')
    else:
        ncfile_d = Dataset(filename_d,'w',clobber=clobber,format='NETCDF4')
    mval = 1.e30 # missing value if unpackshort=True

    # Copy buffer specified in MiB, so convert to bytes
    buffersize = buffersize*(1024**2)
    # Chunk size specified in KiB, so convert to bytes
    chunksize = chunksize*1024

    # create dimensions. Check for unlimited dim.
    unlimdimname = False
    unlimdim = None

    # create global attributes.
    if verbose: sys.stdout.write('copying global attributes ..\n')
    #for attname in ncfile_o.ncattrs():
    #    setattr(ncfile_d,attname,getattr(ncfile_o,attname))
    ncfile_d.setncatts(ncfile_o.__dict__) 

    # Copy dimensions
    if verbose: sys.stdout.write('copying dimensions ..\n')
    for dimname,dim in ncfile_o.dimensions.items():
        if dim.isunlimited():
            unlimdimname = dimname
            unlimdim = dim
            ncfile_d.createDimension(dimname,None)
        else:
            ncfile_d.createDimension(dimname,len(dim))

    # create variables.
    if vars is None:
       varnames = ncfile_o.variables.keys()
    else:
       # variables to copy specified
       varnames = vars
       # add dimension variables
       for dimname in ncfile_o.dimensions.keys():
           if dimname in ncfile_o.variables.keys() and dimname not in varnames:
               varnames.append(dimname)

    for varname in varnames:
        ncvar = ncfile_o.variables[varname]
        if verbose: sys.stdout.write('copying variable %s\n' % varname)
        # quantize data?
        if lsd_dict is not None and varname in lsd_dict:
            lsd = int(lsd_dict[varname])
            if verbose: sys.stdout.write('truncating to least_significant_digit = %d\n'%lsd)
        else:
            lsd = None # no quantization.
        datatype = ncvar.dtype

        # is there an unlimited dimension?
        if unlimdimname and unlimdimname in ncvar.dimensions:
            hasunlimdim = True
        else:
            hasunlimdim = False

        if hasattr(ncvar, '_FillValue'):
            FillValue = ncvar._FillValue
        else:
            FillValue = None 

        chunksizes = None
        # check we have a mapping from the type to a number of bytes
        if ncvar.dtype.char in dtypes: 
            if verbose: sys.stdout.write('Variable shape: %s\n' % str(ncvar.shape))
            if (ncvar.shape != ()): chunksizes=chunk_shape_nD(ncvar.shape,valSize=dtypes[ncvar.dtype.char],minDim=mindim,chunkSize=chunksize)
            if verbose: sys.stdout.write('Chunk sizes: %s\n' % str(chunksizes))
        else:
            sys.stderr.write("This datatype not supported: dtype : %s\n" % ncvar.dtype.char)
            sys.exit(1)

        # Create the variable we will copy to
        var = ncfile_d.createVariable(varname, datatype, ncvar.dimensions, fill_value=FillValue, least_significant_digit=lsd, zlib=zlib, complevel=complevel, shuffle=shuffle, fletcher32=fletcher32, chunksizes=chunksizes)
        # fill variable attributes.
        attdict = ncvar.__dict__
        if '_FillValue' in attdict: del attdict['_FillValue']
        var.setncatts(attdict)

        # fill variable with data.

        dimlim = np.asarray(ncvar.shape)

        # bufferChunk is a multiple of the chunksize which is less than the size of copy buffer
        if (ncvar.shape != ()): bufferChunk = chunk_shape_nD(ncvar.shape,valSize=dtypes[ncvar.dtype.char],chunkSize=buffersize)

        # Don't bother copying in steps if all our data fits inside the bufferChunk
        if ncvar.shape == () or np.all(bufferChunk >= dimlim):
            var[:] = ncvar[:]
        else:

            # Make sure our chunk size is no larger than the dimension in that direction
            for ind, chunk in enumerate(bufferChunk):
                if chunk > dimlim[ind]: bufferChunk[ind] = dimlim[ind]
    
            if verbose: sys.stdout.write('Buffer chunk : %s\n' % str(bufferChunk))

            # bufferSteps is the number of copies of bufferChunk that fit along each axis
            bufferSteps = (dimlim-1)//bufferChunk + 1
    
            # Make an iterator out of all possible combinations of the bufferOffsets, which
            # are just steps along each dimension
            for index in np.ndindex(*bufferSteps):
                index *= bufferChunk
                slices = []
                # Make up slices of size bufferChunk
                for start, step, end in zip(index, bufferChunk, dimlim):
                    # min checks we don't go beyond the limits of the variable
                    slices.append(slice(start,min(start+step,end),None))
                # Copy the data
                var[slices] = ncvar[slices] 

        ncfile_d.sync() # flush data to disk

    # close files.
    ncfile_o.close()
    ncfile_d.close()

def parse_args(arglist):
    """
    Parse arguments given as list (arglist)
    """

    class DictAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            try:
                k, v = values.split("=", 1)
            except ValueError:
                raise argparse.ArgumentError(self, "Format must be key=value")

            # Implementation is from argparse._AppendAction
            items = copy.copy(argparse._ensure_value(namespace, self.dest, {}))  # Default mutables, use copy!
            try:
                items[k] = int(v)
            except ValueError:
                raise argparse.ArgumentError(self, "value must be an integer")
            if items[k] < 0: raise argparse.ArgumentError(self, "value cannot be negative")
            setattr(namespace, self.dest, items)

    def positive_int(value):
        ivalue = int(value)
        if ivalue < 1:
            raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
        return ivalue

    parser = argparse.ArgumentParser(description="Make a copy of a netCDF file with automatic chunk sizing")
    parser.add_argument("-d","--dlevel", help="Set deflate level. Valid values 0-9 (default=5)", type=int, default=5, choices=range(0,10), metavar='{1-9}')
    parser.add_argument("-m","--mindim", help="Minimum dimension of chunk. Valid values 1-dimsize", type=positive_int, default=1)
    parser.add_argument("-s","--chunksize", help="Set chunksize - total size of one chunk in KiB (default=64)", type=int, default=64)
    parser.add_argument("-b","--buffersize", help="Set size of copy buffer in MiB (default=500)", type=int, default=500)
    parser.add_argument("-n","--noshuffle", help="Don't shuffle on deflation (default is to shuffle)", action='store_true')
    parser.add_argument("-v","--verbose", help="Verbose output", action='store_true')
    parser.add_argument("-c","--classic", help="use NETCDF4_CLASSIC output instead of NETCDF4 (default true)", action='store_false')
    parser.add_argument("-f","--fletcher32", help="Activate Fletcher32 checksum", action='store_true')
    parser.add_argument("-va","--vars", help="Specify variables to copy (default is to copy all)", action='append')
    parser.add_argument("-q","--quantize", help="Truncate data in variable to a given decimal precision, e.g. -q speed=2 -q temp=0 causes variable speed to be truncated to a precision of 0.01 and temp to a precision of 1", action=DictAction)
    parser.add_argument("-o","--overwrite", help="Write output file even if already it exists (default is to not overwrite)", action='store_true')
    parser.add_argument("-i","--ignoreformat", help="Ignore warnings about netCDF4 formatted file: BE CAREFUL! (default false)", action='store_true')
    parser.add_argument("origin", help="netCDF file to be compressed")
    parser.add_argument("destination", help="netCDF output file")

    return parser.parse_args(arglist)

def main(args):
    
    zlib=False
    if args.dlevel > 0: zlib=True
 
    verbose = args.verbose

    # copy the data from origin to destination
    nc2nc(args.origin, args.destination, zlib=zlib, complevel=args.dlevel, shuffle=not args.noshuffle,
        fletcher32=args.fletcher32, clobber=args.overwrite, lsd_dict=args.quantize,
        verbose=verbose, vars=args.vars, classic=args.classic, chunksize=args.chunksize, buffersize=args.buffersize, ignoreformat=args.ignoreformat)
                
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
