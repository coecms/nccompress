#!/usr/bin/env python

import imp
from netCDF4 import Dataset
from numpy import array, arange, dtype
from numpy.testing import assert_array_equal, assert_array_almost_equal
import os

nc2nc = imp.load_source('nc2nc', "../nc2nc")

def test_numvals():
    assert( nc2nc.numVals((4,5,12)) == 240 )
    assert( nc2nc.numVals((1,5,12)) == 60 )
    # This is not really a case we would want, but it does behave consistently.
    assert( nc2nc.numVals((0,5,12)) == 0 )

def test_cascadeRounding():
    # print nc2nc.cascadeRounding([4.5,3.2,7.8,9.6,1.1])
    assert( all( nc2nc.cascadeRounding([4.5,3.2,7.8,9.6,1.1]) - [5.,3.,8.,9.,1.] == 0 ) )

def test_calcChunkShape():
    assert( all( nc2nc.calcChunkShape(1000,(10,10,10)) - [10,10,10] == 0 ) )
    assert( all( nc2nc.calcChunkShape(1000,(5,10,10)) - [6,13,12] == 0 ) )
    assert( all( nc2nc.calcChunkShape(1000,(5,5,10)) - [8,8,15] == 0 ) )
    assert( all( nc2nc.calcChunkShape(1000,(5,2,100)) - [5,2,100] == 0 ) )
    assert( all( nc2nc.calcChunkShape(1000,(5,17,67)) - [3,9,37] == 0 ) )
    assert( all( nc2nc.calcChunkShape(1000,(1,1,200,1,2)) - [1,1,240,2,2] == 0 ) )

def test_chunk_shape_nD():
    assert_array_equal(nc2nc.chunk_shape_nD((1,50,1080,1440),4,4096,2),[1,2,20,25])
    assert_array_equal( nc2nc.chunk_shape_nD((1,50,1080,1440),4,4096,2), [1,2,20,25])
    assert_array_equal( nc2nc.chunk_shape_nD((1,50,1080,1440),4,2048,2), [1,2,14,18])
    assert_array_equal( nc2nc.chunk_shape_nD((1,50,1080,1440),8,4096,2), [1,2,14,18])
    assert_array_equal( nc2nc.chunk_shape_nD((1,50,1080,1440),4,20000,2), [1,2,43,57])
    assert_array_equal( nc2nc.chunk_shape_nD((1,50,1080,1440),4,4096,5), [1,5,12,16])
    assert_array_equal( nc2nc.chunk_shape_nD((1,50,1080,1440),4,4096,2), [1,2,20,25])
    assert_array_equal( nc2nc.chunk_shape_nD((1,50,1080,1440),4,4096,10), [1,10,10,10])
    # Deliberately use too large a mindim, will issue a warning to stderr
    assert_array_equal( nc2nc.chunk_shape_nD((1,50,1080,1440),4,4096,12), [1,10,10,10])
    # Deliberately use too large a mindim, larger than any of the dimensions. Will
    # silently ignore and use the variable dimensions
    assert_array_equal( nc2nc.chunk_shape_nD((1,5,5,5),4,4096,12), [1,5,5,5])

ncfiles =['simple_xy.nc']

def make_netcdf_files():

    # os.unlink(ncfiles[0])

    # the output array to write will be nx x ny
    nx = 600; ny = 120
    # open a new netCDF file for writing.
    ncfile = Dataset(ncfiles[0],'w') 
    # create the output data.
    data_out = arange(nx*ny)/100. # 1d array
    data_out.shape = (nx,ny) # reshape to 2d array
    # create the x and y dimensions.
    ncfile.createDimension('x',nx)
    ncfile.createDimension('y',ny)
    # create the variable (4 byte integer in this case)
    # first argument is name of variable, second is datatype, third is
    # a tuple with the names of dimensions.
    data = ncfile.createVariable('data',dtype('float32').char,('x','y'))
    data.setncattr("Unhidden","test")
    # write data to variable.

    print "First value: ",data_out[0,0]
    data[:] = data_out
    print "First value: ",data[0,0]
    # close the file.
    ncfile.close()

def test_nc2nc():

    make_netcdf_files()
    # Compress the file we just made
    nc2nc.nc2nc(ncfiles[0], ncfiles[0]+'2nc.nc',clobber=True)
    # call h5diff?

    ncfile = Dataset(ncfiles[0],'r') 
    # read the data in variable named 'data'.
    data = ncfile.variables['data'][:]
    nx,ny = data.shape
    # check the data.
    data_check = arange(nx*ny)/100. # 1d array
    data_check.shape = (nx,ny) # reshape to 2d array
    # close the file.
    ncfile.close()

    # Check data is equal to 2 dp
    assert_array_almost_equal(data, data_check,2)
    
    # test setting mindim too large, should complain and set to 32
    nc2nc.nc2nc(ncfiles[0], ncfiles[0]+'2nc.nc', clobber=True,mindim=200)
    nc2nc.nc2nc(ncfiles[0], ncfiles[0]+'2nc.nc', clobber=True,mindim=-1)

    # quantise the variable to 1 dp
    nc2nc.nc2nc(ncfiles[0], ncfiles[0]+'2nc_quantised.nc', clobber=True, lsd_dict = {'data':1})
