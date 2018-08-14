#!/usr/bin/env python
#
# file: /data/isip/exp/tuh_eeg/exp_2546/scripts/tse_update.py
#
# revision history:
#  20180628 (RA): begin script, create outline of functionality
#  20180629 (RA): create functions for script
#  20180702 (RA): continue adding functions
#  20180703 (RA): wrap up rdir/odir functionality
#  20180704 (RA): fixed edf duration bug by implementing separate function
#  20180705 (RA): commented and formatted code to conform to isip standards
#  20180714 (RA): fix bug to prevent null data from printing consecutively
#  20180718 (RA): bug fix for edf file duration 
# 
# This utility script accepts edits tse files to ensure that all time is
# accounted for. Therefore, if any time gaps exist between seizure events,
# a "null" field is added with a 100% confidence level. This way, the entire 
# duration of the file is annotated.
#
#------------------------------------------------------------------------------

# import modules
#
import sys
import os

# import NEDC modules
#
import nedc_cmdl_parser as ncp
import nedc_file_tools as nft
import nedc_edf_reader as ner

#------------------------------------------------------------------------------
#
# global variables are listed here
#
#------------------------------------------------------------------------------

# define the locations of the help and usage
#
HELP_FILE = "/data/isip/exp/tuh_eeg/exp_2546/tse_update.help"
USAGE_FILE = "/data/isip/exp/tuh_eeg/exp_2546/tse_update.help"

# define error output location, if error in edf file caught
#
ERR_FILES = "/data/isip/exp/tuh_eeg/exp_2546/error_files/error_edf.list"

# define default argument values, rdir set to none to force user to provide
#
ODIR = os.getcwd()
RDIRTSE = None
RDIREDF = None

# define TSE data format information
#
START = 0
END = 1
NULL_LOC = 2
CONF_LOC = 3
ZERO = '0.0000'
CONF = '1.000000'
TSE_EXT = '.tse'
EDF_EXT = '.edf'
CHANNEL_FLAG = False

# define tse header characters to parse header
#
HEADER_PREFIX = set(['#', 'version', ''])

# define null insertion characters
#
NULL_INSERT = "null"

#
def main(argv):
    
    # define local variables
    #
    odir = ODIR
    rdir_tse = RDIRTSE
    rdir_edf = RDIREDF
    header_prefix = HEADER_PREFIX
    null_insert = NULL_INSERT
    tse_ext = TSE_EXT
    edf_ext = EDF_EXT
    
    # create command line parser
    #
    parser = ncp.CommandLineParser(USAGE_FILE, HELP_FILE)

    # define command line arguments
    #
    parser.add_argument("ilist", type = str, nargs='*')
    parser.add_argument("-odir", "-o", "-output", type = str)
    parser.add_argument("-rdirtse", "-rtse", "-replacetse", type = str)
    parser.add_argument("-rdiredf", "-redf", "-replaceedf", type = str)
    parser.add_argument("-channel", "-chan", "-ch", action = "store_true")

    # parse the command line
    #
    args = parser.parse_args()

    # print usage file if no cmdl arguments provided and exit
    #
    if not args.ilist:
        parser.print_usage()
        exit(-1)

    # set options and argument values provided and strip trailing ('/')
    #
    if args.odir:
        odir = args.odir.rstrip('/')
    
    if args.rdirtse:
        rdir_tse = args.rdirtse.rstrip('/')
    else:
        print  "%s (%s: %s): error loading the rdir for tse files" % \
            (sys.argv[0], __name__, "main")    
        exit(-1)

    if args.rdiredf:
        rdir_edf = args.rdiredf.rstrip('/')
    else:
        print  "%s (%s: %s): error loading the rdir for edf files" % \
            (sys.argv[0], __name__, "main")
        exit(-1)

    # if channel argument provided with any input, channel flag is set 
    # to true
    #
    if args.channel == True:
        channel_flag = True
        CHANNEL_FLAG = True
    else:
        channel_flag = False

    # load tse file list
    #
    flist = nft.get_flist(args.ilist[0])

    # loop over file lists provided on command line
    #
    for tse_file in flist:
        
        # break down tse file into header/data
        #
        tse_header, tse_data = get_tse_data(tse_file, header_prefix) 
        
        # check if channel flag is true and act accordingly
        #
        if channel_flag == True:
         
            # get and remove channel info from tse filepath for 
            # odir/rdir manipulations
            #
            channel_info = tse_file[-10:-4]
            tse_file = tse_file.replace(channel_info, '')

        else:
            channel_info = ''
			
        # get file name and manipulate for rdir/odir
        #
        fname = os.path.basename(tse_file)
        edf_file = fname.replace(tse_ext, edf_ext)
        fdir = os.path.dirname(tse_file)
        edf_fdir = fdir.replace(rdir_tse, rdir_edf)
        edf_file = os.path.join(edf_fdir, edf_file)
        ofile = tse_file.replace(rdir_tse, odir)
        of_dir = os.path.dirname(ofile)
        
        # check if directory of ofile exists, create if not
        #
        if not os.path.exists(of_dir):
            os.makedirs(of_dir)
            
        # try to get edf duration, if error, print edf to error file
        #
        try:
            end_duration = get_edf_duration(edf_file)
            
            # insert null data where gaps in time exist
            #
            tse_data = insert_null_data(tse_data, end_duration)
            
            # write tse data to output file
            #
            merge_write_tse(tse_header, tse_data, ofile, channel_info, channel_flag)

        except:
            # write edf to a error file path
            #
            write_edf_to_err(edf_file)
        
    # exit gracefully
    #
    return
