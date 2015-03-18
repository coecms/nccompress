#!/usr/bin/env python

import imp
from netCDF4 import Dataset
from numpy import array, arange, dtype
from numpy.testing import assert_array_equal, assert_array_almost_equal
import sys
import os

# Make sure we find nc2nc in the directory above
os.environ['PATH'] = '..' + os.pathsep + os.environ['PATH']

nc_compress = imp.load_source('nc_compress', "../nc_compress")

def test_is_compressed():
    assert not nc_compress.is_compressed('simple_xy.nc')
    assert nc_compress.is_compressed('simple_xy.nc2nc.nc')
    # Test classic model
    assert not nc_compress.is_compressed('simple_xy.classic.nc')

def test_is_compressed():
    retdict = nc_compress.run_nccopy('simple_xy.nc','simple_xy.run_nccopy.nc',level=3,verbose=False,shuffle=True)
    assert (retdict['orig_size']/retdict['comp_size'] >= 5.)
    assert (retdict['dlevel'] == 3)
    assert retdict['shuffle']
    retdict = nc_compress.run_nc2nc('simple_xy.nc','simple_xy.run_nc2nc.nc',level=3,verbose=False,shuffle=True)
    assert (retdict['orig_size']/retdict['comp_size'] >= 5.)
    assert (retdict['dlevel'] == 3)
    assert retdict['shuffle']

def test_are_equal():
    assert nc_compress.are_equal('simple_xy.nc','simple_xy.run_nc2nc.nc',verbose=True)
    assert nc_compress.are_equal('simple_xy.run_nc2nc.nc','simple_xy.run_nccopy.nc',verbose=True)
    assert not nc_compress.are_equal('simple_xy.nc','simple_xy.2nc_quantised.nc',verbose=True)
    # os.unlink('simple_xy.run_nc2nc.nc')
