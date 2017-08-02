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
from __future__ import print_function

import imp
from netCDF4 import Dataset
from numpy import array, arange, dtype
from numpy.testing import assert_array_equal, assert_array_almost_equal
import sys
import os
from utils import make_simple_netcdf_file, remove_ncfiles

verbose = True

# Make sure we find nc2nc in the directory above
os.environ['PATH'] = '..' + os.pathsep + os.environ['PATH']

# Test is run from directory above this one, location of the source file
nc_compress = imp.load_source('nc_compress', "nc_compress")

ncfiles =['simple_xy.nc']

def setup_module(module):
    if verbose: print ("setup_module      module:%s" % module.__name__)
    remove_ncfiles(verbose)
    make_simple_netcdf_file(ncfiles)
 
def teardown_module(module):
    if verbose: print ("teardown_module   module:%s" % module.__name__)
    remove_ncfiles(verbose)

def test_is_compressed():
    assert not nc_compress.is_compressed('simple_xy.nc')
    assert nc_compress.is_compressed('simple_xy.nc2nc.nc')
    # Test classic model
    assert not nc_compress.is_compressed('simple_xy.classic.nc')

def test_is_compressed():
    # retdict = nc_compress.run_nccopy('simple_xy.nc','simple_xy.run_nccopy.nc',level=3,verbose=False,shuffle=True)
    retdict = nc_compress.run_compress('simple_xy.nc','simple_xy.run_nccopy.nc',level=3,verbose=False,shuffle=True,nccopy=True)
    assert (retdict['orig_size']/retdict['comp_size'] >= 5.)
    assert (retdict['dlevel'] == 3)
    assert retdict['shuffle']
    # retdict = nc_compress.run_nc2nc('simple_xy.nc','simple_xy.run_nc2nc.nc',level=3,verbose=False,shuffle=True)
    retdict = nc_compress.run_compress('simple_xy.nc','simple_xy.run_nc2nc.nc',level=3,verbose=False,shuffle=True,nccopy=False)
    assert (retdict['orig_size']/retdict['comp_size'] >= 5.)
    assert (retdict['dlevel'] == 3)
    assert retdict['shuffle']

def test_are_equal():
    assert nc_compress.are_equal('simple_xy.nc','simple_xy.run_nc2nc.nc',verbose=True)
    assert nc_compress.are_equal('simple_xy.run_nc2nc.nc','simple_xy.run_nccopy.nc',verbose=True)
    assert not nc_compress.are_equal('simple_xy.nc','simple_xy.2nc_quantised.nc',verbose=True)
    # os.unlink('simple_xy.run_nc2nc.nc')
