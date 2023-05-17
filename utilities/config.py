#
# @file config.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief 
# @version See Git tags for version information.
# @date 2022.08.22
# 
# @copyright Copyright (c) 2022
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#

from __future__ import annotations

import configparser as confp
import os
import datetime as dt
from utilities import log

def reset_config(path: str):
    log.warn("Resetting configuration file...")
    
    data_save_dir = os.path.expanduser('~/Documents')
    data_save_dir += '/mcpherson_mmc/%s/'%(dt.datetime.now().strftime('%Y%m%d'))
    if not os.path.exists(data_save_dir):
        os.makedirs(data_save_dir)
    if os.path.exists(path + '/config.ini'):
        os.remove(path + '/config.ini')
    save_config(path, data_save_directory=data_save_dir)

# TODO: Change this to taking a dictionary or something, this many arguments is ridiculous.
def save_config(path: str, is_export: bool = False, mes_sign: int = 1, autosave_data: bool = True, data_save_directory: str = './data/', model_index: int = 0, current_grating_density: float = 0.0, zero_ofst: float = 1, max_pos: float = 600.0, min_pos: float = -40.0, main_axis_index: int = 1, filter_axis_index: int = 0, rsamp_axis_index: int = 0, asamp_axis_index: int = 0, tsamp_axis_index: int = 0, detector_axis_index: int = 0, main_axis_dev_name: str = 'Loaded Config Name Empty', filter_axis_dev_name: str = 'Loaded Config Name Empty', rsamp_axis_dev_name: str = 'Loaded Config Name Empty', asamp_axis_dev_name: str = 'Loaded Config Name Empty', tsamp_axis_dev_name: str = 'Loaded Config Name Empty', detector_axis_dev_name: str = 'Loaded Config Name Empty', num_axes: int = 0, fw_max_pos: float = 9999.0, fw_min_pos: float = -9999.0, smr_max_pos: float = 9999.0, smr_min_pos: float = -9999.0, smt_max_pos: float = 9999.0, smt_min_pos: float = -9999.0, dr_max_pos: float = 9999.0, dr_min_pos: float = -9999.0, fw_offset: float = 0.0, st_offset: float = 0.0, sr_offset: float = 0.0, dr_offset: float = 0.0) -> bool:t
    
    # Save the current configuration when exiting. If the program crashes, it doesn't save your config.
    save_config = confp.ConfigParser()
    
    if autosave_data:
        autosave_data_str = 'True'
    else:
        autosave_data_str = 'False'
        
    save_config['INTERFACE'] = {'measurementSign': mes_sign, 
                                'autosaveData': autosave_data_str,
                                'dataSaveDirectory': data_save_directory}
    save_config['INSTRUMENT'] = {'modelIndex': model_index,
                                 'gratingDensity': str(current_grating_density),
                                 'zeroOffset': str(zero_ofst), 
                                 'maxPosition': str(max_pos),
                                 'minPosition': str(min_pos)}
    save_config['CONNECTIONS'] = {'mainAxisIndex': main_axis_index,
                                  'filterAxisIndex': filter_axis_index,
                                  'rsampAxisIndex': rsamp_axis_index,
                                  'asampAxisIndex': asamp_axis_index,
                                  'tsampAxisIndex': tsamp_axis_index,
                                  'detectorAxisIndex': detector_axis_index,
                                  'mainAxisName': main_axis_dev_name,
                                  'filterAxisName': filter_axis_dev_name,
                                  'rsampAxisName': rsamp_axis_dev_name,
                                  'asampAxisName': asamp_axis_dev_name,
                                  'tsampAxisName': tsamp_axis_dev_name,
                                  'detectorAxisName': detector_axis_dev_name,
                                  'numAxes': num_axes}
    save_config['AXIS LIMITS'] = {'fwMax': fw_max_pos,
                                  'fwMin': fw_min_pos,
                                  'smrMax': smr_max_pos,
                                  'smrMin': smr_min_pos,
                                  'smtMax': smt_max_pos,
                                  'smtMin': smt_min_pos,
                                  'drMax': dr_max_pos,
                                  'drMin': dr_min_pos}
    save_config['OFFSETS'] = {'fwOffset': fw_offset,
                              'stOffset': st_offset,
                              'srOffset': sr_offset,
                              'drOffset': dr_offset}
    
    if not is_export:
        with open(path + '/config.ini', 'w') as confFile:
            save_config.write(confFile)
    else:
        with open(path, 'w') as confFile:
            save_config.write(confFile)

