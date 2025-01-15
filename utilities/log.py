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
from termcolor import colored
import datetime

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
        for filename in file_list[:-MAX_DIR_SIZE]:
            print('Removing:', filename)
            os.remove('%s/%s'%(logdir, filename))
    logname = time.strftime('%Y%m%dT%H%M%S')
    global __logfile
    __logfile = None
    try:
        __logfile = open('%s/%s_%s.txt'%(logdir, logname, version.__version__), 'a')
    except Exception as e:    
        error('Failed to open log file. This is most likely due to a lack of privileges. Try running the program as Administrator. Exception reported as:', e)
        __logfile = None

        error('Logger failed to initialize. This will be reported.')
    else:
        info('Logger opened log file.')

        info('Logger initialized. Log level: %d.'%(LOG_LEVEL))
        if log_file_found:
            info('Log configuration file found.')
        else:
            warn('No log configuration file found.')

def logging_to_file():
    if __logfile is not None:
        return True
    else:
        return False

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
    print(__logfile)

    cstack = ''
    if _t:
        stack = inspect.stack()
        objs = []
        for i in range(2, len(stack)):
            callerframerecord = stack[i]
            __FILE__, __LINE__, __FUNC__ = inspect.getframeinfo(callerframerecord[0])[0:3]
            __FILE__ = __FILE__.split(sep='\\')[-1]
            objs.append('[%s:%d | %s]'%(__FILE__, __LINE__, __FUNC__))
        cstack = '->\n\t'.join(objs[::-1])

        # callerframerecord = inspect.stack()[3]
        # __FILE__, __LINE__, __FUNC__ = inspect.getframeinfo(callerframerecord[0])[0:3]
        # __FILE__ = __FILE__.split(sep='\\')[-1]
        # __FLF__ = '[%s:%d | %s]'%(__FILE__, __LINE__, __FUNC__)
        # cstack = 'Caller: %s, '%(__FLF__)

    callerframerecord = inspect.stack()[2]
    __FILE__, __LINE__, __FUNC__ = inspect.getframeinfo(callerframerecord[0])[0:3]
    __FILE__ = __FILE__.split(sep='\\')[-1]

    __FLF__ = ('[%s:%d | %s]'%(__FILE__, __LINE__, __FUNC__)).ljust(50, ' ')

    out = '%s %s'%(_l, __FLF__)
    if len(cstack) > 0:
        out += ' ' + cstack
    if len(_m) > 0:
        out += ' ' + str(_m[0])
        if len(_m) > 1:
            for i in range(1, len(_m)):
                out += ' %s'%(_m[i])
            # out += '\n'
    out += '\n'

    # Get timestamp.
    # Prints are NOT guaranteed to be in order or meaningfully timestamped. This just provides a general duration between things.
    ts = datetime.datetime.now().time().strftime('%H:%M:%S.%f')

    if __logfile is not None:
        __logfile.write(ts + ' ' + out)

    out = out.lstrip()
    out = ''.join(out.split(_l))
    if _l == '[DEBUG]':
        col = colored(_l, 'blue')
    elif _l == '[TRACE]':
        col = colored(_l, 'grey', attrs=['bold', 'blink'])
    elif _l == '[INFO ]':
        col = colored(_l, 'green')
    elif _l == '[WARN ]':
        col = colored(_l, 'yellow')
    elif _l == '[ERROR]':
        col = colored(_l, 'red')

    print(ts + ' ', end='')
    print(col, end='')
    print(out, end='\n')

    if __logfile is not None:
        __logfile.flush()

def finish():
    info('Program complete; logger closing log file.')
    if __logfile is not None:
        __logfile.close()