===nccompress=== 

The nccompress package consists of three python programs, ncfind, nc2nc and nc_compress. nc2nc can copy netCDF files with compression and an optimised chunking strategy that has reasonable performance for many datasets. This two main limitations: it is slower than some other programs, and it can only compress netCDF3 or netCDF4 classic format. There is more detail in the following sections.

==Identifying files to be compressed== 

ncfind, part of the nccompress package, can be used to find netCDF files and discriminate between compressed and uncompressed:

[[code]]
$ ncfind -h
usage: ncfind [-h] [-r] [-u | -c] [inputs [inputs ...]]

Find netCDF files. Can discriminate by compression

positional arguments:
  inputs              netCDF files or directories (-r must be specified to
                      recursively descend directories). Can accept piped
                      arguments.

optional arguments:
  -h, --help          show this help message and exit
  -r, --recursive     Recursively descend directories compressing all netCDF
                      files (default False)
  -u, --uncompressed  Find only uncompressed netCDF files (default False)
  -c, --compressed    Find only compressed netCDF files (default False)


[[code]]
There are other methods for finding files, namely the unix utility find utility. For example, to find all files in the directory "directoryname" which end in ".nc":
[[code]]
find directoryname -iname "*.nc"

[[code]]
However, if your netCDF files do not use the convention of ending in ".nc" or cannot be systematically found based on filename, you can use the ncfind to recursively descend into a directory structure looking for netCDF files:
[[code]]
ncfind -r directoryname
[[code]]
You can refine the search further by requesting to return only those files that are uncompressed:
[[code]]
ncfind -r -u directoryname
[[code]]
If you want to find out how much space these uncompressed files occupy you can combine this command with other unix utilities such as xargs and du:
[[code]]
ncfind -r -u directoryname | xargs du -h
[[code]]
du is the disk usage utility. The output looks something like this:
[[code]]
67M     output212/ice__212_223.nc
1003M   output212/ocean__212_223.nc
1.1G    total

[[code]]
It is even possible to combine the system find utility with ncfind, using a unix pipe (|). This command will find all files ending in ".nc", pipe the results to ncfind, and only those that are uncompressed will be printed to the screen:
[[code]]
find directoryname -iname "*.nc" | ncfind -u
[[code]]


