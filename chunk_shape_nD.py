import math
import operator
import numpy as np
import numpy.ma as ma
import pdb

def numVals(shape):
    """Return number of values in chunk of specified shape, given by a list of dimension lengths.

    shape -- list of variable dimension sizes"""
    if(len(shape) == 0):
        return 1
    return reduce(operator.mul, shape)

def calcChunkShape(chunkVol, varShape):
    """
    Calculate a chunk shape for a given volume/area for the dimensions in varShape.

    chunkVol   -- volume/area of the chunk
    chunkVol   -- array of dimensions for the whole dataset
    """

    return np.array(np.ceil(np.asarray(varShape) * (chunkVol / float(numVals(varShape))) ** (1./len(varShape))),dtype="int")

def chunk_shape_nD(varShape, valSize=4, chunkSize=4096, minDim=2):
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

    import pdb

    varShapema = ma.array(varShape)
    
    chunkVals = chunkSize / float(valSize) # ideal number of values in a chunk

    # Make an ideal chunk shape array 
    chunkShape = ma.array(calcChunkShape(chunkVals,varShapema),dtype=int)

    # And a copy where we'll store our final values
    chunkShapeFinal = ma.masked_all(chunkShape.shape,dtype=int)

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

        # print chunkShape,chunkShapeFinal
        # Have we fixed any dimensions and filled them in chunkShapeFinal?
        if chunkShapeFinal.count() > 0:
            chunkCount = numVals(chunkShapeFinal[~chunkShapeFinal.mask])
        else:
            if (lastChunkCount == -1):
                # Haven't modified initial guess, break out of
                # this loop and accept chunkShape 
                break

        if chunkCount != lastChunkCount:
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

    return chunkShapeFinal

if __name__ == "__main__":

    # import pdb

    def checkError(chunks, answer):
        if (chunks-np.asarray(answer)).any():
            print "Error!"
            print chunks, answer

    print calcChunkShape(1024,(50,1440,1080))
    print calcChunkShape(342,(1440,1080))

    # pdb.set_trace()

    chunks = chunk_shape_nD([50,1440,1080])
    checkError(chunks, [2, 35, 26])

    print chunks, numVals(chunks)*4.

    chunks = chunk_shape_nD([50,1440,1080],valSize=8)
    checkError(chunks, [2, 19, 14])

    print chunks, numVals(chunks)*8.

    chunks = chunk_shape_nD([50,1440,1080],chunkSize=8192)
    checkError(chunks, [2, 43, 33])

    print chunks, numVals(chunks)*4.

    chunks = chunk_shape_nD([5, 50,1440,1080])
    checkError(chunks, [2, 2, 19, 14])

    print chunks, numVals(chunks)*4.

    chunks = chunk_shape_nD([1440,1080])
    checkError(chunks, [37, 28])

    print chunks, numVals(chunks)*4.

    chunks = chunk_shape_nD([1440])
    checkError(chunks, [1024])

    print chunks, numVals(chunks)*4.

    chunks = chunk_shape_nD([10000,5,50,1440,1080])
    checkError(chunks, [26, 2, 2, 4, 3])

    print chunks, numVals(chunks)*4.

