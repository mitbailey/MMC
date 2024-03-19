#
# @file log.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief 
# @version See Git tags for version information.
# @date 2023.05.12
# 
# @copyright Copyright (c) 2023
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

from utilities import version
import time
import os
import inspect

LOG_LEVEL = 0
MAX_DIR_SIZE = 1000 # MB
TRACE = True

def register():
    global LOG_LEVEL
    global MAX_DIR_SIZE
    global TRACE
    
    log_file_found = False
    log_cfg = 'log.cfg'
    if os.path.isfile(log_cfg):
        cfg_file = open(log_cfg, 'r')
        contents = cfg_file.read()
        if 'LOG_LEVEL = ' in contents and 'MAX_DIR_SIZE = ' in contents:
            print('Log configuration file found.')
            log_file_found = True
            print('\n')
            print(contents)
            contents = contents.replace('\n', ',')
            contents = contents.replace(' ', '')
            contents = contents.replace('=', ',')
            contents = contents.split(',')
            print(contents)
            try:
                LOG_LEVEL = int(contents[contents.index('LOG_LEVEL') + 1])
                MAX_DIR_SIZE = int(contents[contents.index('MAX_DIR_SIZE') + 1])
            except Exception as e:
                print(e)
                exit(99)
        else:
            print('Log configuration file format invalid.')
    else:
        print('No log configuration file found.')

    logdir = 'logs'
    if not os.path.isdir(logdir):
        os.makedirs(logdir)
    else:
        file_list = os.listdir(logdir)
        # print(file_list[-10:])
        for filename in file_list[:-10]:
            print('Removing:', filename)
            os.remove('%s/%s'%(logdir, filename))
    logname = time.strftime('%Y%m%dT%H%M%S')
    global __logfile
    __logfile = open('%s/%s_%s.txt'%(logdir, logname, version.__version__), 'a')
    info('Logger opened log file.')

    info('Logger initialized. Log level: %d.'%(LOG_LEVEL))
    if log_file_found:
        info('Log configuration file found.')
    else:
        warn('No log configuration file found.')

def debug(*arg, **end):
    global LOG_LEVEL
    if LOG_LEVEL <= 0:
        _out('[DEBUG]', arg)

def trace(*arg, **end):
    global TRACE
    if TRACE:
        _out('[TRACE]', arg, True)

def info(*arg, **end):
    global LOG_LEVEL
    if LOG_LEVEL <= 1:
        _out('[INFO ]', arg)

def warn(*arg, **end):
    global LOG_LEVEL
    if LOG_LEVEL <= 2:
        _out('[WARN ]', arg)

def error(*arg, **end):
    global LOG_LEVEL
    if LOG_LEVEL <= 3:
        _out('[ERROR]', arg)

def fatal(*arg, **end):
    global LOG_LEVEL
    if LOG_LEVEL <= 4:
        _out('[FATAL]', arg)

def _out(_l, _m, _t = False):
    global __logfile

    if _t:
        callerframerecord = inspect.stack()[3]
        __FILE__, __LINE__, __FUNC__ = inspect.getframeinfo(callerframerecord[0])[0:3]
        __FILE__ = __FILE__.split(sep='\\')[-1]
        __FLF__ = '[%s:%d | %s]'%(__FILE__, __LINE__, __FUNC__)
        __logfile.write('Caller: %s, '%(__FLF__))
        print('Caller: %s, '%(__FLF__), end='')

    callerframerecord = inspect.stack()[2]
    __FILE__, __LINE__, __FUNC__ = inspect.getframeinfo(callerframerecord[0])[0:3]
    __FILE__ = __FILE__.split(sep='\\')[-1]

    __FLF__ = ('[%s:%d | %s]'%(__FILE__, __LINE__, __FUNC__)).ljust(50, ' ')

    if len(_m) == 1:
        __logfile.write('%s %s %s\n'%(__FLF__, _l, _m[0]))
        print('%s %s %s'%(__FLF__, _l, _m[0]))
    elif len(_m) > 1:
        __logfile.write('%s %s'%(__FLF__, _l))
        print('%s %s'%(__FLF__, _l), end='')
        for i in range(len(_m)):
            __logfile.write(' %s'%(_m[i]))
            print(' %s'%(_m[i]), end='')
        __logfile.write('\n')
        print()

    __logfile.flush()

def finish():
    info('Program complete; logger closing log file.')
    __logfile.close()