=============================
nccompress
=============================

Tool to compress directories of netCDF files

.. image:: https://travis-ci.org/coecms/nccompress.svg?branch=master
  :target: https://travis-ci.org/coecms/nccompress
.. image:: https://circleci.com/gh/coecms/nccompress.svg?style=shield
  :target: https://circleci.com/gh/coecms/nccompress
.. content-marker-for-sphinx

   nccompress
==========

The nccompress package has been written to facilitate compressing netcdf
files. Although nccompress can work on single files, it is particularly
useful to compress all uncompressed files under whole directory trees.
This can allow users to compress files regularly using the same script
each time.

The nccompress package consists of three python programs, ncfind, nc2nc
and nccompress. nc2nc can copy netCDF files with compression and an
optimised chunking strategy that has reasonable performance for many
datasets. His two main limitations: it is slower than some other
programs, and it can only compress netCDF3 or netCDF4 classic format.
There is more detail in the following sections.

The convenience utility ncinfo is also included, and though it has no
direct relevance to compression, it is a convenient way to get a summary
of the contents of a netCDF file.

Identifying files to be compressed
----------------------------------

ncfind, part of the nccompress package, can be used to find netCDF files
and discriminate between compressed and uncompressed:

::

    $ ncfind -h
    usage: ncfind [-h] [-r] [-u | -c] [inputs [inputs ...]]

    Find netCDF files. Can discriminate by compression

    positional arguments:
      inputs              netCDF files or directories (-r must be specified to
                          recursively descend directories). Can accept piped
                          arguments.

    optional arguments:
      -h, --help          show this help message and exit
      -r, --recursive     Recursively descend directories to find netCDF files
                          (default False)
      -u, --uncompressed  Find only uncompressed netCDF files (default False)
      -c, --compressed    Find only compressed netCDF files (default False)
     

There are other methods for finding files, namely the unix utility find
utility. For example, to find all files in the directory "directoryname"
which end in ".nc":

::

    find directoryname -iname "*.nc"

However, if your netCDF files do not use the convention of ending in
".nc" or cannot be systematically found based on filename, you can use
the ncfind to recursively descend into a directory structure looking for
netCDF files:

::

    ncfind -r directoryname

You can refine the search further by requesting to return only those
files that are uncompressed:

::

    ncfind -r -u directoryname

If you want to find out how much space these uncompressed files occupy
you can combine this command with other unix utilities such as xargs and
du:

::

    ncfind -r -u directoryname | xargs du -h

du is the disk usage utility. The output looks something like this:

::

    67M     output212/ice__212_223.nc
    1003M   output212/ocean__212_223.nc
    1.1G    total

It is even possible to combine the system find utility with ncfind,
using a unix pipe (|). This command will find all files ending in ".nc",
pipe the results to ncfind, and only those that are uncompressed will be
printed to the screen:

::

    find directoryname -iname "*.nc" | ncfind -u


Batch Compressing files
----------------------

Having identified where the netCDF files you wish to compress are
located, there is a convenience program, nccompress, which can be used
to easily step through and compress each file in turn:

::

    $ nccompress --help
    usage: nccompress [-h] [-d {1-9}] [-n] [-s CHUNKSIZE] [-b BUFFERSIZE]
                    [-t TMPDIR] [-v] [-r] [-o] [-m MAXCOMPRESS] [-p] [-f] [-c]
                    [-pa] [-np NUMPROC] [-ff FROMFILE] [--nccopy] [--timing]
                    [inputs [inputs ...]]

    Run nc2nc (or nccopy) on a number of netCDF files

    positional arguments:
    inputs                netCDF files or directories (-r must be specified to
                            recursively descend directories). Can accept piped
                            arguments.

    optional arguments:
    -h, --help            show this help message and exit
    -d {1-9}, --dlevel {1-9}
                            Set deflate level. Valid values 0-9 (default=5)
    -n, --noshuffle       Don't shuffle on deflation (default is to shuffle)
    -s CHUNKSIZE, --chunksize CHUNKSIZE
                        Set chunksize - total size of one chunk in KiB
                        (default=64), nc2nc only
    -b BUFFERSIZE, --buffersize BUFFERSIZE
                        Set size of copy buffer in MiB (default=500), nc2nc only
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
    -pa, --parallel       Compress files in parallel
    -np NUMPROC, --numproc NUMPROC
                            Specify the number of processes to use in parallel
                            operation
    -ff FROMFILE, --fromfile FROMFILE
                            Read files to be compressed from a text file
    --nccopy              Use nccopy instead of nc2nc (default False)
    --timing              Collect timing statistics when compressing each file
                            (default False)


