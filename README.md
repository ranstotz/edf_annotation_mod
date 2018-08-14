# edf_annotation_mod

The tse_update.py script revises seizure annotation text files (TSE files) to include "null" data. The
script reads EDF (European Data Format) binary headers to get the duration of the EEG, then
fills in "null" annotations where necessary.

The script uses a command line interface to input replacement directories for both EDF and
TSE files, output directory, a channel flag (EEG related), and a file list (text file of file
paths).

See '.usage' and '.help' files for more details.