def load_config(path: str, is_import: bool) -> dict:
    log.info('Beginning load for %s.'%(path))

    if not is_import:
        path = path + '/config.ini'

    if not os.path.exists(path):
        if is_import:
            log.error("File doesn't exist.")
            raise RuntimeError("File doesn't exist.")
        log.warn("No config.ini file found, creating one...")
        temp_gratings = ['1200', '2400', '* New Entry']
        data_save_dir = os.path.expanduser('~/Documents')
        data_save_dir += '/mcpherson_mmc/%s/'%(dt.datetime.now().strftime('%Y%m%d'))
        if not os.path.exists(data_save_dir):
            os.makedirs(data_save_dir)

        save_config(path, False, 1, True, data_save_dir, 0.0, 1, 37.8461, 600.0, -40.0, 1, 0, 0, 0, 0, 'none', 'none', 'none', 'none', 'none', 0, 9999, -9999, 9999, -9999, 9999, -9999, 9999, -9999, 0.0, 0.0, 0.0, 0.0)
        # save_config(..?)

    while os.path.exists(path):
        config = confp.ConfigParser()
        config.read(path)

        log.debug(config)
        error = False

        if len(config.sections()) and 'INSTRUMENT' in config.sections():
            try:
                current_grating_density = float(config['INSTRUMENT']['gratingDensity'])
            except Exception as e:
                log.error('Invalid grating density, %s'%(e.what()))
            if current_grating_density < 0:
                log.error('Invalid grating density %f'%(current_grating_density))
                current_grating_density = 0
            try:
                zero_ofst = float(config['INSTRUMENT']['zeroOffset'])
            except Exception as e:
                log.error('Invalid incidence angle, %s'%(e.what()))
            if not -90 < zero_ofst < 90:
                log.error('Invalid incidence angle %f'%(zero_ofst))
                zero_ofst = 0

            max_pos = float(config['INSTRUMENT']['maxPosition'])
            min_pos = float(config['INSTRUMENT']['minPosition'])

            try:
                mes_sign = int(config['INTERFACE']['measurementSign'])
            except Exception as e:
                log.error('Invalid measurement sign, %s'%(e.what()))
            if mes_sign != 1 and mes_sign != -1:
                log.error('Invalid measurement sign, %s'%(e.what()))
                mes_sign = 1
            
            try:
                model_index = int(config['INSTRUMENT']['modelIndex'])
            except Exception as e:
                log.error('Invalid model index, %s'%(e.what()))
            if model_index < 0:
                log.error('Invalid model index, %s'%(e.what()))
                model_index = 0

            try:
                autosave_data_str = config['INTERFACE']['autosaveData']
                if autosave_data_str == 'True':
                    autosave_data = True
                else:
                    autosave_data = False
            except Exception as e:
                log.error('Invalid auto-save data boolean, %s'%(e.what()))

            try:
                data_save_directory = config['INTERFACE']['dataSaveDirectory']
            except Exception as e:
                log.error('Invalid directory, %s'%(e.what()))
            
            main_axis_index = int(config['CONNECTIONS']['mainAxisIndex'])
            filter_axis_index = int(config['CONNECTIONS']['filterAxisIndex'])
            rsamp_axis_index = int(config['CONNECTIONS']['rsampAxisIndex'])
            asamp_axis_index = int(config['CONNECTIONS']['asampAxisIndex'])
            tsamp_axis_index = int(config['CONNECTIONS']['tsampAxisIndex'])
            detector_axis_index = int(config['CONNECTIONS']['detectorAxisIndex'])

            main_axis_dev_name = str(config['CONNECTIONS']['mainAxisName'])
            filter_axis_dev_name = str(config['CONNECTIONS']['filterAxisName'])
            rsamp_axis_dev_name = str(config['CONNECTIONS']['rsampAxisName'])
            asamp_axis_dev_name = str(config['CONNECTIONS']['asampAxisName'])
            tsamp_axis_dev_name = str(config['CONNECTIONS']['tsampAxisName'])
            detector_axis_dev_name = str(config['CONNECTIONS']['detectorAxisName'])

            num_axes = int(config['CONNECTIONS']['numAxes'])

            fw_max_pos = float(config['AXIS LIMITS']['fwMax'])
            fw_min_pos = float(config['AXIS LIMITS']['fwMin'])
            smr_max_pos = float(config['AXIS LIMITS']['smrMax'])
            smr_min_pos = float(config['AXIS LIMITS']['smrMin'])
            smt_max_pos = float(config['AXIS LIMITS']['smtMax'])
            smt_min_pos = float(config['AXIS LIMITS']['smtMin'])
            dr_max_pos = float(config['AXIS LIMITS']['drMax'])
            dr_min_pos = float(config['AXIS LIMITS']['drMin'])

            fw_offset = float(config['OFFSETS']['fwOffset'])
            st_offset = float(config['OFFSETS']['stOffset'])
            sr_offset = float(config['OFFSETS']['srOffset'])
            dr_offset = float(config['OFFSETS']['drOffset'])

            break

    ret_dict = {
        "measurementSign": mes_sign,
        "autosaveData": autosave_data,
        "dataSaveDirectory": data_save_directory,
        "modelIndex": model_index,
        "gratingDensity": current_grating_density,
        "zeroOffset": zero_ofst,
        "maxPosition": max_pos,
        "minPosition": min_pos,
        'mainAxisIndex': main_axis_index,
        'filterAxisIndex': filter_axis_index,
        'rsampAxisIndex': rsamp_axis_index,
        'asampAxisIndex': asamp_axis_index,
        'tsampAxisIndex': tsamp_axis_index,
        'detectorAxisIndex': detector_axis_index,
        'mainAxisName': main_axis_dev_name,
        'filterAxisName': filter_axis_dev_name,
        'rsampAxisName': rsamp_axis_dev_name,
        'asampAxisName': asamp_axis_dev_name,
        'tsampAxisName': tsamp_axis_dev_name,
        'detectorAxisName': detector_axis_dev_name,
        'numAxes': num_axes,
        'fwMax': fw_max_pos,
        'fwMin': fw_min_pos,
        'smrMax': smr_max_pos,
        'smrMin': smr_min_pos,
        'smtMax': smt_max_pos,
        'smtMin': smt_min_pos,
        'drMax': dr_max_pos,
        'drMin': dr_min_pos,
        'fwOffset': fw_offset,
        'stOffset': st_offset,
        'srOffset': sr_offset,
        'drOffset': dr_offset
    }

    log.debug(ret_dict)
    return ret_dict