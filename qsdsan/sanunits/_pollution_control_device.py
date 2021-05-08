#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar  9 13:41:03 2021

@author: lewisrowles stetson@gmail.com
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
__all__ = ('PollutionControlDevice',)

data_path += 'sanunit_data/_pollution_control_device.tsv'

#data_path = '//Users/lewisrowles/opt/anaconda3/lib/python3.8/site-packages/exposan/biogenic_refinery/_pollution_control_device.csv'

#data_path = os.path.abspath(os.path.dirname('_pollution_control_device.csv'))
# data_path += 'sanunit_data/_pollution_control_device.csv'

### 
class PollutionControlDevice(SanUnit):
    '''
    Pollution Control Device’s primary responsibilities include pollution 
    control and pre heating of the feedstock. 
    Due to the inefficiencies of the pyrolysis process, there are typically 
    pollutants in the exhaust. In order to treat these pollutants, the 
    Biogenic Refinery has a catalyst, similar to a catalytic converter in a 
    car, to ensure destruction of the pollutants before they can be released 
    into the surrounding environment. The process of destroying the pollutants 
    requires the catalyst to maintain temperatures above 315 deg C, and 
    additional energy is released during this process. The temperature of 
    the catalysis is closely monitored because the catalyst material 
    will start to degrade above 615 deg C and could cause the feedstock to 
    prematurely pyrolyze in the fuel auger. 
    
    Reference documents
    -------------------
    N/A
    
    Parameters
    ----------
    ins : WasteStream
        hot gas, fugitive N2O (from Carbonizer Base)
    outs : WasteStream 
        hot gas, fugitive N2O.
            set both as WasteStream 
            others could be:
            Gases consist of SO2_emissions, NOx_emissions, CO_emissions, 
            Hg_emissions, Cd_emissions, As_emissions, Dioxin_Furans_emissions.
            
    References
    ----------
    .. N/A
    
    '''
    

    def __init__(self, ID='', ins=None, outs=(), carbonizer_uptime_ratio=1, **kwargs):
        
        
        SanUnit.__init__(self, ID, ins, outs)

    
        data = load_data(path=data_path)
        for para in data.index:
            value = float(data.loc[para]['expected'])
            setattr(self, para, value)
        del data
        
        for attr, value in kwargs.items():
            setattr(self, attr, value)
    

        
    
    _N_ins = 2
    _N_outs = 2
    
    def _run(self):
        heat_in, N2O_in = self.ins
        heat_out, N2O_out = self.outs
        heat_in.phase = N2O_in.phase = 'g'
        heat_out.phase = N2O_out.phase = 'g'
        
        self.daily_run_time = self.uptime_ratio * 24 # hr/d


        # set temperature 
        heat_out.T = self.catalyst_temp
     
        # N2O emissions
        N2O_emissions = N2O_in.imass['N2O'] * 0.9 # g N2O / hr
        N2O_out.imass['N2O'] = N2O_emissions

    #_design will include all the construction or captial impacts  
    def _design(self):
        design = self.design_results
        
        design['StainlessSteel'] = SS_quant = self.pcd_cat_sandwich_stainless
        design['Steel'] = S_quant = self.pcd_cat_sandwich_steel
        design['ElectricMotor'] =  EM_quant = (5/5.8)
        design['CatalyticConverter'] = Cat_quant = 1
        
        self.construction = (
            Construction(item='StainlessSteel', quantity = SS_quant, quantity_unit = 'kg'),
            Construction(item='Steel', quantity = S_quant, quantity_unit = 'kg'),
            Construction(item='ElectricMotor', quantity = EM_quant, quantity_unit = 'ea'),
            Construction(item='CatalyticConverter', quantity = Cat_quant, quantity_unit = 'ea'),
            )
        self.add_construction()

    
    
    #_cost based on amount of steel and stainless plus individual components
    def _cost(self):
        
        #purchase_costs is used for capital costs
        #can use quantities from above (e.g., self.design_results['StainlessSteel'])
        #can be broken down as specific items within purchase_costs or grouped (e.g., 'Misc. parts')
        self.purchase_costs['Stainless steel'] = (self.stainless_steel_cost 
                            * self.design_results['StainlessSteel'])
        self.purchase_costs['Steel'] = (self.steel_cost 
                            * self.design_results['Steel'])
        self.purchase_costs['Electric motor'] = self.input_auger_motor_pcd
        self.purchase_costs['Misc. parts'] = (self.o2_sensor_cost_pcd +
                                              self.thermocouple_cost_cb_pcd +
                                              self.thermistor_cost_cb_pcd +
                                              self.input_auger_pcd +
                                              self.catylist_pcd +
                                              self.drive_chain_pcd +
                                              self.catalyst_access_door_pcd +
                                              self.feedstock_staging_bin_pcd +
                                              self.bindicator_pcd +
                                              self.feedstock_staging_assembly_pcd +
                                              self.temperature_limit_switch_pcd +
                                              self.airlock_pcd)
        
        self._BM = dict.fromkeys(self.purchase_costs.keys(), 1)
 
        #certain parts need to be replaced based on an expected lifefime
        #the cost of these parts is considered along with the cost of the labor to replace them
        cb_replacement_parts_annual_cost = (((self.daily_run_time * 365 / self.o2_sensor_lifetime_pcd) * self.o2_sensor_cost_pcd)
                                            + ((1 / self.thermocouple_lifetime_cb_2pcd) * 2 * self.thermocouple_cost_cb_pcd)
                                            + ((1 / self.thermistor_lifetime_cb_2pcd) * 2 * self.thermistor_cost_cb_pcd)) # USD/yr only accounts for time running
        
        cb_annual_maintenance = ((self.service_team_adjustdoor_pcd / 60 * 12 * self.service_team_wages)
                                 + (self.service_team_replacecatalyst_pcd / 60 * (1 / self.frequency_corrective_maintenance) * self.service_team_wages) 
                                 + (self.service_team_replacebrick_pcd / 60 * (1 / self.frequency_corrective_maintenance) * self.service_team_wages)
                                 + (self.service_team_replaceo2sensor_pcd / 60 * (self.daily_run_time * 365 / self.o2_sensor_lifetime_pcd) * self.service_team_wages)) #USD/yr only accounts for time running

        self.add_OPEX =  (cb_replacement_parts_annual_cost + cb_annual_maintenance) / (365 * 24) # USD/hr 
       
        power_demand = (self.pcd_auger_power + self.pcd_airlock_power) * self.daily_run_time / 24 #kW
        self.power_utility(power_demand)  #kWh
        #breakpoint()
        # costs associated with full time opperators can be added in the TEA as staff



       