The simplest way to invoke the program would be with a single file:

::

    nccompress ice_daily_0001.nc

or using a wildcard expression:

::

    nccompress ice*.nc

You can also specify one or more directory names in combination with the
recursive flag (`-r`) and the program will recursively descend into those
directories and find all netCDF files contained therein. For example, a
directory listing might look like so:

::

    $ ls data/
    output001  output003  output005  output007  output009  restart001  restart003  restart005  restart007  restart009
    output002  output004  output006  output008  output010  restart002  restart004  restart006  restart008  restart010

with a number of sub-directories, all containing netCDF files.

Note that the only way `nccompress` can determine if files are netCDF
format is to try and open them. If there are large numbers of non-netCDF
files, or even already compressed netCDF files, in the directory tree 
this can severely slow down the process. In this case it is best to
remove non-essential files before running this tool, or use some other
approaches detailed below.

It is a good idea to do a trial run and make sure it functions properly.
For example, this will compress the netCDF files in just one of the
directories:

::

    nccompress -p -r data/output001

Once completed there will be a new subdirectory called `tmp.nc_compress`
inside the directory `output001`. It will contain compressed copies of all
the netCDF files from the directory above. You can check the compressed
copies to make sure they are correct. The paranoid option (`-p`) calls
`nco diffn` to check that the variables contained in the two files are
the same. The `cdo` program must be present in your `PATH`. 
You can use the paranoid option routinely, thought it will
make the process more time consuming. It is a good idea to use it in the
testing phase. You should also check the compressed copies manually to
make sure they look ok, and if so, re-run the command with the `-o` option
(overwrite):

::

    nccompress -r -o data/output001

and it will find the already compressed files, copy them over the
originals and delete the temporary directory `tmp.nc_compress`. It won't
try to compress the files again. It also won't compress already
compressed files, so, for example, if you were happy that the
compression was working well you could compress the entire data
directory, and the already compressed files in `output001` will not be
re-compressed.

So, by default, nccompress **does not overwrite the original files**.
If you invoke it without the `-o` option it will create compressed
copies in the tmp.nc_compress subdirectory and leave them there, which
will consume more disk space! This is a feature, not a bug, but you need
to be aware that this is how it functions.

With large variables, which usually means large files (> 1GB) it is a
good idea to specify a larger buffer size with the `-b` option, as it
will run faster. On raijin this may mean you need to run interactively
with a higher memory (~10GB) or submit it as a copyq job. A typical
buffer size might be 1000 -> 5000 (1->5 GB).

It is also possible to use wildcards type operations, e.g.

::

    nccompress -r -o output*

    nccompress -r -o output00[1-5]

    nccompress -r -o run[1-5]/output*/ocean*.nc random.nc ice*.nc

or use a tool like `find` to locate the files to be compressed and
pipe that into `nccompress`:

::

    find . -iname "*.nc" | nccompress -o

Using `find` to locate files can be a good approach if the files to
be compressed are a relatively small proportion of all the files
in the directory tree. 

Optionally a file containing the paths to the files to be compressed
can be specified. One filepath per line.

This can be useful to use other tools to modify
the list as required. Again, find can be used to generate a suitable
list, e.g.

::

    find . -iname "*.nc" > list.txt
    nccompress -o --filelist list.txt

The nccompress program handles finding files/directories etc, it
calls nc2nc to do the compression. Using the option `--nccopy` forces
nccompress to use the nccopy program in place of `nc2nc`, though the
netcdf package must already be loaded for this to work.

You can tell nccompress to work on multple files simultaneously with
the `-pa` option. By default this will use all the physical processors
on the machine, or you can specify how many simultaneous processes you
want to with `-np`, e.g.

::

    nccompress -r -o -np 16 run[1-5]/output*/ocean*.nc random.nc ice*.nc

will compress 16 netCDF files at a time (the -np option implies parallel
option). As each directory is processed before beginning on a new
directory there will be little reduction in execution time if there are
few netCDF files in each directory.

nc2nc
-----

