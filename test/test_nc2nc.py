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

import pytest
import imp
from netCDF4 import Dataset
from numpy import array, arange, dtype
from numpy.testing import assert_array_equal, assert_array_almost_equal
import os
from utils import make_simple_netcdf_file, remove_ncfiles
from nccompress import nc2nc

verbose = True


ncfiles =['simple_xy.nc', 'simple_xy_noclassic.nc']

def setup_module(module):
    if verbose: print ("setup_module      module:%s" % module.__name__)
    remove_ncfiles(verbose)
    make_simple_netcdf_file(ncfiles)
 
def teardown_module(module):
    if verbose: print ("teardown_module   module:%s" % module.__name__)
    remove_ncfiles(verbose)

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

def test_nc2nc():

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

    # test copy buffer
    nc2nc.nc2nc(ncfiles[0], ncfiles[0]+'2nc.nc', clobber=True,verbose=False, buffersize=10)

    # quantise the variable to 1 dp
    nc2nc.nc2nc(ncfiles[0], ncfiles[0]+'2nc_quantised.nc', clobber=True, lsd_dict = {'data':1})

    # Make a netCDF4 version
    nc2nc.nc2nc(ncfiles[0], ncfiles[0]+'2nc.nc4',clobber=True,classic=False)
    
    try:
        nc2nc.nc2nc(ncfiles[0]+'2nc.nc4',ncfiles[0]+'2nc.2.nc4',clobber=True,classic=False)
    except nc2nc.FormatError:
        pass

    nc2nc.nc2nc(ncfiles[0]+'2nc.nc4',ncfiles[0]+'2nc.2.nc4',clobber=True,classic=False,ignoreformat=True)
