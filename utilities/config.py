from __future__ import annotations

import configparser as confp
import pathlib
import os
import datetime as dt

def reset_config(path: str):
    print("Resetting configuration file...")
    
    temp_gratings = ['1200', '2400', '* New Entry']
    data_save_dir = os.path.expanduser('~/Documents')
    data_save_dir += '/mcpherson_mmc/%s/'%(dt.datetime.now().strftime('%Y%m%d'))
    if not os.path.exists(data_save_dir):
        os.makedirs(data_save_dir)
    if os.path.exists(path + '/config.ini'):
        os.remove(path + '/config.ini')
    save_config(path, data_save_directory=data_save_dir)

# TODO: Change this to taking a dictionary or something, this many arguments is ridiculous.
def save_config(path: str, is_export: bool = False, mes_sign: int = 1, autosave_data: bool = True, data_save_directory: str = './data/', model_index: int = 0, current_grating_density: float = 0.0, zero_ofst: float = 1, max_pos: float = 600.0, min_pos: float = -40.0, main_axis_index: int = 1, filter_axis_index: int = 0, rsamp_axis_index: int = 0, tsamp_axis_index: int = 0, detector_axis_index: int = 0, main_axis_dev_name: str = 'none', filter_axis_dev_name: str = 'none', rsamp_axis_dev_name: str = 'none', tsamp_axis_dev_name: str = 'none', detector_axis_dev_name: str = 'none', num_axes: int = 0, fw_max_pos: float = 9999.0, fw_min_pos: float = -9999.0, smr_max_pos: float = 9999.0, smr_min_pos: float = -9999.0, smt_max_pos: float = 9999.0, smt_min_pos: float = -9999.0, dr_max_pos: float = 9999.0, dr_min_pos: float = -9999.0) -> bool:
    # Save the current configuration when exiting. If the program crashes, it doesn't save your config.
    save_config = confp.ConfigParser()
    # grating_lstr = grating_combo_lstr[:-1]
    # gratingDensityStr = ''
    # for obj in grating_lstr:
    #     gratingDensityStr += obj + ','
    # gratingDensityStr = gratingDensityStr.rstrip(',')
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
                                  'tsampAxisIndex': tsamp_axis_index,
                                  'detectorAxisIndex': detector_axis_index,
                                  'mainAxisName': main_axis_dev_name,
                                  'filterAxisName': filter_axis_dev_name,
                                  'rsampAxisName': rsamp_axis_dev_name,
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
    
    if not is_export:
        with open(path + '/config.ini', 'w') as confFile:
            save_config.write(confFile)
    else:
        with open(path, 'w') as confFile:
            save_config.write(confFile)

