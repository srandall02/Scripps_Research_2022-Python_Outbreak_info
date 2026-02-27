#import pytest
import pandas as pd

VOC_FILE = "resources/voc.txt"
VOI_FILE = "resources/voi.txt"

SEQ_FILE = "resources/sequences.csv"

def test_voc_file_correct_format():
    with open( VOC_FILE, "r" ) as voc_file:
        assert all( len( line.split( "," ) ) == 2 for line in voc_file ), "VOC file is not the proper format. Two columns are not found in every file."

def test_voi_file_correct_format():
    with open( VOI_FILE, "r" ) as voi_file:
        assert all( len( line.split( "," ) ) == 2 for line in voi_file ), "VOI file is not the proper format. Two columns are not found in every file."

def test_all_zipcodes_decimal():
    seqs = pd.read_csv( SEQ_FILE )
    try:
        _ = pd.to_numeric( seqs["zipcode"], errors="raise", downcast="integer" )
    except ValueError:
        # TODO: determine what values are causing the error. Something like iterate through rows, try and convert, if
        #  fail add to a list, assert list is empty at the end.
        assert False, "Some values in zipcode column are not able to be parsed to floats."