from netCDF4 import Dataset
import numpy as np
from glob import glob
import os

def which(program):
    import os
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def remove_ncfiles(verbose=True):
    for file in glob("*.nc"):
        if (verbose): print("Removing {}".format(file))
        os.remove(file)

def make_simple_netcdf_file(ncfiles):

    ## nx = 120
    ## ny = 600

    ## rootgrp = nc.Dataset("simple_xy.nc", "w", format="NETCDF3_CLASSIC")
    ## xdim = rootgrp.createDimension("x", 600)
    ## ydim = rootgrp.createDimension("y", 120)
    ## data = rootgrp.createVariable("data","f4",("y","x"))
    ## data[:] = range(0,600) * 120
    
    # the output array to write will be nx x ny
    ny = 600; nx = 120
    # open a new netCDF file for writing.
    ncfile = Dataset(ncfiles[0],'w',format="NETCDF4_CLASSIC") 
    # create the output data.
    data_out = np.arange(nx*ny)/100. # 1d array
    data_out.shape = (nx,ny) # reshape to 2d array
    # create the x and y dimensions.
    ncfile.createDimension('x',nx)
    ncfile.createDimension('y',ny)
    # create the variable (4 byte integer in this case)
    # first argument is name of variable, second is datatype, third is
    # a tuple with the names of dimensions.
    data = ncfile.createVariable('data',np.dtype('float32').char,('x','y'))
    data.setncattr("Unhidden","test")
    # write data to variable.
    data[:] = data_out
    # close the file.
    ncfile.close()

if __name__ == "__main__":

    make_simple_netcdf_file(['simple_xy.nc'])
