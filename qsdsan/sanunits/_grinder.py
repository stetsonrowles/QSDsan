
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 21 19:55:59 2021

@author: lewisrowles
"""

'''
QSDsan: Quantitative Sustainable Design for sanitation and resource recovery systems
Copyright (C) 2020, Quantitative Sustainable Design Group

This module is developed by:
    Lewis Rowles <stetsonsc@gmail.com>

This module is under the University of Illinois/NCSA Open Source License.
Please refer to https://github.com/QSD-Group/QSDsan/blob/master/LICENSE.txt
for license details.
'''
# %%


import numpy as np
from qsdsan import SanUnit, Construction
from qsdsan.utils.loading import load_data, data_path
import os

__all__ = ('Grinder',)

#path to csv with all the inputs
#data_path = '/Users/lewisrowles/opt/anaconda3/lib/python3.8/site-packages/exposan/biogenic_refinery/_grinder.csv'
data_path += 'sanunit_data/_grinder.tsv'

### 
class Grinder(SanUnit):
    '''
    Grinder is used to break up solids.

    
    Reference documents
    -------------------
    N/A
    
    Parameters
    ----------
    ins : WasteStream
        Solids
    outs : WasteStream 
        Solids

        
    References
    ----------
    .. N/A
    
    '''
    

    def __init__(self, ID='', ins=None, outs=(), **kwargs):
        
        SanUnit.__init__(self, ID, ins, outs, F_BM_default=1)

# load data from csv each name will be self.name    
        data = load_data(path=data_path)
        for para in data.index:
            value = float(data.loc[para]['expected'])
            setattr(self, para, value)
        del data
        
        for attr, value in kwargs.items():
            setattr(self, attr, value)




        
# define the number of influent and effluent streams    
    _N_ins = 1
    _N_outs = 1

# in _run: define influent and effluent streams and treatment processes 
    def _run(self):
        waste_in = self.ins[0]
        waste_out = self.outs[0]
        waste_out.copy_like(self.ins[0])

        moisture_content = (waste_in.imass['H2O'] / waste_in.F_mass) # fraction
        TS_in = waste_in.F_mass - waste_in.imass['H2O'] # kg TS dry/hr

        # set necessary moisture content of effluent as 35%
        waste_out.imass['H2O'] = (0.65/0.35) * TS_in # fraction

