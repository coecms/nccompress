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
import os
from utils import make_simple_netcdf_file, remove_ncfiles, which
import subprocess
import pdb
from nccompress import nccompress

verbose = True

ncfiles =['simple_xy.nc']

def setup_module(module):
    if verbose: print ("setup_module      module:%s" % module.__name__)
    remove_ncfiles(verbose)
    make_simple_netcdf_file(ncfiles)
 
def teardown_module(module):
    if verbose: print ("teardown_module   module:%s" % module.__name__)
    remove_ncfiles(verbose)

def test_nccopy():

    if which('cdo') is None:
        print("Could not find cdo in path")
        assert(False)
    else:
        print(which('cdo'))

    if which('nccopy') is None:
        print("Could not find nccopy in path")
        assert(False)
    else:
        print(which('nccopy'))

    cmd = ['nccopy', '-d', '3', '-s', 'simple_xy.nc', 'simple_xy.nccopy.nc']

    output = ''

    try:
        output = subprocess.check_output(cmd,stderr=subprocess.STDOUT)
    except Exception as e:
        # pdb.set_trace()
        print("exception : {} {}".format(e,e.output))
    else:
        pass


    # Use a function from nccompress which calls cdo diffn. First test it with
    # the same file
    assert nccompress.are_equal('simple_xy.nc','simple_xy.nc',verbose=True)

    assert nccompress.are_equal('simple_xy.nc','simple_xy.nccopy.nc',verbose=True)

