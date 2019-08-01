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
from nccompress import ncfind, nc2nc

from glob import glob

verbose = True

ncfiles =['simple_xy.nc']

def setup_module(module):
    if verbose: print ("setup_module      module:%s" % module.__name__)
    remove_ncfiles(verbose)
    make_simple_netcdf_file(ncfiles)
    # Compress the file we just made
    nc2nc.nc2nc(ncfiles[0], ncfiles[0]+'2nc.nc',clobber=True)
 
def teardown_module(module):
    if verbose: print ("teardown_module   module:%s" % module.__name__)
    remove_ncfiles(verbose)

def test_find():

    arguments = ['-u']
    arguments.extend(ncfiles)
    args = ncfind.parse_args(arguments)
    found = ncfind.find_files(args)
    found = [os.path.normpath(file) for file in found]
    assert(len(ncfiles) == len(found))
    assert(found == ncfiles)

    arguments = ['-c']
    arguments.extend(ncfiles)
    args = ncfind.parse_args(arguments)
    found = ncfind.find_files(args)
    assert(found == [])

    files = ncfiles + [ncfiles[0]+'2nc.nc']

    arguments = ['-u']
    arguments.extend(files)
    args = ncfind.parse_args(arguments)
    found = ncfind.find_files(args)
    found = [os.path.normpath(file) for file in found]
    assert(1 == len(found))
    assert(found == files[0:1])

    arguments = ['-c']
    arguments.extend(files)
    args = ncfind.parse_args(arguments)
    found = ncfind.find_files(args)
    found = [os.path.normpath(file) for file in found]
    assert(1 == len(found))
    assert(found == files[1:])