The nc2nc program was written because no existing tool had a generalised
per variable chunking algorithm. The total chunk size is defined to be
the file system block size (4096KB). The dimensions of the chunk are
sized to be as close as possible to the same ratio as the dimensions of
the data, with the limits that no dimension can be less than 1. This
chunking scheme performs well for a wide range of data, but there will
always be cases for certain types of access, or variable shape that this
is not optimal. In those cases a different approach may be required.

Be aware that nc2nc takes at least twice as long to compress an
equivalent file as nccopy. In some cases with large files containing
many variables it can be up to five times slower.

You can use nc2nc "stand alone". It has a couple of extra features that
can only be accessed by calling it directly:

::

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

With the vars option (-va) it is possible to select out only a subset of
variables to be copied to the destination file. By default the output
file is netCDf4 classic, but this can be changed to netCDF4 using the
`-c` option. It is also possible to specify a minimum dimension size for
the chunks (-m). This may be desirable for a dataset that has one
particularly long dimension,. The chunk dimensions would mirror this and
be very large in this direction . If fast access is required from slices
orthogonal to this direction performance might be improved setting this option to a number greater than 1.

## ncinfo

ncinfo is a convenient way to get a summary of the contents of a netCDF file.
```
./ncinfo -h
usage: ncinfo [-h] [-v] [-t] [-d] [-a] [-va VARS] inputs [inputs ...]

Output summary information about a netCDF file

positional arguments:
  inputs                netCDF files

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose output
  -t, --time            Show time variables
  -d, --dims            Show dimensions
  -a, --aggregate       Aggregate multiple netCDF files into one dataset
  -va VARS, --vars VARS
                        Show info for only specify variables

```
By default it prints out a simple summary of the variables in a netCDF file, but omitting dimensions and time related variables. e.g.
```
ncinfo output096/ocean_daily.nc

output096/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x    :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y    :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity
geolon_t :: (1080, 1440)      :: tracer longitude
geolat_t :: (1080, 1440)      :: tracer latitude
geolon_c :: (1080, 1440)      :: uv longitude
geolat_c :: (1080, 1440)      :: uv latitude

```
If you specify more than one file it will print the information for each file in turn
```
ncinfo output09?/ocean_daily.nc

output096/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x    :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y    :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity
geolon_t :: (1080, 1440)      :: tracer longitude
geolat_t :: (1080, 1440)      :: tracer latitude
geolon_c :: (1080, 1440)      :: uv longitude
geolat_c :: (1080, 1440)      :: uv latitude

output097/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x    :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y    :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity
geolon_t :: (1080, 1440)      :: tracer longitude
geolat_t :: (1080, 1440)      :: tracer latitude
geolon_c :: (1080, 1440)      :: uv longitude
geolat_c :: (1080, 1440)      :: uv latitude

output098/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x    :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y    :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity
geolon_t :: (1080, 1440)      :: tracer longitude
geolat_t :: (1080, 1440)      :: tracer latitude
geolon_c :: (1080, 1440)      :: uv longitude
geolat_c :: (1080, 1440)      :: uv latitude

output099/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x    :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y    :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity
geolon_t :: (1080, 1440)      :: tracer longitude
geolat_t :: (1080, 1440)      :: tracer latitude
geolon_c :: (1080, 1440)      :: uv longitude
geolat_c :: (1080, 1440)      :: uv latitude
```
If the files have the same structure it is possible to aggregate the data and display it as if it were contained in a single dataset:
```
ncinfo -a output09?/ocean_daily.nc

Time steps:  1460  x  1.0 days
tau_x    :: (1460, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y    :: (1460, 1080, 1440) :: j-directed wind stress forcing v-velocity
geolon_t :: (1080, 1440)       :: tracer longitude
geolat_t :: (1080, 1440)       :: tracer latitude
geolon_c :: (1080, 1440)       :: uv longitude
geolat_c :: (1080, 1440)       :: uv latitude
```
You can also just request variables you are interested in to be output:
```
ncinfo -va tau_x -va tau_y output09?/ocean_daily.nc 

output096/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity

output097/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity

output098/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity

output099/ocean_daily.nc
Time steps:  365  x  1.0 days
tau_x :: (365, 1080, 1440) :: i-directed wind stress forcing u-velocity
tau_y :: (365, 1080, 1440) :: j-directed wind stress forcing v-velocity
```
