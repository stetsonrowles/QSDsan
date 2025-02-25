#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
QSDsan: Quantitative Sustainable Design for sanitation and resource recovery systems

This module is developed by:
    Yalin Li <zoe.yalin.li@gmail.com>

Part of this module is based on the biosteam package:
https://github.com/BioSTEAMDevelopmentGroup/biosteam

This module is under the University of Illinois/NCSA Open Source License.
Please refer to https://github.com/QSD-Group/QSDsan/blob/master/LICENSE.txt
for license details.
'''


# %%

import biosteam as bst
from thermosteam import Stream
from . import currency, SanStream, WasteStream, Construction, Transportation

format_title = bst.utils.misc.format_title

__all__ = ('SanUnit',)

class SanUnit(bst.Unit, isabstract=True):

    '''
    Subclass of :class:`biosteam.Unit`, is initialized with :class:`~.SanStream`
    rather than :class:`thermosteam.Stream`.
    
    Parameters
    ----------
    construction : tuple
        Contains construction information.
    construction_impacts : dict
        Total impacts associated with this unit.
    transportation : tuple
        Contains construction information.
    add_OPEX : float or dict
        Operating expense per hour in addition to utility cost (assuming 100% uptime).
        Float input will be automatically converted to a dict with the key being
        "Additional OPEX".
    uptime_ratio : float
        Uptime of the unit to adjust add_OPEX, should be in [0,1]
        (i.e., a unit that is always operating has an uptime_ratio of 1).
    lifetime : float or dict
        Lifetime of this unit (float) or individual equipment within this unit
        (dict) in year.
        It will be used to adjust cost and emission calculation in TEA and LCA.
        Equipment without provided lifetime will be assumed to have the same
        lifetime as the TEA/LCA.
    
    See Also
    --------
    `biosteam.Unit <https://biosteam.readthedocs.io/en/latest/Unit.html>`_
    `thermosteam.Stream <https://thermosteam.readthedocs.io/en/latest/Stream.html>`_

    '''
    
    ticket_name = 'SU'

    def __init__(self, ID='', ins=None, outs=(), thermo=None, init_with='WasteStream',
                 equipments=(), add_OPEX={}, uptime_ratio=1., lifetime=None, **kwargs):
        self._register(ID)
        self._specification = None
        self._load_thermo(thermo)
        self._init_ins(ins, init_with)
        self._init_outs(outs, init_with)
        self._init_utils()
        self._init_results()
        self._assert_compatible_property_package()
        
        self._add_OPEX = add_OPEX
        self._uptime_ratio = 1.
        self._lifetime = None

        for equip in equipments:
            equip._linked_unit = self
        self.equipments = equipments
        
        for attr, val in kwargs.items():
            setattr(self, attr, val)

    @staticmethod
    def _from_stream(streams, init_with):
        if not streams:
            return []

        kind = init_with.lower()
        if kind == 'stream':
            return [streams]
        elif not kind in ('sanstream', 'wastestream'):
            raise ValueError('init_with can only be "Stream", "SanStream", or "WasteStream", ' \
                             f'not "{init_with}".')
        
        if kind == 'sanstream':
            if isinstance(streams, Stream):
                SanStream.from_stream(SanStream, streams)
                return [streams]
            converted = []
            for s in streams:
                converted.append(SanStream.from_stream(SanStream, s))

        else:
            if isinstance(streams, Stream):
                WasteStream.from_stream(WasteStream. streams)
                return [streams]
            converted = []
            for s in streams:
                converted.append(WasteStream.from_stream(WasteStream, s))

        return converted
        

    def _init_ins(self, ins, init_with):
        super()._init_ins(ins)
        self._ins = self._from_stream(self.ins, init_with)

        
    def _init_outs(self, outs, init_with):
        super()._init_outs(outs)
        self._outs = self._from_stream(self.outs, init_with)

    def _init_results(self):
        super()._init_results()
        self._construction = ()
        self._transportation = ()


    def __repr__(self):
        return f'<{type(self).__name__}: {self.ID}>'

    def _info(self, T, P, flow, composition, N, IDs, _stream_info):
        '''Information of the unit.'''
        if self.ID:
            info = f'{type(self).__name__}: {self.ID}\n'
        else:
            info = f'{type(self).__name__}\n'
        info += 'ins...\n'
        i = 0
        for stream in self.ins:
            if not stream:
                info += f'[{i}] {stream}\n'
                i += 1
                continue
            if _stream_info:
                stream_info = stream._info(T, P, flow, composition, N, IDs) + \
                    '\n' + stream._wastestream_info()
            else:
                stream_info = stream._wastestream_info()
            su = stream._source
            index = stream_info.index('\n')
            source_info = f'  from  {type(su).__name__}-{su}\n' if su else '\n'
            info += f'[{i}] {stream.ID}' + source_info + stream_info[index+1:]
            i += 1
        info += 'outs...\n'
        i = 0
        for stream in self.outs:
            if not stream:
                info += f'[{i}] {stream}\n'
                i += 1
                continue
            if _stream_info:
                stream_info = stream._info(T, P, flow, composition, N, IDs) + \
                    '\n' + stream._wastestream_info()
            else:
                stream_info = stream._wastestream_info()
            su = stream._sink
            index = stream_info.index('\n')
            sink_info = f'  to  {type(su).__name__}-{su}\n' if su else '\n'
            info += f'[{i}] {stream.ID}' + sink_info + stream_info[index+1:]
            i += 1
        info = info.replace('\n ', '\n    ')
        return info[:-1]


    def _summary(self):
        '''After system converges, design the unit and calculate cost and environmental impacts.'''
        self._design()
        self._cost()
   
    
    def show(self, T=None, P=None, flow='g/hr', composition=None, N=15, IDs=None, stream_info=True):
        '''Print information of the unit, including waste stream-specific information.'''
        print(self._info(T, P, flow, composition, N, IDs, stream_info))
    

    def add_equipment_design(self):
        for equip in self.equipments:
            name = equip.name or format_title(type(equip).__name__)
            self.design_results.update(equip._design())
            self._units.update(equip.design_units)
            self._BM[name] = equip.BM
            if equip.lifetime:
                self._equipment_lifetime[name] = equip.lifetime
    
    def add_equipment_cost(self):
        for equip in self.equipments:
            name = equip.name or format_title(type(equip).__name__)
            self.purchase_costs[name] = equip._cost()
    
    def add_construction(self, add_unit=True, add_design=True, add_cost=True,
                         add_lifetime=True):
        '''Batch-adding construction unit, designs, and costs.'''
        for i in self.construction:
            if add_unit:
                self._units[i.item.ID] = i.item.functional_unit
            if add_design:
                self.design_results[i.item.ID] = i.quantity
            if add_cost:
                self.purchase_costs[i.item.ID] = i.cost
            if add_lifetime and i.lifetime:
                self._equipment_lifetime[i.item.ID] = i.lifetime
    
    @property
    def components(self):
        '''[Components] The :class:`Components` object associated with this unit.'''
        return self.chemicals
    
    @property
    def construction(self):
        '''[tuple] Contains construction information.'''
        return self._construction
    @construction.setter
    def construction(self, i):
        if isinstance(i, Construction):
            i = (i,)
        else:
            if not iter(i):
                raise TypeError(f'Only <Construction> can be included, not {type(i).__name__}.')
            for j in i:
                if not isinstance(j, Construction):
                    raise TypeError(f'Only <Construction> can be included, not {type(j).__name__}.')
        self._construction = i

    @property
    def construction_impacts(self):
        '''[dict] Total impacts associated with this unit.'''
        impacts = {}
        if not self.construction:
            return impacts
        for i in self.construction:
            impact = i.impacts
            for i, j in impact.items():
                try: impacts[i] += j
                except: impacts[i] = j
        return impacts

    @property
    def transportation(self):
        '''[tuple] Contains transportation information.'''
        return self._transportation
    @transportation.setter
    def transportation(self, i):
        if isinstance(i, Transportation):
            i = (i,)
        else:
            if not iter(i):
                raise TypeError(f'Only <Transportation> can be included, not {type(i).__name__}.')
            for j in i:
                if not isinstance(j, Transportation):
                    raise TypeError(f'Only <Transportation> can be included, not {type(j).__name__}.')
        self._transportation = i

    @property
    def add_OPEX(self):
        '''
        [dict] Operating expense per hour in addition to utility cost.
        Float input will be automatically converted to a dict with the key being
        "Additional OPEX".
        '''
        return {'Additional OPEX': self._add_OPEX} if isinstance(self._add_OPEX, float) \
                                                   else self._add_OPEX
    @add_OPEX.setter
    def add_OPEX(self, i):
        if isinstance(i, float):
            i = {'Additional OPEX': i}
        if not isinstance(i, dict):
            raise TypeError(f'add_OPEX can only be float of dict, not {type(i).__name__}.')
        self._add_OPEX = i

    def results(self, with_units=True, include_utilities=True,
                include_total_cost=True, include_installed_cost=False,
                include_zeros=True, external_utilities=(), key_hook=None):

        results = super().results(with_units, include_utilities,
                                  include_total_cost, include_installed_cost,
                                  include_zeros, external_utilities, key_hook)

        for k, v in self.add_OPEX.items():
            results.loc[(k, ''), :] = ('USD/hr', v)
        if with_units:
            results.replace({'USD': f'{currency}', 'USD/hr': f'{currency}/hr'},
                            inplace=True)
        return results

    @property
    def uptime_ratio(self):
        '''
        [float] Uptime of the unit to adjust `add_OPEX`, should be in [0,1]
        (i.e., a unit that is always operating).
        '''
        return self._uptime_ratio
    @uptime_ratio.setter
    def uptime_ratio(self, i):
        assert 0 <= i <= 1, f'Uptime must be between 0 and 1 (100%), not {i}.'
        self._uptime_ratio = float(i)

    @property
    def lifetime(self):
        '''
        [float] or [dict] Lifetime of this unit (float) or individual equipment
        within this unit (dict) in year.
        It will be used to adjust cost and emission calculation in TEA and LCA.
        Equipment without provided lifetime will be assumed to have the same
        lifetime as the TEA/LCA. 
        '''
        if self._lifetime is not None:
            return self._lifetime
        elif self._equipment_lifetime:
            return self._equipment_lifetime
        else:
            return None
    @lifetime.setter
    def lifetime(self, i):
        self._lifetime = float(i)