==Batch Compressing files== 
[[#nc_compress]]
Having identified where the netCDF files you wish to compress are located, there is a convenience program, nc_compress, which can be used to easily step through and compress each file in turn:
[[code]]
$ nc_compress -h
usage: nc_compress [-h] [-d {1-9}] [-n] [-b BUFFERSIZE] [-t TMPDIR] [-v] [-r]
                   [-o] [-m MAXCOMPRESS] [-p] [-f] [-c] [--nccopy]
                   inputs [inputs ...]

Run nc2nc (or nccopy) on a number of netCDF files

positional arguments:
  inputs                netCDF files or directories (-r must be specified to
                        recursively descend directories)

optional arguments:
  -h, --help            show this help message and exit
  -d {1-9}, --dlevel {1-9}
                        Set deflate level. Valid values 0-9 (default=5)
  -n, --noshuffle       Don't shuffle on deflation (default is to shuffle)
  -b BUFFERSIZE, --buffersize BUFFERSIZE
                        Set size of copy buffer in MB (default=50)
  -t TMPDIR, --tmpdir TMPDIR
                        Specify temporary directory to save compressed files
  -v, --verbose         Verbose output
  -r, --recursive       Recursively descend directories compressing all netCDF
                        files (default False)
  -o, --overwrite       Overwrite original files with compressed versions
                        (default is to not overwrite)
  -m MAXCOMPRESS, --maxcompress MAXCOMPRESS
                        Set a maximum compression as a paranoid check on
                        success of nccopy (default is 10, set to zero for no
                        check)
  -p, --paranoid        Paranoid check : run nco ndiff on the resulting file
                        ensure no data has been altered
  -f, --force           Force compression, even if input file is already
                        compressed (default False)
  -c, --clean           Clean tmpdir by removing existing compressed files
                        before starting (default False)
  --nccopy              Use nccopy instead of nc2nc (default False)

[[code]]
The simplest way to invoke the program would be with a single file:
[[code]]
nc_compress ice_daily_0001.nc
[[code]]
or using a wildcard expression:
[[code]]
nc_compress ice*.nc
[[code]]
You can also specify one or more directory names in combination with the recursive flag (-r) and the program will recursively descend into those directories and find all netCDF files contained therein. For example, a directory listing might look like so:
[[code]]
$ ls data/
output001  output003  output005  output007  output009  restart001  restart003  restart005  restart007  restart009
output002  output004  output006  output008  output010  restart002  restart004  restart006  restart008  restart010
[[code]]
with a number of sub-directories, all containing netCDF files.

It is a good idea to do a trial run and make sure it functions properly. For example, this will compress the netCDF files in just one of the directories:
[[code]]
nc_compress -p -r data/output001
[[code]]
Once completed there will be a new subdirectory called tmp.nc_compress inside the directory output001. It will contain compressed copies of all the netCDF files from the directory above. You can check the compressed copies to make sure they are correct. The paranoid option (-p) calls an nco command to check that the variables contained in the two files are the same. You can use the paranoid option routinely, thought it will make the process more time consuming. It is a good idea to use it in the testing phase. You should also check the compressed copies manually to make sure they look ok, and if so, re-run the command with the -o option (overwrite):
[[code]]
nc_compress -r -o data/output001
[[code]]

and it will find the already compressed files, copy them over the originals and delete the temporary directory tmp.nc_compress. It won't try to compress the files again. It also won't compress already compressed files, so, for example, if you were happy that the compression was working well you could compress the entire data directory, and the already compressed files in output001 will not be re-compressed.

So, by default, nc_compress **does not overwrite the original files**. If you invoke it without the '-o' option it will create compressed copies in the tmp.nc_compress subdirectory and leave them there, which will consume more disk space! This is a feature, not a bug, but you need to be aware that this is how it functions.

With large variables, which usually means large files (> 1GB) it is a good idea to specify a larger buffer size with the '-b' option, as it will run faster. On raijin this may mean you need to run interactively with a higher memory (~10GB) or submit it as a copyq job. A typical buffer size might be 1000 -> 5000 (1->5 GB).

It is also possible to use wildcards type operations, e.g.

[[code]]
nc_compress -r -o output*

nc_compress -r -o output00[1-5]

nc_compress -r -o run[1-5]/output*/ocean*.nc random.nc ice*.nc
[[code]]
The nc_compress program just sorts out finding files/directories etc, it calls nc2nc to do the compression. Using the '--nccopy' forces nc_compress to use the nccopy program in place of nc2nc, though the netcdf package must already be loaded for this to work.

==nc2nc[[#nc2nc]]== 

The nc2nc program was written because no existing tool had a generalised per variable chunking algorithm. The total chunk size is defined to be the file system block size (4096KB). The dimensions of the chunk are sized to be as close as possible to the same ratio as the dimensions of the data, with the limits that no dimension can be less than 1. This chunking scheme performs well for a wide range of data, but there will always be cases for certain types of access, or variable shape that this is not optimal. In those cases a different approach may be required.

Be aware that nc2nc takes at least twice as long to compress an equivalent file as nccopy. In some cases with large files containing many variables it can be up to five times slower.

You can use nc2nc "stand alone". It has a couple of extra features that can only be accessed by calling it directly:
[[code]]
$ nc2nc -h
usage: nc2nc [-h] [-d {1-9}] [-m MINDIM] [-b BUFFERSIZE] [-n] [-v] [-c] [-f]
             [-va VARS] [-q QUANTIZE] [-o]
             origin destination

Make a copy of a netCDF file with automatic chunk sizing

positional arguments:
  origin                netCDF file to be compressed
  destination           netCDF output file

optional arguments:
  -h, --help            show this help message and exit
  -d {1-9}, --dlevel {1-9}
                        Set deflate level. Valid values 0-9 (default=5)
  -m MINDIM, --mindim MINDIM
                        Minimum dimension of chunk. Valid values 1-dimsize
  -b BUFFERSIZE, --buffersize BUFFERSIZE
                        Set size of copy buffer in MB (default=50)
  -n, --noshuffle       Don't shuffle on deflation (default is to shuffle)
  -v, --verbose         Verbose output
  -c, --classic         use NETCDF4_CLASSIC output instead of NETCDF4 (default
                        true)
  -f, --fletcher32      Activate Fletcher32 checksum
  -va VARS, --vars VARS
                        Specify variables to copy (default is to copy all)
  -q QUANTIZE, --quantize QUANTIZE
                        Truncate data in variable to a given decimal
                        precision, e.g. -q speed=2 -q temp=0 causes variable
                        speed to be truncated to a precision of 0.01 and temp
                        to a precision of 1
  -o, --overwrite       Write output file even if already it exists (default
                        is to not overwrite)
[[code]]
With the vars option (-va) it is possible to select out only a subset of variables to be copied to the destination file. By default the output file is netCDf4 classic, but this can be changed to netCDF4 using the '-c' option. It is also possible to specify a minimum dimension size for the chunks (-m). This may be desirable for a dataset that has one particularly long dimension,. The chunk dimensions would mirror this and be very large in this direction . If fast access is required from slices orthogonal to this direction performance might be improved setting this option to a number greater than 1.