def load_config(path: str, is_import: bool) -> dict:
    print('Beginning load for %s.'%(path))

    if not is_import:
        path = path + '/config.ini'

    if not os.path.exists(path):
        if is_import:
            raise RuntimeError("File doesn't exist.")
        print("No config.ini file found, creating one...")
        temp_gratings = ['1200', '2400', '* New Entry']
        data_save_dir = os.path.expanduser('~/Documents')
        data_save_dir += '/mcpherson_mmc/%s/'%(dt.datetime.now().strftime('%Y%m%d'))
        if not os.path.exists(data_save_dir):
            os.makedirs(data_save_dir)

        save_config(path, False, 1, True, data_save_dir, 0.0, 1, 37.8461, 600.0, -40.0, 1, 0, 0, 0, 0, 'none', 'none', 'none', 'none', 'none', 0, 9999, -9999, 9999, -9999, 9999, -9999, 9999, -9999)

    while os.path.exists(path):
        config = confp.ConfigParser()
        config.read(path)

        print(config)
        error = False

        if len(config.sections()) and 'INSTRUMENT' in config.sections():
            # gratingDensityStr = config['INSTRUMENT']['gratingDensities']
            # gratingDensityList = gratingDensityStr.split(',')
            # for d in gratingDensityList:
            #     try:
            #         _ = float(d)
            #     except Exception:
            #         print('Error getting grating densities')
            #         # show a window here or something
            #         error = True
            #         break
            # if error:
            #     break
            # grating_combo_lstr = gratingDensityList + ['* New Entry']
            # try:
            #     idx = int(config['INSTRUMENT']['gratingDensityIndex'])
            # except Exception as e:
            #     print('Error getting grating index, %s'%(e.what()))
            #     idx = 0
            # if idx >= len(grating_combo_lstr) - 1:
            #     print('Invalid initial grating index')
            #     idx = 0
            # current_grating_idx = idx
            # grating_density = float(grating_combo_lstr[current_grating_idx])
            # try:
            #     diff_order = int(config['INSTRUMENT']['diffractionOrder'])
            # except Exception as e:
            #     print('Invalid diffraction order, %s'%(e.what()))
            # if diff_order < 1:
            #     print('Diffraction order can not be zero or negative')
            #     diff_order = 1
            try:
                current_grating_density = float(config['INSTRUMENT']['gratingDensity'])
            except Exception as e:
                print('Invalid grating density, %s'%(e.what()))
            if current_grating_density < 0:
                print('Invalid grating density %f'%(current_grating_density))
                current_grating_density = 0
            try:
                zero_ofst = float(config['INSTRUMENT']['zeroOffset'])
            except Exception as e:
                print('Invalid incidence angle, %s'%(e.what()))
            if not -90 < zero_ofst < 90:
                print('Invalid incidence angle %f'%(zero_ofst))
                zero_ofst = 0
            # try:
            #     inc_ang = float(config['INSTRUMENT']['incidenceAngle'])
            # except Exception as e:
            #     print('Invalid incidence angle, %s'%(e.what()))
            # if not -90 < inc_ang < 90:
            #     print('Invalid incidence angle %f'%(inc_ang))
            #     inc_ang = 0
            
            # try:
            #     tan_ang = float(config['INSTRUMENT']['tangentAngle'])
            # except Exception as e:
            #     print('Invalid tangent angle, %s'%(e.what()))
            # if not -90 < tan_ang < 90:
            #     print('Invalid tangent angle %f'%(tan_ang))
            #     tan_ang = 0

            # try:
            #     arm_len = float(config['INSTRUMENT']['armLength'])
            # except Exception as e:
            #     print('Invalid arm length, %s'%(e.what()))
            # if not 0 < arm_len < 1e6: # 1 km
            #     print('Invalid arm length %f'%(arm_len))
            #     arm_len = 100

            max_pos = float(config['INSTRUMENT']['maxPosition'])
            min_pos = float(config['INSTRUMENT']['minPosition'])

            try:
                mes_sign = int(config['INTERFACE']['measurementSign'])
            except Exception as e:
                print('Invalid measurement sign, %s'%(e.what()))
            if mes_sign != 1 and mes_sign != -1:
                print('Invalid measurement sign, %s'%(e.what()))
                mes_sign = 1
            
            try:
                model_index = int(config['INSTRUMENT']['modelIndex'])
            except Exception as e:
                print('Invalid model index, %s'%(e.what()))
            if model_index < 0:
                print('Invalid model index, %s'%(e.what()))
                model_index = 0

            try:
                autosave_data_str = config['INTERFACE']['autosaveData']
                if autosave_data_str == 'True':
                    autosave_data = True
                else:
                    autosave_data = False
            except Exception as e:
                print('Invalid auto-save data boolean, %s'%(e.what()))

            try:
                data_save_directory = config['INTERFACE']['dataSaveDirectory']
            except Exception as e:
                print('Invalid directory, %s'%(e.what()))
            
            main_axis_index = int(config['CONNECTIONS']['mainAxisIndex'])
            filter_axis_index = int(config['CONNECTIONS']['filterAxisIndex'])
            rsamp_axis_index = int(config['CONNECTIONS']['rsampAxisIndex'])
            tsamp_axis_index = int(config['CONNECTIONS']['tsampAxisIndex'])
            detector_axis_index = int(config['CONNECTIONS']['detectorAxisIndex'])

            main_axis_dev_name = str(config['CONNECTIONS']['mainAxisName'])
            filter_axis_dev_name = str(config['CONNECTIONS']['filterAxisName'])
            rsamp_axis_dev_name = str(config['CONNECTIONS']['rsampAxisName'])
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
        'tsampAxisIndex': tsamp_axis_index,
        'detectorAxisIndex': detector_axis_index,
        'mainAxisName': main_axis_dev_name,
        'filterAxisName': filter_axis_dev_name,
        'rsampAxisName': rsamp_axis_dev_name,
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
        'drMin': dr_min_pos
    }

    print(ret_dict)
    return ret_dict