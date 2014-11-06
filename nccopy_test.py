#!/usr/bin/env python
from __future__ import print_function
import glob
import subprocess
import os
import sys
import netCDF4 as nc

# debug=True
debug=False

path='./'
tmpdir='tmp'
timecmd='/usr/bin/time'

nccopy='nccopy'

def run_nccopy(ncfile,outdir,level='4',limited=False,shuffle=False,chunking=None):
    copyobj = {}
    # The format string for the time command
    #   %e     (Not in tcsh.) Elapsed real time (in seconds).
    #   %S     Total number of CPU-seconds that the process spent in kernel mode.
    #   %U     Total number of CPU-seconds that the process spent in user mode.
    #   %M     Maximum resident set size of the process during its lifetime, in Kbytes.
    fmt = "%e %S %U %M"
    outfile = os.path.join(path,outdir,ncfile)
    cmd = ['time','-f',fmt,nccopy,'-d',str(level)]
    if (limited): cmd.append('-u')
    if (shuffle): cmd.append('-s')
    if (chunking):
        cmd.append('-c')
        cmd.append(chunking)
    cmd.append(ncfile)
    cmd.append(outfile)
    if (debug):
        print (' '.join(cmd))
    else:
        try:
            output = subprocess.check_output(cmd,stderr=subprocess.STDOUT)
            # return output.split(),float(os.path.getsize(outfile))/float(os.path.getsize(ncfile))
            copyobj = {
                'times' : output.split(),
                'orig_size' : os.path.getsize(outfile),
                'comp_size' : os.path.getsize(ncfile),
                'dlevel' : level,
                'shuffle' : shuffle,
                'limited' : limited
                      }
            return copyobj
        except:
            raise

# all_files=glob.glob(os.path.join(path,'*.nc'))
# all_files=['TFLUX.0000691200.nc']
# all_files=['clearly_not_a_real_file.nc']

for arg in sys.argv[1:]:
# for n in range(len(all_files)):
    # Open the data set and get some info on the dimensions
    ## data = Dataset(all_files[n], 'r')
    ## for (dimname,dimsize) in data.dimensions.items():
    ##     for d in range(dimsize/4,dimsize,dimsize/4)
    for deflate in range(0,10):
        for removeunlim in (True,False):
            for shuff in (True,False):
                try:
                    copydict = run_nccopy(arg,tmpdir,level=deflate,limited=removeunlim,shuffle=shuff)
                except:
                    print("Something went wrong with {}".format(arg))
                    continue
                print("{} d = {} Conv unlim: {:d} Shuffle: {:d} {} s {} s {} s {} Kb {:0.4}".format(arg, deflate, removeunlim, shuff, copydict['times'][0], copydict['times'][1], copydict['times'][2], copydict['times'][3], float(copydict['orig_size'])/float(copydict['comp_size'])),end='\n')
 
    
print()

