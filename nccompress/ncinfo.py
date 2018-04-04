#!/usr/bin/env python

from netCDF4 import Dataset, MFDataset
import numpy as np
import numpy.ma as ma
import os
import sys
import math
import operator
import itertools as it
import argparse
from warnings import warn

def ncinfo(files, hidedims, ignoretime, units, vars=None):

    if isinstance(files, list):
        try:
            ncobj = MFDataset(files)
        except Exception as e:
            warn("Could not aggregate datasets, python library returned: "+str(e))
            return
    else:
        print()
        print(files)
        ncobj = Dataset(files,'r')

    varnames = ncobj.variables.keys()
    varname_maxlen =  len(max(varnames, key=len))

    pr_varnames = []
    pr_dimensions = []
    pr_longnames = []

    for varname in varnames:

        var = ncobj.variables[varname]

        if "time" == varname.lower():
            if not var.ndim == 1:
                warn("I don't understand two dimensional time dimensions")
                continue
            # Get our time axis
            nsteps = len(var)
            try:
                unit = var.__getattribute__("units").partition(' ')[0]
            except AttributeError:
                unit = 'None'
            if nsteps > 1:
                print("Time steps: ",nsteps," x ",var[1]-var[0],unit)
            elif nsteps == 1:
                print("Time : ",var[0],unit)
            continue

        if ignoretime and "time" in varname.lower():
            continue

        if vars is not None:
            if varname not in vars: continue

        if var.ndim == 1:
            dims = ncobj.variables[varname].dimensions
            if hidedims and dims[0] == varname:
                # This is a dimension variable, ignore
                continue
            if ignoretime and dims[0] == "time":
                # Time bounds stuff also ignore
                continue
        # fmt = '{0:{1}} ::  {2:<22}  :: {3}'

        try:
            long_name =  var.__getattribute__("long_name")
        except AttributeError:
            long_name =  ''

        if units:
            try:
                unit =  "(" + var.__getattribute__("units") + ")"
            except AttributeError:
                unit =  ''
            long_name = " ".join([long_name,unit])

        pr_varnames.append(str(varname))
        pr_dimensions.append(str(var.shape))
        pr_longnames.append(str(long_name))

    fmt = '{0:{1}} :: {2:{3}} :: {4}'
    pr_varnames_maxlen = len(max(pr_varnames, key=len))
    pr_dimensions_maxlen = len(max(pr_dimensions, key=len))
    for varstr, dimstr, namestr in zip(pr_varnames, pr_dimensions, pr_longnames):
        print(fmt.format(varstr,pr_varnames_maxlen,dimstr,pr_dimensions_maxlen,namestr))


def parse_args(arglist):
    """
    Parse arguments given as list (arglist)
    """

    parser = argparse.ArgumentParser(description="Output summary information about a netCDF file")
    parser.add_argument("-v","--verbose", help="Verbose output", action='store_true')
    parser.add_argument("-t","--time", help="Show time variables", action='store_true')
    parser.add_argument("-d","--dims", help="Show dimensions", action='store_true')
    parser.add_argument("-a","--aggregate", help="Aggregate multiple netCDF files into one dataset", action='store_true')
    parser.add_argument("-va","--vars", help="Show info for only specify variables", action='append')
    parser.add_argument("-u","--units", help="Show units", action='store_true')
    parser.add_argument("inputs", help="netCDF files", nargs='+')

    return parser.parse_args(arglist)

def main(args):
    
    verbose = args.verbose

    if args.aggregate:
        ncinfo(args.inputs, not args.dims, not args.time, args.units, args.vars)
        # ncinfo(args.inputs, not args.dims, not args.time)
    else:
        for ncinput in args.inputs:
            ncinfo(ncinput, not args.dims, not args.time, args.units, args.vars)
                
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
