#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 26 01:52:56 2022

@author: sarahrandall
"""

""" in the file outbreak_common, we have a function that returns a dataframe, 
a good unit test would exist in another file (test.py) and call that function, 
checking if the result is correct"""
import sys
sys.path.insert(0, '/Users/sarahrandall/Python-outbreak-info/outbreak_data') 

""" Imported outbreak_data file from different directory"""

import outbreak_common as oc
test = oc.cases_by_location('USA')
test.to_csv('USA_Data.csv')

import pandas as pd
import unittest

testd = pd.read_csv("/Users/sarahrandall/Projects/USA_Data.csv")
# testcol1 = itanic["Age"]
# testcol2
# testcol3


class TestS_Outbreak_Data(unittest.TestCase):
    
    
    
    def setUp(self):
        fool = oc.cases_by_location('USA')  
        self.data = fool
        
    def checking_rows(self):
        pass
        

# pd.testing.assert_frame_equal(my_df,fool)

    
    
""" One way to do that is to cherry pick out a few rows
 and make sure they get properly returned.  
 The reason why you pick out a few rows is to make sure 
 1. You're getting a 200 response and 
 2. The data gets returned in a proper format.
 Sometimes things get inadvertently changed in terms of format
 and it can lead to failures."""
    

   

    
if __name__ == "__main__":
    unittest.main()










        