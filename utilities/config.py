from __future__ import annotations

import configparser as confp
import pathlib
import os
import datetime as dt

def reset_config(path: str | pathlib.Path):
    print("Resetting configuration file...")
    
    temp_gratings = ['1200', '2400', '* New Entry']
    data_save_dir = os.path.expanduser('~/Documents')
    data_save_dir += '/mcpherson_mmc/%s/'%(dt.datetime.now().strftime('%Y%m%d'))
    if not os.path.exists(data_save_dir):
        os.makedirs(data_save_dir)

    os.remove(path + '/config.ini')
    save_config(path, 1, True, data_save_dir, temp_gratings, 0, 1, 37.8461, 32.0, 0.0, 56.54, 600.0, -40.0, 1, 0, 0, 0, 0, 'none', 'none', 'none', 'none', 'none', 0)

def save_config(path: str | pathlib.Path, mes_sign: int, autosave_data: bool, data_save_directory: str, grating_combo_lstr: list(str), current_grating_idx: int, diff_order: int, zero_ofst: float, inc_ang: float, tan_ang: float, arm_len: float, max_pos: float, min_pos: float, main_axis_index: int, filter_axis_index: int, rsamp_axis_index: int, tsamp_axis_index: int, detector_axis_index: int, main_axis_dev_name: str, filter_axis_dev_name: str, rsamp_axis_dev_name: str, tsamp_axis_dev_name: str, detector_axis_dev_name: str, num_axes: int) -> bool:
    # Save the current configuration when exiting. If the program crashes, it doesn't save your config.
    save_config = confp.ConfigParser()
    grating_lstr = grating_combo_lstr[:-1]
    gratingDensityStr = ''
    for obj in grating_lstr:
        gratingDensityStr += obj + ','
    gratingDensityStr = gratingDensityStr.rstrip(',')
    if autosave_data:
        autosave_data_str = 'True'
    else:
        autosave_data_str = 'False'
        
    save_config['INTERFACE'] = {'measurementSign': mes_sign,
                                'autosaveData': autosave_data_str,
                                'dataSaveDirectory': data_save_directory}
    save_config['INSTRUMENT'] = {'gratingDensities': gratingDensityStr,
                                 'gratingDensityIndex': str(current_grating_idx),
                                 'diffractionOrder': str(diff_order),
                                 'zeroOffset': str(zero_ofst),
                                 'incidenceAngle': str(inc_ang),
                                 'tangentAngle': str(tan_ang),
                                 'armLength': str(arm_len),
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
    
    with open(path + '/config.ini', 'w') as confFile:
        save_config.write(confFile)

def load_config(path: str | pathlib.Path) -> dict:
    if not os.path.exists(path + '/config.ini'):
        print("No config.ini file found, creating one...")
        temp_gratings = ['1200', '2400', '* New Entry']
        data_save_dir = os.path.expanduser('~/Documents')
        data_save_dir += '/mcpherson_mmc/%s/'%(dt.datetime.now().strftime('%Y%m%d'))
        if not os.path.exists(data_save_dir):
            os.makedirs(data_save_dir)

        save_config(path, 1, True, data_save_dir, temp_gratings, 0, 1, 37.8461, 32.0, 0.0, 56.54, 600.0, -40.0, 1, 0, 0, 0, 0, 'none', 'none', 'none', 'none', 'none', 0)

    while os.path.exists(path + '/config.ini'):
        config = confp.ConfigParser()
        config.read(path + '/config.ini')
        print(config)
        error = False

        if len(config.sections()) and 'INSTRUMENT' in config.sections():
            gratingDensityStr = config['INSTRUMENT']['gratingDensities']
            gratingDensityList = gratingDensityStr.split(',')
            for d in gratingDensityList:
                try:
                    _ = float(d)
                except Exception:
                    print('Error getting grating densities')
                    # show a window here or something
                    error = True
                    break
            if error:
                break
            grating_combo_lstr = gratingDensityList + ['* New Entry']
            try:
                idx = int(config['INSTRUMENT']['gratingDensityIndex'])
            except Exception as e:
                print('Error getting grating index, %s'%(e.what()))
                idx = 0
            if idx >= len(grating_combo_lstr) - 1:
                print('Invalid initial grating index')
                idx = 0
            current_grating_idx = idx
            grating_density = float(grating_combo_lstr[current_grating_idx])
            try:
                diff_order = int(config['INSTRUMENT']['diffractionOrder'])
            except Exception as e:
                print('Invalid diffraction order, %s'%(e.what()))
            if diff_order < 1:
                print('Diffraction order can not be zero or negative')
                diff_order = 1
            try:
                zero_ofst = float(config['INSTRUMENT']['zeroOffset'])
            except Exception as e:
                print('Invalid incidence angle, %s'%(e.what()))
            if not -90 < zero_ofst < 90:
                print('Invalid incidence angle %f'%(zero_ofst))
                zero_ofst = 0
            try:
                inc_ang = float(config['INSTRUMENT']['incidenceAngle'])
            except Exception as e:
                print('Invalid incidence angle, %s'%(e.what()))
            if not -90 < inc_ang < 90:
                print('Invalid incidence angle %f'%(inc_ang))
                inc_ang = 0
            
            try:
                tan_ang = float(config['INSTRUMENT']['tangentAngle'])
            except Exception as e:
                print('Invalid tangent angle, %s'%(e.what()))
            if not -90 < tan_ang < 90:
                print('Invalid tangent angle %f'%(tan_ang))
                tan_ang = 0

            try:
                arm_len = float(config['INSTRUMENT']['armLength'])
            except Exception as e:
                print('Invalid arm length, %s'%(e.what()))
            if not 0 < arm_len < 1e6: # 1 km
                print('Invalid arm length %f'%(arm_len))
                arm_len = 100

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


            break

    ret_dict = {
        "measurementSign": mes_sign,
        "autosaveData": autosave_data,
        "dataSaveDirectory": data_save_directory,
        "gratingDensities": grating_combo_lstr,
        "gratingDensityIndex": current_grating_idx,
        "diffractionOrder": diff_order,
        "zeroOffset": zero_ofst,
        "incidenceAngle": inc_ang,
        "tangentAngle": tan_ang,
        "armLength": arm_len,
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
        'numAxes': num_axes
    }

    print(ret_dict)
    return ret_dict