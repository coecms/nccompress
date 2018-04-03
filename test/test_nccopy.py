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

import pytest
import imp
import os
from utils import make_simple_netcdf_file, remove_ncfiles, which
import subprocess
import pdb

# Test is run from directory above this one, location of the source file
nc_compress = imp.load_source('nc_compress', "nc_compress")

verbose = True

ncfiles =['simple_xy.nc']

def setup_module(module):
    if verbose: print ("setup_module      module:%s" % module.__name__)
    remove_ncfiles(verbose)
    make_simple_netcdf_file(ncfiles)
 
def teardown_module(module):
    if verbose: print ("teardown_module   module:%s" % module.__name__)
    # remove_ncfiles(verbose)

def test_nccopy():

    # pdb.set_trace()

    if which('cdo') is None:
        print("Could not find cdo in path")
        assert(False)
    else:
        print(which('cdo'))

    cmd = ['nccopy', '-d', '3', '-s', '-m', '50000000', 'simple_xy.nc', 'simple_xy.nccopy.nc']

    output = ''

    try:
        output = subprocess.check_output(cmd,stderr=subprocess.STDOUT)
        # print("Try : {}".format(output))
    except Exception as e:
        print("Except : {}".format(e))
    else:
        pass
        # print("Else : {}".format(output))


    # Use a function from nc_compress which calls cdo diffn. First test it with
    # the same file
    assert nc_compress.are_equal('simple_xy.nc','simple_xy.nc',verbose=True)

    assert nc_compress.are_equal('simple_xy.nc','simple_xy.nccopy.nc',verbose=True)