#
# end of main

#------------------------------------------------------------------------------
#
# Functions are listed here
#
#------------------------------------------------------------------------------

# function to append edf file to file list of error edf duration files
#
def write_edf_to_err(edf_fname_a):

    # check if dirname path exists, then append to file
    #
    if not os.path.exists(os.path.dirname(ERR_FILES)):
        os.makedirs(os.path.dirname(ERR_FILES))
    with open(os.path.basename(ERR_FILES), 'a+') as f:
        f.write("%s\n" % edf_fname_a)

    # exit gracefully
    #
    return
#
# end of function

# function to retrieve edf duration from edf file and return as string 
#
def get_edf_duration(edf_fname_a):

    # open edf file and read duration bytes
    #
    with open(edf_fname_a, 'rb')as f:
        
        # go to beginning of n_records then append trailing format zeroes
        #
        f.seek(236, 0)
        nrecords = f.read(8).strip()
        string_len_d = str(int(nrecords)) + '.0000'

    # return string duration gracefully
    #
    return string_len_d
#
# end of function

# function to merge tse header and data to an output path
#
def merge_write_tse(header_a, data_a, odir_a, chan_info, chan_flag):

    # add channel info if channel flag provided
    #
    if chan_flag == True:
        odir_a = odir_a[:-4] + chan_info + odir_a[-4:]

    # open output dir and write header and data as specified
    #
    with open(odir_a, 'w') as f:
        
        # write header as space delimited
        #
        for line in header_a:
            f.write("%s\n" % ' '.join(line))
        
        # write data as tab delimited
        #
        for line in data_a:
            f.write("%s\n" % '\t'.join(line))
            
    # exit gracefully
    #
    return
#
# end of function

# function to parse/separate header and data from tse file
#
def get_tse_data(tse_file_a, header_prefix_a):
 
    # initialize lists for header/data
    #
    tse_header_d = []
    tse_data_d = []
    
    # open tse file, read lines in the file, and split lines
    #
    with open(tse_file_a) as f:
        for line in f.readlines():
            line = line.split()

            # check if line exists or if the first character indicates
            # header
            #
            if not line or line[START] in header_prefix_a:
                tse_header_d.append(line)
            
            # else test if the first entry can be converted to float
            # indicating that it is a start time
            #
            else:
                try:
                    float(line[START])
                    tse_data_d.append(line)
                except:
                    pass
    # return header/data lists gracefully
    #
    return tse_header_d, tse_data_d
#
# end of function

# function to insert null data as per the goal of the script
# if gaps in timestamps for seizure events exist, fill with null data
# with confidence level of 1.0
#
def insert_null_data(tse_data_a, end_duration_a):
    
    # check if values begin at zero, if not, insert zero null value
    #
    if tse_data_a[START][START] != ZERO:
        tse_data_a.insert(START, [ZERO, tse_data_a[START][START], \
                            NULL_INSERT, CONF])
    
    # check if end of edf duration exceeds end tse value, if so, insert
    # null at the end of the tse file. [:-5] removes trailing 0's from string
    #
    if int(tse_data_a[-1][END][:-5]) < int(end_duration_a[:-5]):
        tse_data_a.append([tse_data_a[-1][END], end_duration_a, \
                             NULL_INSERT, CONF])
        
    # loop through list and insert null data where time gaps exist
    #
    line = 0
    while line < len(tse_data_a)-1:
        if tse_data_a[line][END] != tse_data_a[line+1][START]:
            tse_data_a.insert(line+1, [tse_data_a[line][END], \
                                tse_data_a[line+1][START], NULL_INSERT, \
                                CONF])
        line += 1
    
    # loop through list and remove consecutive null data if exists
    #
    line = 0
    while line < len(tse_data_a)-1:
        if tse_data_a[line][NULL_LOC] == NULL_INSERT and \
           tse_data_a[line+1][NULL_LOC] == NULL_INSERT:
        
            # set end time to end time for the repeat
            #
            tse_data_a[line][END] = tse_data_a[line+1][END]
            
            # remove repeat
            #
            tse_data_a.pop(line+1)
        line += 1
    
    # return tse header gracefully
    #
    return tse_data_a
# 
# end of function

# begin gracefully
#
if __name__ == "__main__":
    main(sys.argv[0:])

# 
# end of file
