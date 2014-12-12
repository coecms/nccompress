import math
import operator
import numpy as np

def count(arr):
    """Return number of true values in the array arr"""
    o = np.ones(np.size(arr),dtype="int")
    return sum(o[arr])

def binlist(n, width=0):
    """Return list of bits that represent a non-negative integer.

    n      -- non-negative integer
    width  -- number of bits in returned zero-filled list (default 0)
    """
    return map(int, list(bin(n)[2:].zfill(width)))

def numVals(shape):
    """Return number of values in chunk of specified shape, given by a list of dimension lengths.

    shape -- list of variable dimension sizes"""
    if(len(shape) == 0):
        return 1
    return reduce(operator.mul, shape)

def perturbShape(shape, onbits):
    """Return shape perturbed by adding 1 to elements corresponding to 1 bits in onbits

    shape  -- list of variable dimension sizes
    onbits -- non-negative integer less than 2**len(shape)
    """
    return map(sum, zip(shape, binlist(onbits, len(shape))))

def chunk_shape_nD(varShape, valSize=4, chunkSize=4096):
    """
    Return a 'good shape' for a 3D variable, assuming balanced 1D, 2D access

    varShape  -- list of variable dimension sizes
    chunkSize -- minimum chunksize desired, in bytes (default 4096)
    valSize   -- size of each data value, in bytes (default 4)

    Returns integer chunk lengths of a chunk shape that provides
    balanced access of 1D subsets and 2D subsets of a netCDF or HDF5
    variable var. 'Good shape' for chunks means that the number of
    chunks accessed to read any kind of 1D or 2D subset is approximately
    equal, and the size of each chunk (uncompressed) is at least
    chunkSize, which is often a disk block size.
    """

    rank = len(varShape)
    chunkVals = chunkSize / float(valSize) # ideal number of values in a chunk
    numChunks  = numVals(varShape) / chunkVals # ideal number of chunks
    axisChunks = numChunks ** (1./rank)   # ideal number of chunks along each axis

    # Add together all the axisChunks, divide up by the proportion of the total number
    # of dimensions, with the proviso that minimum size is 0.1 of dimension size
    # Also would like to make the chunk a multiple of dimension
    # Also need to make sure cache is large enough

    axisFrac = np.array(varShape) / float(sum(varShape))

    # Renormalise all fractions greater than 0.1
    tot = sum(axisFrac>0.1)/float(count(axisFrac>0.1))
    for i in range(len(axisFrac)):
        if axisFrac[i] > 0.1:
            axisFrac[i] /= tot
        else:
            axisFrac[i] = 0.1
            
    cFloor = numChunks * axisChunks
    
    cFloor = [] # will be first estimate of good chunk shape
    # cFloor  = [varShape[0] // axisChunks**2, varShape[1] // axisChunks, varShape[2] // axisChunks]
    # except that each chunk shape dimension must be at least 1
    # chunkDim = max(1.0, varShape[0] // axisChunks**2)
    if varShape[0] / axisChunks**2 < 1.0:
        chunkDim = 1.0
        axisChunks = axisChunks / math.sqrt(varShape[0]/axisChunks**2)
    else:
        chunkDim = varShape[0] // axisChunks**2

    
        
    cFloor.append(chunkDim)
    prod = 1.0  # factor to increase other dims if some must be increased to 1.0
    for i in range(1, rank):
        if varShape[i] / axisChunks < 1.0:
            prod *= axisChunks / varShape[i]
    for i in range(1, rank):
        if varShape[i] / axisChunks < 1.0:
            chunkDim = 1.0
        else:
            chunkDim = (prod*varShape[i]) // axisChunks
        cFloor.append(chunkDim)

    # cFloor is typically too small, (numVals(cFloor) < chunkSize)
    # Adding 1 to each shape dim results in chunks that are too large,
    # (numVals(cCeil) > chunkSize).  Want to just add 1 to some of the
    # axes to get as close as possible to chunkSize without exceeding
    # it.  Here we use brute force, compute numVals(cCand) for all
    # 2**rank candidates and return the one closest to chunkSize
    # without exceeding it.
    bestChunkSize = 0
    cBest = cFloor
    for i in range(8):
        # cCand = map(sum,zip(cFloor, binlist(i, rank)))
        cCand = perturbShape(cFloor, i)
        thisChunkSize = valSize * numVals(cCand)
        if bestChunkSize < thisChunkSize <= chunkSize:
            bestChunkSize = thisChunkSize
            cBest = list(cCand) # make a copy of best candidate so far
    return map(int, cBest)
