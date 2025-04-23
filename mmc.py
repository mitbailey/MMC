#
# @file mmc.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief The MMC GUI and program.
# @version See Git tags for version information.
# @date 2022.08.03
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

""" 
UI Element Naming Scheme
------------------------
All UI elements should be named in the following format:
UIE_[window code]_[subsection code]_[Chosen Name]_[Q-type]

Device Manager Window       dmw_
Main GUI Window             mgw_
Machine Config. Window      mcw_

Main Drive                  md_
Filter Wheel                fw_
Sample Movement             sm_
Detector Rotation           dr_
Data Table                  dt_

Q-Types: Capital letters of the type; 
ex:
QMainWindow                 _qmw
QPushButton                 _qpb

EXCEPTIONS: 
QCheckBox = qckbx
QProgressBar = qpbar
"""

from middleware import MotionController  # , list_all_devices
from PyQt5 import QtCore
import signal
from utilities import version
from middleware import Detector
from utilities import log
from utilities import motion_controller_list as mcl
from instruments.mcpherson import McPherson
from utilities_qt import connect_devices
from utilities_qt import update_position_displays
from utilities_qt import scan
from utilities_qt.datatable import DataTableWidget
from PyQt5.QtWidgets import QGraphicsView
import webbrowser
from utilities.config import load_config_devman, save_config_devman, load_config, save_config, reset_config
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
import matplotlib
import copy
from functools import partial
import datetime as dt
import numpy as np
import weakref
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QMainWindow, QDoubleSpinBox, QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QRadioButton, QSizePolicy,
                             QStyle, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QTabWidget, QTableWidgetItem, QFrame, QProgressBar, QCheckBox, QSpinBox, QStatusBar, QAction, QSpacerItem, QGroupBox)
from PyQt5.QtGui import QColor, QFontDatabase, QFont
from PyQt5.QtCore import (pyqtSignal, QFileInfo, QEvent,
                          QFile, QIODevice, QTimer, QPropertyAnimation, QEasingCurve)
from PyQt5 import uic
import sys
import traceback as tb
import os
import hashlib
import faulthandler
import math
import typing
import subprocess
from typing import Callable
from typing_extensions import Self
faulthandler.enable()

# OS and SYS Imports

# Obtains the executable directory (as exeDir) and the application directory (as appDir) for future use.
try:
    exeDir = sys._MEIPASS
except Exception:
    exeDir = os.getcwd()

if getattr(sys, 'frozen', False):
    appDir = os.path.dirname(sys.executable)
elif __file__:
    appDir = os.path.dirname(__file__)

# PyQt Imports

# More Standard Imports

matplotlib.use('Qt5Agg')

# Custom Imports


try:
    import middleware as mw
except Exception as e:
    log.error(str(e))
    raise e


QtWidgets.QApplication.setAttribute(
    QtCore.Qt.AA_EnableHighDpiScaling, True)  # enable highdpi scaling
QtWidgets.QApplication.setAttribute(
    QtCore.Qt.AA_UseHighDpiPixmaps, True)  # use highdpi icons

# Setup signal.
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Setup fonts variables.
digital_7_italic_22 = None
digital_7_16 = None

# Determines which enabler files exist - these will enable certain experimental or advanced sections of the program.
SHOW_FILTER_WHEEL = os.path.isfile('enable.exp')
# SHOW_SAMPLE_MOVEMENT = os.path.isfile('enable.adv')
SHOW_SAMPLE_MOVEMENT = True
# SHOW_DETECTOR_ROTATION = os.path.isfile('enable.adv')
SHOW_DETECTOR_ROTATION = True
ALLOW_DUMMY_MODE = os.path.isfile('enable.dev')

# Classes.

# Sets up the navigation toolbar for the graph.


class NavigationToolbar(NavigationToolbar2QT):
    def edit_parameters(self):
        super(NavigationToolbar, self).edit_parameters()

# Sets up the canvas for the graph.


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self:Self, parent=None, width:float=5, height:float=4, dpi:int=100, xlabel:str='Position (nm or deg)', ylabel:str='Magnitude (pA or V)'):

        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout=True)

        self._parent = parent
        self.axes = fig.add_subplot(111)
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.axes.set_xlabel(self.xlabel)
        self.axes.set_ylabel(self.ylabel)
        self.axes.grid()
        self.lines = dict()
        self.colors = ['b', 'r', 'k', 'c', 'g', 'm', 'tab:orange']
        self._tableClearCb = None
        super(MplCanvas, self).__init__(fig)

    def get_toolbar(self:Self) -> NavigationToolbar:
        self.toolbar = NavigationToolbar(self, self._parent)
        return self.toolbar

    def set_table_clear_cb(self:Self, fcn:Callable[[object], None]) -> None:
        self._tableClearCb = fcn

    def clear_plot_fcn(self:Self, det_idx:int):
        if not self._parent.scanRunning:
            self.axes.cla()
            self.axes.set_xlabel(self.xlabel)
            self.axes.set_ylabel(self.ylabel)
            self.axes.grid()
            self.draw()
            if self._tableClearCb is not None:
                self._tableClearCb()
        return

    def update_plots(self:Self, data: list):
        self.axes.cla()
        self.axes.set_xlabel(self.xlabel)
        self.axes.set_ylabel(self.ylabel)
        for row in data:
            c = self.colors[row[-1] % len(self.colors)]
            log.warn(f"Plotting: {row[0]} ; {row[1]}")
            if len(row[0]) != len(row[1]):
                log.error('X and Y data lengths do not match!')
                continue
            self.lines[row[-1]
                       ], = self.axes.plot(row[0], row[1], label=row[2], color=c)
        self.axes.legend()
        self.axes.grid()
        self.draw()
        return

    def append_plot(self, idx, xdata, ydata):
        if idx not in self.lines.keys():
            c = self.colors[idx % len(self.colors)]
            self.lines[idx], = self.axes.plot(
                xdata, ydata, label='Scan #%d' % (idx), color=c)
        else:
            self.lines[idx].set_data(xdata, ydata)
        self.draw()

# The main MMC program and GUI class.


class MMC_Main(QMainWindow):
    # STARTUP PROCEDURE
    # Begins by starting the Device Manager window.
    # Once devices are selected and connected, the Main GUI window is launched.

    # MMC_Main.__init__() --> show_window_device_manager() >>> emits device_manager_ready_signal
    # --> autoconnect_devices() >>> emits devices_auto_connected_signal
    # --> devices_auto_connected()
    # IF devices connected --> _show_main_gui()
    # ELSE allow user to interact w/ device manager

    SIGNAL_device_manager_ready = pyqtSignal()
    SIGNAL_devices_connection_check = pyqtSignal(bool, list, list)

    EXIT_CODE_FINISHED = 0
    EXIT_CODE_REBOOT = 1

    # Destructor
    def __del__(self):
        if self.motion_controllers is not None:
            del self.motion_controllers
        if self.mtn_ctrls is not None:
            del self.mtn_ctrls
        if self.detectors is not None:
            del self.detectors
        if self.dev_finder is not None:
            self.dev_finder.done = True
            del self.dev_finder

    # Constructor
    def __init__(self, application, uiresource=None):

        self.global_scan_id = 0
        self.scan_start_delay = 0.0
        self.detection_delay = 0.0
        self.per_detection_averages = 1

        try:
            self.git_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
        except Exception as e:
            log.error('Not a Git repo: Unable to get git hash: %s' % (str(e)))
            log.warn('Not a Git repo: Did you download the source code from GitHub as a zip file?')
            log.warn('Not a Git repo: To maintain the proper version hash, please use `git clone [URL]` instead.')
            self.git_hash = 'No Hash'

        self.selected_config_save_path = os.path.expanduser(
            '~/Documents') + '/mcpherson_mmc/s_d.csv'

        # Handles the initial showing of the UI.
        self.mtn_ctrls = []
        self.detectors = []

        self.connect_devices_thread = connect_devices.ConnectDevices(
            weakref.proxy(self))
        self.connecting_devices = False

        self.update_position_displays_thread = update_position_displays.UpdatePositionDisplays(
            weakref.proxy(self))

        self.queue_executor_thread = scan.QueueExecutor(weakref.proxy(self))

        self.autosave_next_scan = False

        self.application: QApplication = application
        self._startup_args = self.application.arguments()

        super(MMC_Main, self).__init__()
        uic.loadUi(uiresource, self)

        self.setWindowIcon(QtGui.QIcon(exeDir + '/res/faviconV2.png'))

        self.SIGNAL_device_manager_ready.connect(self.connect_devices)
        self.SIGNAL_devices_connection_check.connect(
            self.devices_connection_check)

        self.dev_man_win_enabled = False
        self.main_gui_booted = False
        self.dmw = None
        self.show_window_device_manager()
        self.dev_finder = None

        self.scan_queue = None
        self.autosave_next_dir = None

        self.motion_controllers = mcl.MotionControllerList()

        # Load Configuration File
        self.moving = False
        
        self.movement_sensitive_buttons_disabled = False

        # Default measurement sign.
        self.mes_sign = 1

        # Default grating equation values.
        self.max_pos = 600.0
        self.min_pos = -40.0
        self.model_index = 0
        self.grating_density = 1200.0  # grooves/mm

        self.zero_ofst = 37.8461  # nm
        self.fw_offset = 0.0
        self.st_offset = 0.0
        self.sr_offset = 0.0
        self.sa_offset = 0.0
        self.dr_offset = 0.0

        # Other settings' default values.
        self.main_axis_index = 0
        self.filter_axis_index = 0
        self.rsamp_axis_index = 0
        self.asamp_axis_index = 0
        self.tsamp_axis_index = 0
        self.detector_axis_index = 0

        self.main_axis_dev_name = 'none'
        self.filter_axis_dev_name = 'none'
        self.rsamp_axis_dev_name = 'none'
        self.asamp_axis_dev_name = 'none'
        self.tsamp_axis_dev_name = 'none'
        self.detector_axis_dev_name = 'none'
        self.num_axes_at_time_of_save = 0

        self.fw_max_pos = 9999
        self.fw_min_pos = -9999
        self.smr_max_pos = 9999
        self.smr_min_pos = -9999
        self.sma_max_pos = 9999
        self.sma_min_pos = -9999
        self.smt_max_pos = 9999
        self.smt_min_pos = -9999
        self.dr_max_pos = 9999
        self.dr_min_pos = -9999

        self.md_sp = 0.0
        self.fw_sp = 0.0
        self.sr_sp = 0.0
        self.sa_sp = 0.0
        self.st_sp = 0.0
        self.dr_sp = 0.0

        self.load_config(appDir, False)

        self.manual_position = 0  # 0 nm
        self.startpos = 0
        self.stoppos = 0
        self.steppos = 0.1

        self.reference_operation = 0
        self.reference_order_meas_ref = True

    def eventFilter(self, source, event):
        if event.type() == QEvent.Wheel:
            return True
        return super().eventFilter(source, event)

    # Screen shown during startup to disable premature user interaction as well as handle device-not-found issues.
    def show_window_device_manager(self):

        self.device_timer = None
        if self.dmw is None:
            ui_file_name = exeDir + '/ui/device_manager.ui'
            ui_file = QFile(ui_file_name)
            if not ui_file.open(QIODevice.ReadOnly):
                log.fatal(
                    f"Cannot open {ui_file_name}: {ui_file.errorString()}")
                raise RuntimeError('Could not load grating input UI file')

            self.dmw = QDialog(self)  # pass parent window
            uic.loadUi(ui_file, self.dmw)

            self.dmw.setWindowTitle('%s (%s-%s)'%(version.__long_name__, version.__version__, self.git_hash))
            self.dmw_list = ''

            self.UIEL_dmw_detector_qhbl = []
            self.UIEL_dmw_detector_qhbl.append(
                self.dmw.findChild(QHBoxLayout, "detector_combo_sublayout"))

            self.UIEL_dmw_mtn_ctrl_qhbl = []
            self.UIEL_dmw_mtn_ctrl_qhbl.append(
                self.dmw.findChild(QHBoxLayout, "mtn_ctrl_combo_sublayout"))

            self.UIEL_dmw_detector_qcb = []
            self.UIEL_dmw_detector_qcb.append(
                self.dmw.findChild(QComboBox, "samp_combo"))
            self.UIEL_dmw_detector_qcb[0].addItem("NO DEVICE SELECTED")
            self.UIEL_dmw_detector_model_qcb = []
            self.UIEL_dmw_detector_model_qcb.append(
                self.dmw.findChild(QComboBox, "samp_model_combo"))
            for device in Detector.SupportedDevices:
                self.UIEL_dmw_detector_model_qcb[0].addItem(device)

            self.UIEL_dmw_mtn_ctrl_qcb = []
            self.UIEL_dmw_mtn_ctrl_qcb.append(
                self.dmw.findChild(QComboBox, "mtn_combo"))
            self.UIEL_dmw_mtn_ctrl_qcb[0].addItem("NO DEVICE SELECTED")
            self.UIEL_dmw_mtn_ctrl_model_qcb = []
            self.UIEL_dmw_mtn_ctrl_model_qcb.append(
                self.dmw.findChild(QComboBox, "mtn_model_combo"))
            for device in MotionController.SupportedDevices:
                self.UIEL_dmw_mtn_ctrl_model_qcb[0].addItem(device)

            self.UIE_dmw_accept_qpb: QPushButton = self.dmw.findChild(
                QPushButton, "acc_button")
            self.UIE_dmw_accept_qpb.clicked.connect(self.connect_devices)
            self.UIE_dmw_cancel_qpb: QPushButton = self.dmw.findChild(
                QPushButton, "cancel_button")
            self.UIE_dmw_cancel_qpb.clicked.connect(
                self.cancel_connect_devices)
            self.UIE_dmw_cancel_qpb.setEnabled(False)
            self.UIE_dmw_dummy_qckbx: QCheckBox = self.dmw.findChild(
                QCheckBox, "dum_checkbox")
            self.UIE_dmw_dummy_qckbx.setChecked(len(self._startup_args) == 2)

            if not ALLOW_DUMMY_MODE:
                self.UIE_dmw_dummy_qckbx.hide()

            self.UIE_dmw_loading_status_ql: QLabel = self.dmw.findChild(
                QLabel, 'current_loading_status')

            self.UIE_dmw_num_detectors_qsb: QSpinBox = self.dmw.findChild(
                QSpinBox, "num_detectors")
            self.UIE_dmw_num_detectors_qsb.valueChanged.connect(
                self.update_num_detectors_ui)
            self.num_detectors = 1

            self.UIE_dmw_mc_add_qpb: QPushButton = self.dmw.findChild(
                QPushButton, "mc_add")
            self.UIE_dmw_mc_add_qpb.clicked.connect(self.mc_add_fn)
            self.UIE_dmw_mc_sub_qpb: QPushButton = self.dmw.findChild(
                QPushButton, "mc_sub")
            self.UIE_dmw_mc_sub_qpb.clicked.connect(self.mc_sub_fn)
            self.UIE_dmw_d_add_qpb: QPushButton = self.dmw.findChild(
                QPushButton, "d_add")
            self.UIE_dmw_d_add_qpb.clicked.connect(self.d_add_fn)
            self.UIE_dmw_d_sub_qpb: QPushButton = self.dmw.findChild(
                QPushButton, "d_sub")
            self.UIE_dmw_d_sub_qpb.clicked.connect(self.d_sub_fn)

            self.UIE_dmw_num_motion_controllers_qsb: QSpinBox = self.dmw.findChild(
                QSpinBox, "num_motion_controllers")
            self.UIE_dmw_num_motion_controllers_qsb.valueChanged.connect(
                self.update_num_motion_controllers_ui)
            self.num_motion_controllers = 1

            self.UIE_dmw_detector_combo_qvbl: QVBoxLayout = self.dmw.findChild(
                QVBoxLayout, "detector_combo_layout")
            self.UIE_dmw_mtn_ctrl_combo_qvbl: QVBoxLayout = self.dmw.findChild(
                QVBoxLayout, "mtn_ctrl_combo_layout")
            self.UIE_dmw_load_bar_qpb: QProgressBar = self.dmw.findChild(
                QProgressBar, "loading_bar")

            self.UIE_dmw_load_spinner_ql: QLabel = self.dmw.findChild(
                QLabel, "load_spinner")

            self.devman_list_devices(True)

            self.dmw.show()

        # UIE_dmw_load_spinner_ql
        self.anim_dmw_load_spinner = QtGui.QMovie(exeDir + '/res/131.gif')
        self.UIE_dmw_load_spinner_ql.setMovie(self.anim_dmw_load_spinner)

        self.application.processEvents()

        if not self.dev_man_win_enabled:
            self.dev_man_win_enabled = True
            self.device_timer = QTimer()
            self.device_timer.timeout.connect(self.devman_list_devices)

            # Devices are checked for every this many milliseconds.
            # TODO: Is this causing the lag when a KST201 is connected? Fix this if so. It may need a longer timeout than 1000 ms.
            self.device_timer.start(10000)

        if log.logging_to_file():
            log.info('Log file is active.')
        else:
            log.warn('Log file is not active.')
            self.QMessageBoxCritical(
                'Log File Error', 'The software was unable to create the log file. This is likely due to a lack of permissions. Try running the program as an Administrator or no error logs will be produced.')

    # Called when the main GUI window is closed.
    def closeEvent(self, event):
        answer = self.QMessageBoxYNC(
            'Exit Confirmation', "Do you want to save all current settings and values?")
        event.ignore()
        if answer == 0:
            log.info('Exiting program and saving current configuration.')
            self.save_config(appDir + '/config.ini')
            event.accept()
        elif answer == 1:
            log.info('Exiting program without saving current configuration.')
            event.accept()
        else:
            log.info('Canceling program exit.')

    def d_add_fn(self):
        self.UIE_dmw_num_detectors_qsb.setValue(
            self.UIE_dmw_num_detectors_qsb.value() + 1)
        pass

    def d_sub_fn(self):
        self.UIE_dmw_num_detectors_qsb.setValue(
            self.UIE_dmw_num_detectors_qsb.value() - 1)
        pass

    def mc_add_fn(self):
        self.UIE_dmw_num_motion_controllers_qsb.setValue(
            self.UIE_dmw_num_motion_controllers_qsb.value() + 1)
        pass

    def mc_sub_fn(self):
        self.UIE_dmw_num_motion_controllers_qsb.setValue(
            self.UIE_dmw_num_motion_controllers_qsb.value() - 1)
        pass

    def update_num_detectors_ui(self, force: bool = False):
        if (self.num_detectors != self.UIE_dmw_num_detectors_qsb.value()) or (force):
            self.num_detectors = self.UIE_dmw_num_detectors_qsb.value()
            for widget in self.UIEL_dmw_detector_qcb:
                widget.setParent(None)
            for widget in self.UIEL_dmw_detector_model_qcb:
                widget.setParent(None)
            for layout in self.UIEL_dmw_detector_qhbl:
                self.UIE_dmw_detector_combo_qvbl.removeItem(layout)

            self.UIEL_dmw_detector_qcb = []
            self.UIEL_dmw_detector_model_qcb = []
            self.UIEL_dmw_detector_qhbl = []

            for i in range(self.num_detectors):
                s_combo = QComboBox()
                s_combo.addItem("NO DEVICE SELECTED")
                for dev in self.dev_list:
                    s_combo.addItem('%s' % (dev))
                m_combo = QComboBox()
                for device in Detector.SupportedDevices:
                    m_combo.addItem(device)
                layout = QHBoxLayout()
                layout.addWidget(s_combo)
                layout.addWidget(m_combo)
                layout.setStretch(0, 4)
                layout.setStretch(1, 1)
                self.UIE_dmw_detector_combo_qvbl.addLayout(layout)
                self.UIEL_dmw_detector_qcb.append(s_combo)
                self.UIEL_dmw_detector_model_qcb.append(m_combo)
                self.UIEL_dmw_detector_qhbl.append(layout)

        log.debug('new detectors combo list len: %d' %
                  (len(self.UIEL_dmw_detector_qcb)))

    def update_num_motion_controllers_ui(self, force: bool = True):
        if (self.num_motion_controllers != self.UIE_dmw_num_motion_controllers_qsb.value()) or (force):
            self.num_motion_controllers = self.UIE_dmw_num_motion_controllers_qsb.value()
            for widget in self.UIEL_dmw_mtn_ctrl_qcb:
                widget.setParent(None)
            for widget in self.UIEL_dmw_mtn_ctrl_model_qcb:
                widget.setParent(None)
            for layout in self.UIEL_dmw_mtn_ctrl_qhbl:
                self.UIE_dmw_mtn_ctrl_combo_qvbl.removeItem(layout)

            # Very important - must reset the combos list.
            self.UIEL_dmw_mtn_ctrl_qcb = []
            self.UIEL_dmw_mtn_ctrl_model_qcb = []
            self.UIEL_dmw_mtn_ctrl_qhbl = []

            for i in range(self.num_motion_controllers):
                s_combo = QComboBox()
                s_combo.addItem("NO DEVICE SELECTED")
                for dev in self.dev_list:
                    s_combo.addItem('%s' % (dev))
                m_combo = QComboBox()
                for device in MotionController.SupportedDevices:
                    m_combo.addItem(device)
                layout = QHBoxLayout()
                layout.addWidget(s_combo)
                layout.addWidget(m_combo)
                layout.setStretch(0, 4)
                layout.setStretch(1, 1)
                self.UIE_dmw_mtn_ctrl_combo_qvbl.addLayout(layout)
                self.UIEL_dmw_mtn_ctrl_qcb.append(s_combo)
                self.UIEL_dmw_mtn_ctrl_model_qcb.append(m_combo)
                self.UIEL_dmw_mtn_ctrl_qhbl.append(layout)

        log.debug('new mtn ctrls combo list len: %d' %
                  (len(self.UIEL_dmw_mtn_ctrl_qcb)))

    def connect_devices(self):
        # Save the current states of the devman immediately when Accept is pressed.
        """ Parameters we want to save.
        - Number of detectors.
        - Spinbox index 
        """

        self.UIE_dmw_load_spinner_ql.show()
        self.anim_dmw_load_spinner.start()

        if self.num_detectors == 1 and self.UIEL_dmw_detector_qcb[0].currentIndex() == 0:
            self.QMessageBoxInformation(
                'No Detectors Selected', 'No detectors selected: will run without a detector.')
            self.detectors = []  # This should allow for loops to auto-skip.
            self.num_detectors = 0
        else:
            try:
                for i in range(self.num_detectors):
                    if self.UIEL_dmw_detector_qcb[i].currentIndex() == 0:
                        self.QMessageBoxInformation(
                            'Connection Failure', 'No detector was selected for entry #%d.' % (i))
                        self.anim_dmw_load_spinner.stop()
                        self.UIE_dmw_load_spinner_ql.hide()
                        return
            except Exception as e:
                log.error(str(e))
                self.QMessageBoxCritical(
                    'Connection Failure', 'An error occurred while attempting to connect to the detector.\n%s' % (str(e)))
                self.anim_dmw_load_spinner.stop()
                self.UIE_dmw_load_spinner_ql.hide()
                return

        for i in range(self.num_motion_controllers):
            try:
                if self.UIEL_dmw_mtn_ctrl_qcb[i].currentIndex() == 0:
                    self.QMessageBoxInformation(
                        'Connection Failure', 'No motion controller was selected for entry #%d.' % (i))
                    self.anim_dmw_load_spinner.stop()
                    self.UIE_dmw_load_spinner_ql.hide()
                    return
            except Exception as e:
                log.error(str(e))
                self.QMessageBoxCritical(
                    'Connection Failure', 'An error occurred while attempting to connect to the motion controller.\n%s' % (str(e)))
                self.anim_dmw_load_spinner.stop()
                self.UIE_dmw_load_spinner_ql.hide()
                return

        # Save config here.
        self.save_config_devman(appDir + '/devman.ini')

        if not self.connecting_devices:
            self.connect_devices = True

            self.UIE_dmw_cancel_qpb.setEnabled(True)
            self.UIE_dmw_accept_qpb.setEnabled(False)
            self.application.processEvents()
            self.dummy = self.UIE_dmw_dummy_qckbx.isChecked()

            self.connect_devices_thread.start()

    def cancel_connect_devices(self):
        # TODO: Implement device connection cancelation.
        log.warn('Cancelling device connections is not yet implemented.')

    def _connect_devices(self, detectors_connected, mtn_ctrls_connected):
        self.connecting_devices = False
        self.UIE_dmw_cancel_qpb.setEnabled(False)
        self.UIE_dmw_accept_qpb.setEnabled(True)
        self.SIGNAL_devices_connection_check.emit(
            self.dummy, detectors_connected, mtn_ctrls_connected)

    def _connect_devices_failure_cleanup(self):
        self._connect_devices_progress_anim(0)
        self.connecting_devices = False
        self.UIE_dmw_cancel_qpb.setEnabled(False)
        self.UIE_dmw_accept_qpb.setEnabled(True)
        self.anim_dmw_load_spinner.stop()
        self.UIE_dmw_load_spinner_ql.hide()

    def _connect_devices_status(self, message):
        self.UIE_dmw_loading_status_ql.setText(message)

    def _connect_devices_progress_anim(self, value):
        self.anim = QPropertyAnimation(
            targetObject=self.UIE_dmw_load_bar_qpb, propertyName=b"value")
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self.UIE_dmw_load_bar_qpb.value())
        self.anim.setEndValue(value)
        self.anim.setDuration(5000)
        self.anim.start()

    # If things are connected, boot main GUI.
    # If somethings wrong, enable advanced dev man functions.
    def devices_connection_check(self, dummy: bool, detectors: list, mtn_ctrls: list):
        connected = True
        for status in detectors:
            if not status:
                connected = False
                break
        if connected:
            for status in mtn_ctrls:
                if not status:
                    connected = False
                    break

        if connected:
            if self.device_timer is not None:
                log.warn('STOPPING DEVICE TIMER!')
                self.device_timer.stop()
            self._show_main_gui(dummy)
            return

        # If we are here, then we have not automatically connected to all required devices. We must now enable the device manager.
        self.QMessageBoxWarning(
            'Connection Failure', 'Connection attempt has failed!\n%s' % (mtn_ctrls))

    def _show_main_gui(self, dummy: bool):
        # Set this via the QMenu QAction Edit->Change Auto-log Directory
        self.data_save_directory = os.path.expanduser('~/Documents')
        self.data_save_directory += '/mcpherson_mmc/%s/' % (
            dt.datetime.now().strftime('%Y%m%d'))
        if not os.path.exists(self.data_save_directory):
            os.makedirs(self.data_save_directory)

        self.num_scans = 0
        self.previous_position = -9999
        self.immobile_count = 0

        # The data we are using as a reference post-operation (if applicable).
        # e.g., the result of sample_scan/ref_scan
        self.operated_ref_data = None
        self.reference_active = False
        self.is_advanced_ref = False

        self.autosave_data_bool = False
        self.pop_out_table = False
        self.pop_out_plot = False
        self.mda_moving = False
        self.fwa_moving = False
        self.sra_moving = False
        self.saa_moving = False
        self.sta_moving = False
        self.dra_moving = False
        self.scanRunning = False

        self.machine_conf_win: QDialog = None
        self.grating_conf_win: QDialog = None
        self.spectral_ops_win: QDialog = None
        self.grating_density_in: QDoubleSpinBox = None

        self.UIE_mcw_max_pos_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_min_pos_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_zero_ofst_in_qdsb: QDoubleSpinBox = None

        self.UIE_mcw_machine_conf_qpb: QPushButton = None

        self.UIE_mcw_steps_per_nm_qdsb: QDoubleSpinBox = None
        
        if ALLOW_DUMMY_MODE:
            if dummy:
                self.setWindowTitle('%s (%s-%s-DB)'%(version.__long_name__, version.__version__, self.git_hash))
            else:
                self.setWindowTitle('%s (%s-%s-HW)'%(version.__long_name__, version.__version__, self.git_hash))
        else:
            self.setWindowTitle('%s (%s-%s)'%(version.__long_name__, version.__version__, self.git_hash))

        self.is_conv_set = False  # Use this flag to set conversion

        # GUI initialization, gets the UI elements from the .ui file.
        self.UIE_mgw_scan_qpb: QPushButton = self.findChild(
            QPushButton, "begin_scan_button")  # Scanning Control 'Begin Scan' Button
        pixmapi = getattr(QStyle, 'SP_ArrowForward')
        icon = self.style().standardIcon(pixmapi)
        self.UIE_mgw_scan_qpb.setIcon(icon)
        self.UIE_mgw_stop_scan_qpb: QPushButton = self.findChild(
            QPushButton, "stop_scan_button")
        pixmapi = getattr(QStyle, 'SP_BrowserStop')
        icon = self.style().standardIcon(pixmapi)
        self.UIE_mgw_stop_scan_qpb.setIcon(icon)
        self.UIE_mgw_stop_scan_qpb.setEnabled(False)
        self.UIE_mgw_save_data_qckbx: QCheckBox = self.findChild(
            QCheckBox, "save_data_checkbox")  # Scanning Control 'Save Data' Checkbox
        self.UIE_mgw_dir_box_qle = self.findChild(
            QLineEdit, "save_dir_lineedit")
        self.UIE_mgw_start_qdsb = self.findChild(
            QDoubleSpinBox, "start_set_spinbox")
        self.UIE_mgw_stop_qdsb = self.findChild(
            QDoubleSpinBox, "end_set_spinbox")

        if dummy:
            self.UIE_mgw_stop_qdsb.setValue(10.0)

        # self.UIE_mgw_mca_pos_ql = self.findChild(QLabel, "mca_pos")
        self.UIE_mgw_fwa_pos_ql = self.findChild(QLabel, "fwa_pos")
        self.UIE_mgw_sra_pos_ql = self.findChild(QLabel, "sra_pos")
        self.UIE_mgw_saa_pos_ql = self.findChild(QLabel, "saa_pos")
        self.UIE_mgw_sta_pos_ql = self.findChild(QLabel, "sta_pos")
        self.UIE_mgw_dra_pos_ql = self.findChild(QLabel, "dra_pos")

        self.UIE_mgw_step_qdsb = self.findChild(
            QDoubleSpinBox, "step_set_spinbox")
        self.UIE_mgw_currpos_nm_disp_ql = self.findChild(QLabel, "currpos_nm")
        self.UIE_mgw_scan_status_ql = self.findChild(QLabel, "status_label")
        self.UIE_mgw_scan_qpbar = self.findChild(QProgressBar, "progressbar")
        self.UIE_mgw_scan_time_ql = self.findChild(QLabel, "scan_time")
        self.scan_remaining_timer = QtCore.QTimer(self)        
        self.scan_time_left = 0.0

        self.UIE_mgw_save_config_qpb: QPushButton = self.findChild(
            QPushButton, 'save_config_button')
        self.UIE_mgw_spectral_ops_qpb: QPushButton = self.findChild(
            QPushButton, 'spectral_math')
        self.UIE_mgw_spectral_ops_qpb.clicked.connect(
            self.show_window_spectral_ops)
        self.UIE_mgw_spectral_ops_qpb.hide()
        self.UIE_mgw_pos_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, "pos_set_spinbox")  # Manual Control 'Position:' Spin Box
        self.UIE_mgw_move_to_position_qpb: QPushButton = self.findChild(
            QPushButton, "move_pos_button")
        
        self.UIE_mgw_xmin_in_qle: QLineEdit = self.findChild(
            QLineEdit, "xmin_in")
        self.UIE_mgw_ymin_in_qle: QLineEdit = self.findChild(
            QLineEdit, "ymin_in")
        self.UIE_mgw_xmax_in_qle: QLineEdit = self.findChild(
            QLineEdit, "xmax_in")
        self.UIE_mgw_ymax_in_qle: QLineEdit = self.findChild(
            QLineEdit, "ymax_in")
        
        self.UIE_mgw_plot_clear_plots_qpb: QPushButton = self.findChild(
            QPushButton, "clear_plots_button")

        self.UIE_mgw_machine_conf_qa: QAction = self.findChild(
            QAction, "machine_configuration")
        self.UIE_mgw_invert_mes_qa: QAction = self.findChild(
            QAction, "invert_mes")
        self.UIE_mgw_autosave_data_qa: QAction = self.findChild(
            QAction, "autosave_data")
        self.UIE_mgw_autosave_dir_qa: QAction = self.findChild(
            QAction, "autosave_dir_prompt")
        self.UIE_mgw_preferences_qa: QAction = self.findChild(
            QAction, "preferences")
        self.UIE_mgw_pop_out_table_qa: QAction = self.findChild(
            QAction, "pop_out_table")
        self.UIE_mgw_pop_out_plot_qa: QAction = self.findChild(
            QAction, "pop_out_plot")
        self.UIE_mgw_about_source_qa: QAction = self.findChild(
            QAction, "actionSource_Code")
        self.UIE_mgw_about_licensing_qa: QAction = self.findChild(
            QAction, "actionLicensing")
        self.UIE_mgw_about_manual_qa: QAction = self.findChild(
            QAction, "actionManual_2")

        self.UIE_mgw_import_qa: QAction = self.findChild(
            QAction, "actionImport_Config")
        self.UIE_mgw_export_qa: QAction = self.findChild(
            QAction, "actionExport_Config")
        self.UIE_mgw_save_current_config_qa: QAction = self.findChild(
            QAction, "actionSave_Current_Config")
        self.UIE_mgw_import_qa.triggered.connect(self.config_import)
        self.UIE_mgw_export_qa.triggered.connect(self.config_export)
        self.UIE_mgw_save_current_config_qa.triggered.connect(self.config_save)

        self.UIE_mgw_save_data_qpb: QPushButton = self.findChild(
            QPushButton, 'save_data_button')
        self.UIE_mgw_save_data_qpb.clicked.connect(self.save_data_cb)
        self.UIE_mgw_delete_data_qpb: QPushButton = self.findChild(
            QPushButton, 'delete_data_button')
        self.UIE_mgw_delete_data_qpb.clicked.connect(self.delete_data_cb)

        self.UIE_mgw_ref_det_qcb: QComboBox = self.findChild(
            QComboBox, 'ref_det')
        self.UIE_mgw_sample_det_qcb: QComboBox = self.findChild(
            QComboBox, 'sample_det')

        for i in range(self.num_detectors):
            self.UIE_mgw_ref_det_qcb.addItem('Det %d' % (i+1))

        for i in range(self.num_detectors):
            self.UIE_mgw_sample_det_qcb.addItem('Det %d' % (i+1))

        self.UIE_mgw_setref_qpb: QPushButton = self.findChild(
            QPushButton, 'fir_order_ref_set')
        self.UIE_mgw_setop_qcb: QComboBox = self.findChild(
            QComboBox, 'fir_order_ref_op')
        self.UIE_mgw_setr1_qpb: QPushButton = self.findChild(
            QPushButton, 'sec_order_ref_setr1')
        # self.UIE_mgw_setop1_qcb: QComboBox = self.findChild(QComboBox, 'sec_order_ref_op1')
        self.UIE_mgw_setr2_qpb: QPushButton = self.findChild(
            QPushButton, 'sec_order_ref_setr2')
        # self.UIE_mgw_setop2_qcb: QComboBox = self.findChild(QComboBox, 'sec_order_ref_op2')
        self.UIE_mgw_ref_collap_qpb: QPushButton = self.findChild(
            QPushButton, 'ref_collap')
        self.ref_collapsed = False
        self.UIE_mgw_ref_area_qw: QWidget = self.findChild(QWidget, 'ref_area')
        self.UIE_mgw_ref_reset_qpb: QPushButton = self.findChild(
            QPushButton, 'ref_reset')
        self.UIE_mgw_ref_enact_qpb: QPushButton = self.findChild(
            QPushButton, 'ref_enact')
        self.UIE_mgw_ref_simple_qrb: QRadioButton = self.findChild(
            QRadioButton, 'ref_simple')
        self.UIE_mgw_ref_advanced_qrb: QRadioButton = self.findChild(
            QRadioButton, 'ref_advanced')
        self.UIE_mgw_simple_opbox_qgb: QGroupBox = self.findChild(
            QGroupBox, 'simple_opbox')
        self.UIE_mgw_advanced_opbox_qgb: QGroupBox = self.findChild(
            QGroupBox, 'advanced_opbox')
        self.UIE_mgw_advanced_opbox_qgb.hide()

        self.ref_collapsed = True
        self.UIE_mgw_ref_area_qw.setVisible(False)
        self.UIE_mgw_ref_collap_qpb.setText('∑ ⮜')

        self.ref0_data = None
        self.ref1_data = None
        self.ref2_data = None

        self.ref_det_idx = 0
        self.sample_det_idx = 0

        self.UIE_mgw_setref_qpb.clicked.connect(self.set_ref)
        self.UIE_mgw_setr1_qpb.clicked.connect(self.set_ref1)
        self.UIE_mgw_setr2_qpb.clicked.connect(self.set_ref2)
        self.UIE_mgw_ref_collap_qpb.clicked.connect(self.collapse_ref)
        self.UIE_mgw_ref_reset_qpb.clicked.connect(self.reset_ref)
        self.UIE_mgw_ref_enact_qpb.clicked.connect(self.enact_ref)

        self.UIE_mgw_ref_reset_qpb.setDisabled(True)

        self.UIE_mgw_ref_advanced_qrb.toggled.connect(self.toggle_ref)

        self.UIE_mgw_open_queue_file_qpb: QPushButton = self.findChild(
            QPushButton, 'open_queue_file_button')
        self.UIE_mgw_open_queue_file_qpb.clicked.connect(self.load_queue_file)

        self.UIE_mgw_begin_queue_qpb: QPushButton = self.findChild(
            QPushButton, 'begin_queue_button')
        self.UIE_mgw_begin_queue_qpb.clicked.connect(self.begin_queue)

        self.UIE_mgw_table_qtw: QTabWidget = self.findChild(
            QTabWidget, "table_tabs")

        self.UIE_mgw_mda_load_spinner_ql: QLabel = self.findChild(
            QLabel, "mda_load_spinner")
        self.anim_mgw_mda_load_spinner = QtGui.QMovie(
            exeDir + '/res/Thin stripes.gif')
        self.UIE_mgw_mda_load_spinner_ql.setMovie(
            self.anim_mgw_mda_load_spinner)
        self.anim_mgw_mda_load_spinner_running = False

        self.UIE_mgw_fwa_load_spinner_ql: QLabel = self.findChild(
            QLabel, "fwa_load_spinner")
        self.anim_mgw_fwa_load_spinner = QtGui.QMovie(
            exeDir + '/res/Thin stripes.gif')
        self.UIE_mgw_fwa_load_spinner_ql.setMovie(
            self.anim_mgw_fwa_load_spinner)
        self.anim_mgw_fwa_load_spinner_running = False

        self.UIE_mgw_sra_load_spinner_ql: QLabel = self.findChild(
            QLabel, "sra_load_spinner")
        self.anim_mgw_sra_load_spinner = QtGui.QMovie(
            exeDir + '/res/Thin stripes.gif')
        self.UIE_mgw_sra_load_spinner_ql.setMovie(
            self.anim_mgw_sra_load_spinner)
        self.anim_mgw_sra_load_spinner_running = False

        self.UIE_mgw_saa_load_spinner_ql: QLabel = self.findChild(
            QLabel, "saa_load_spinner")
        self.anim_mgw_saa_load_spinner = QtGui.QMovie(
            exeDir + '/res/Thin stripes.gif')
        self.UIE_mgw_saa_load_spinner_ql.setMovie(
            self.anim_mgw_saa_load_spinner)
        self.anim_mgw_saa_load_spinner_running = False

        self.UIE_mgw_sta_load_spinner_ql: QLabel = self.findChild(
            QLabel, "sta_load_spinner")
        self.anim_mgw_sta_load_spinner = QtGui.QMovie(
            exeDir + '/res/Thin stripes.gif')
        self.UIE_mgw_sta_load_spinner_ql.setMovie(
            self.anim_mgw_sta_load_spinner)
        self.anim_mgw_sta_load_spinner_running = False

        self.UIE_mgw_dra_load_spinner_ql: QLabel = self.findChild(
            QLabel, "dra_load_spinner")
        self.anim_mgw_dra_load_spinner = QtGui.QMovie(
            exeDir + '/res/Thin stripes.gif')
        self.UIE_mgw_dra_load_spinner_ql.setMovie(
            self.anim_mgw_dra_load_spinner)
        self.anim_mgw_dra_load_spinner_running = False

        # Setup the first (result) table tab.
        table = DataTableWidget(self)
        VLayout = QVBoxLayout()
        VLayout.addWidget(table)
        self.UIE_mgw_table_qtw.widget(0).setLayout(VLayout)
        self.table_result = table
        self.table_result.is_result = True
        self.UIE_mgw_table_result_tab = self.UIE_mgw_table_qtw.widget(0)

        self.table_list = []
        self.UIEL_mgw_table_tabs = []  # List of tabs.
        for i in range(self.num_detectors):
            if i > 0:
                self.UIE_mgw_table_qtw.addTab(QWidget(), 'Detector %d' % (i+1))

            table = DataTableWidget(self)
            VLayout = QVBoxLayout()
            VLayout.addWidget(table)
            # This is how you address individual tabs.
            self.UIE_mgw_table_qtw.widget(i+1).setLayout(VLayout)

            # TODO: Init all the tabs' layouts.

            # List of datatable objects.

            self.table_list.append(table)
            self.UIEL_mgw_table_tabs.append(self.UIE_mgw_table_qtw.widget(i+1))

        self.UIE_mgw_home_qpb: QPushButton = self.findChild(
            QPushButton, "home_button")
        self.UIE_mgw_home_all_axes_qpb: QPushButton = self.findChild(
            QPushButton, "home_all_axes")

        # The "Active Detectors" combo-box. Determines which detectors will run in a scan.
        self.UIE_mgw_enabled_detectors_qcb: QComboBox = self.findChild(
            QComboBox, "enabled_detectors")

        for i in range(self.num_detectors):
            self.UIE_mgw_enabled_detectors_qcb.addItem('Detector %d' % (i+1))

        # Get axes combos.
        self.UIE_mgw_main_drive_axis_qcb: QComboBox = self.findChild(
            QComboBox, "main_drive_axis")
        self.UIE_mgw_main_drive_axis_qcb.hide()
        self.UIE_mgw_filter_wheel_axis_qcb: QComboBox = self.findChild(
            QComboBox, "filter_wheel_axis")
        self.UIE_mgw_filter_wheel_axis_qcb.hide()
        self.UIE_mgw_sample_rotation_axis_qcb: QComboBox = self.findChild(
            QComboBox, "sample_rot_axis")
        self.UIE_mgw_sample_rotation_axis_qcb.hide()
        self.UIE_mgw_sample_angle_axis_qcb: QComboBox = self.findChild(
            QComboBox, 'sample_angle_axis')
        self.UIE_mgw_sample_angle_axis_qcb.hide()
        self.UIE_mgw_sample_translation_axis_qcb: QComboBox = self.findChild(
            QComboBox, "sample_trans_axis")
        self.UIE_mgw_sample_translation_axis_qcb.hide()
        self.UIE_mgw_detector_rotation_axis_qcb: QComboBox = self.findChild(
            QComboBox, "detector_axis")
        self.UIE_mgw_detector_rotation_axis_qcb.hide()

        self.findChild(QLabel, "label_24").hide()
        self.findChild(QLabel, "label_22").hide()
        self.findChild(QLabel, "label_15").hide()
        self.findChild(QLabel, "label_18").hide()
        self.findChild(QLabel, "label_21").hide()
        self.findChild(QLabel, "label_25").hide()

        self.UIE_mgw_main_drive_axis_qcb.addItem(
            '%s' % ('Select Main Drive Axis'))
        self.UIE_mgw_filter_wheel_axis_qcb.addItem(
            '%s' % ('Select Filter Wheel Axis'))
        self.UIE_mgw_sample_rotation_axis_qcb.addItem(
            '%s' % ('Select Sample Rotation Axis'))
        self.UIE_mgw_sample_angle_axis_qcb.addItem(
            '%s' % ('Select Sample Angle Axis'))
        self.UIE_mgw_sample_translation_axis_qcb.addItem(
            '%s' % ('Select Sample Translation Axis'))
        self.UIE_mgw_detector_rotation_axis_qcb.addItem(
            '%s' % ('Select Detector Rotation Axis'))

        self.UIE_mgw_pframe_1_qf: QFrame = self.findChild(QFrame, "pframe_1")
        self.UIE_mgw_pframe_2_qf: QFrame = self.findChild(QFrame, "pframe_2")
        self.UIE_mgw_pframe_3_qf: QFrame = self.findChild(QFrame, "pframe_3")
        self.UIE_mgw_pframe_4_qf: QFrame = self.findChild(QFrame, "pframe_4")
        self.UIE_mgw_pframe_5_qf: QFrame = self.findChild(QFrame, "pframe_5")
        self.UIE_mgw_pframe_6_qf: QFrame = self.findChild(QFrame, "pframe_6")

        self.UIE_mgw_main_drive_axis_qcb.currentIndexChanged.connect(
            self.mgw_axis_change_main)
        self.UIE_mgw_filter_wheel_axis_qcb.currentIndexChanged.connect(
            self.mgw_axis_change_filter)
        self.UIE_mgw_sample_rotation_axis_qcb.currentIndexChanged.connect(
            self.mgw_axis_change_rsamp)
        self.UIE_mgw_sample_angle_axis_qcb.currentIndexChanged.connect(
            self.mgw_axis_change_asamp)
        self.UIE_mgw_sample_translation_axis_qcb.currentIndexChanged.connect(
            self.mgw_axis_change_tsamp)
        self.UIE_mgw_detector_rotation_axis_qcb.currentIndexChanged.connect(
            self.mgw_axis_change_detector)

        # If anything has changed, we must use default values.
        changes = 0
        if len(self.mtn_ctrls) != self.num_axes_at_time_of_save:
            changes += 1
        log.debug('Length of self.mtn_ctrls: %d' % (len(self.mtn_ctrls)))
        if self.main_axis_index < len(self.mtn_ctrls):
            if self.mtn_ctrls[self.main_axis_index] is not None:
                if self.mtn_ctrls[self.main_axis_index].short_name() != self.main_axis_dev_name:
                    changes += 1
        else:
            changes += 1
        if self.filter_axis_index < len(self.mtn_ctrls):
            if self.mtn_ctrls[self.filter_axis_index] is not None:
                if self.mtn_ctrls[self.filter_axis_index].short_name() != self.filter_axis_dev_name:
                    changes += 1
        else:
            changes += 1
        if self.rsamp_axis_index < len(self.mtn_ctrls):
            if self.mtn_ctrls[self.rsamp_axis_index] is not None:
                if self.mtn_ctrls[self.rsamp_axis_index].short_name() != self.rsamp_axis_dev_name:
                    changes += 1
        else:
            changes += 1
        if self.asamp_axis_index < len(self.mtn_ctrls):
            if self.mtn_ctrls[self.asamp_axis_index] is not None:
                if self.mtn_ctrls[self.asamp_axis_index].short_name() != self.asamp_axis_dev_name:
                    changes += 1
        else:
            changes += 1
        if self.tsamp_axis_index < len(self.mtn_ctrls):
            if self.mtn_ctrls[self.tsamp_axis_index] is not None:
                if self.mtn_ctrls[self.tsamp_axis_index].short_name() != self.tsamp_axis_dev_name:
                    changes += 1
        else:
            changes += 1
        if self.detector_axis_index < len(self.mtn_ctrls):
            if self.mtn_ctrls[self.detector_axis_index] is not None:
                if self.mtn_ctrls[self.detector_axis_index].short_name() != self.detector_axis_dev_name:
                    changes += 1
        else:
            changes += 1

        if changes > 0:
            log.info('Using default CONNECTIONS values.')
            self.main_axis_index = 1
            self.filter_axis_index = 0
            self.rsamp_axis_index = 0
            self.asamp_axis_index = 0
            self.tsamp_axis_index = 0
            self.detector_axis_index = 0

        # Populate axes combos.
        for dev in self.mtn_ctrls:
            if dev is not None:
                log.info('Adding %s to config list.' % (dev))

                self.UIE_mgw_main_drive_axis_qcb.addItem(
                    '%s: %s' % (dev.port_name(), dev.short_name()))
                self.UIE_mgw_filter_wheel_axis_qcb.addItem(
                    '%s: %s' % (dev.port_name(), dev.short_name()))
                self.UIE_mgw_sample_rotation_axis_qcb.addItem(
                    '%s: %s' % (dev.port_name(), dev.short_name()))
                self.UIE_mgw_sample_angle_axis_qcb.addItem(
                    '%s: %s' % (dev.port_name(), dev.short_name()))
                self.UIE_mgw_sample_translation_axis_qcb.addItem(
                    '%s: %s' % (dev.port_name(), dev.short_name()))
                self.UIE_mgw_detector_rotation_axis_qcb.addItem(
                    '%s: %s' % (dev.port_name(), dev.short_name()))

        self.UIE_mgw_fw_mancon_position_set_qsb: QSpinBox = self.findChild(
            QSpinBox, 'filter_wheel_pos_set_spinbox')
        self.UIE_mgw_fw_mancon_move_pos_qpb: QPushButton = self.findChild(
            QPushButton, 'filter_wheel_move_pos_button')
        self.UIE_mgw_fw_mancon_home_qpb: QPushButton = self.findChild(
            QPushButton, 'filter_wheel_home_button')
        self.UIE_mgw_fw_add_rule_qpb: QPushButton = self.findChild(
            QPushButton, 'filter_wheel_add_rule_button')
        self.UIE_mgw_fw_add_rule_qpb.clicked.connect(
            self.new_filter_wheel_rule)

        self.UIE_mgw_sm_rpos_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'sample_rotate_spin')
        self.UIE_mgw_sm_tpos_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'sample_trans_spin')
        self.UIE_mgw_sm_rhome_qpb: QPushButton = self.findChild(
            QPushButton, 'sample_rotate_home_button')
        self.UIE_mgw_sm_thome_qpb: QPushButton = self.findChild(
            QPushButton, 'sample_trans_home_button')
        self.UIE_mgw_sm_rmove_qpb: QPushButton = self.findChild(
            QPushButton, 'sample_rotate_move_button')
        self.UIE_mgw_sm_tmove_qpb: QPushButton = self.findChild(
            QPushButton, 'sample_trans_move_button')
        self.UIE_mgw_sm_apos_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'sample_angle_spin')
        self.UIE_mgw_sm_amove_qpb: QPushButton = self.findChild(
            QPushButton, 'sample_angle_move_button')
        self.UIE_mgw_sm_ahome_qpb: QPushButton = self.findChild(
            QPushButton, 'sample_angle_home_button')
        self.UIE_mgw_dm_rpos_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'detector_rotate_spin')
        self.UIE_mgw_dm_rhome_qpb: QPushButton = self.findChild(
            QPushButton, 'detector_rotate_home_button')
        self.UIE_mgw_dm_rmove_qpb: QPushButton = self.findChild(
            QPushButton, 'detector_rotate_move_button')

        self.UIE_mgw_master_stop_qpb: QPushButton = self.findChild(
            QPushButton, 'master_stop_button')
        self.UIE_mgw_master_stop_qpb.clicked.connect(
            self.stop_master_button_pressed)

        self.UIE_mgw_sm_scan_type_qcb: QComboBox = self.findChild(
            QComboBox, 'scan_type_combo')
        self.UIE_mgw_sm_start_set_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'start_set_spinbox_2')
        self.UIE_mgw_sm_end_set_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'end_set_spinbox_2')
        self.UIE_mgw_sm_step_set_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'step_set_spinbox_2')
        self.UIE_mgw_sm_scan_repeats_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'scan_repeats_3')
        self.UIE_mgw_sm_begin_scan_qpb: QPushButton = self.findChild(
            QPushButton, 'begin_scan_button_3')
        self.UIE_mgw_sm_end_scan_qpb: QPushButton = self.findChild(
            QPushButton, 'stop_scan_button_3')
        self.UIE_mgw_dm_start_set_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'start_set_spinbox_3')
        self.UIE_mgw_dm_end_set_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'end_set_spinbox_3')
        self.UIE_mgw_dm_step_set_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'step_set_spinbox_3')
        self.UIE_mgw_dm_scan_repeats_qdsb: QDoubleSpinBox = self.findChild(
            QDoubleSpinBox, 'scan_repeats_4')
        self.UIE_mgw_dm_begin_scan_qpb: QPushButton = self.findChild(
            QPushButton, 'begin_scan_button_4')
        self.UIE_mgw_dm_end_scan_qpb: QPushButton = self.findChild(
            QPushButton, 'stop_scan_button_4')

        # Set the combo boxes to display the correct axes.
        self.UIE_mgw_main_drive_axis_qcb.setCurrentIndex(self.main_axis_index)
        self.UIE_mgw_filter_wheel_axis_qcb.setCurrentIndex(
            self.filter_axis_index)
        self.UIE_mgw_sample_rotation_axis_qcb.setCurrentIndex(
            self.rsamp_axis_index)
        self.UIE_mgw_sample_angle_axis_qcb.setCurrentIndex(
            self.asamp_axis_index)
        self.UIE_mgw_sample_translation_axis_qcb.setCurrentIndex(
            self.tsamp_axis_index)
        self.UIE_mgw_detector_rotation_axis_qcb.setCurrentIndex(
            self.detector_axis_index)

        # Update the actual axes pointers.

        self.mgw_axis_change_main()
        self.mgw_axis_change_filter()
        self.mgw_axis_change_rsamp()
        self.mgw_axis_change_asamp()
        self.mgw_axis_change_tsamp()
        self.mgw_axis_change_detector()

        self.motion_controllers.main_drive_axis = self.mtn_ctrls[1]

        self.homing_started = False
        if not dummy:
            self.homing_started = True
            self.scan_status_update("HOMING")
        self.current_position = -1900

        # # #

        self.UIE_mgw_graph_qtw: QTabWidget = self.findChild(
            QTabWidget, "graph_tabs")

        # Setup the results graph.
        self.UIE_mgw_plot_result_frame_qw: QWidget = self.findChild(
            QWidget, "data_graph_result")
        graph_result = MplCanvas(self, width=5, height=4, dpi=100)
        graph_result.clear_plot_fcn(-1)
        graph_result.set_table_clear_cb(table.plotsClearedCb)
        toolbar = graph_result.get_toolbar()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(graph_result)
        self.UIE_mgw_graph_qtw.widget(0).findChildren(
            QGraphicsView)[0].setLayout(layout)
        self.graph_result = graph_result

        # # #
        # Setup other tabs.

        self.UIEL_mgw_plot_frames = []
        self.UIE_mgw_plot_frame_qw: QWidget = self.findChild(
            QWidget, "data_graph")

        # Setup the multiple tabbed graphs.
        self.graph_list = []
        self.UIEL_mgw_graph_tabs = []  # List of tabs.
        for i in range(self.num_detectors):
            if i > 0:
                self.UIE_mgw_graph_qtw.addTab(QWidget(), 'Detector %d' % (i+1))
                primary_layout = QVBoxLayout()
                primary_layout.addWidget(QGraphicsView())
                self.UIE_mgw_graph_qtw.widget(i+1).setLayout(primary_layout)

            log.info(
                f'Creating graph for detector {i}: {self.detectors[i].model}.')
            if self.detectors[i].model == mw.Detector.SupportedDevices[0]:
                log.info(
                    f'Creating graph canvas for detector {i}: {self.detectors[i].model}.')
                plotCanvas = MplCanvas(
                    self, width=5, height=4, dpi=100, ylabel='Photocurrent (pA)')
            elif self.detectors[i].model == mw.Detector.SupportedDevices[1] or self.detectors[i].model == mw.Detector.SupportedDevices[2]:
                log.info(
                    f'Creating graph canvas for detector {i}: {self.detectors[i].model}.')
                plotCanvas = MplCanvas(
                    self, width=5, height=4, dpi=100, ylabel='Amplitude (V)')
            else:
                log.info(
                    f'Creating graph canvas for detector {i}: {self.detectors[i].model}.')
                plotCanvas = MplCanvas(self, width=5, height=4, dpi=100)

            plotCanvas.clear_plot_fcn(i)

            for table in self.table_list:
                plotCanvas.set_table_clear_cb(table.plotsClearedCb)

            toolbar = plotCanvas.get_toolbar()
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(toolbar)
            layout.addWidget(plotCanvas)
            # self.UIE_mgw_graph_qtw.widget(i+1).
            self.UIEL_mgw_graph_tabs.append(self.UIE_mgw_graph_qtw.widget(i+1))
            # Get the frame within the tab and set its layout

            log.debug('QGraphicsView:', self.UIE_mgw_graph_qtw.widget(
                i+1).findChildren(QGraphicsView))
            
            log.debug('QWidget:', self.UIE_mgw_graph_qtw.widget(
                i+1).findChildren(QWidget))

            self.UIE_mgw_graph_qtw.widget(
                i+1).findChildren(QGraphicsView)[0].setLayout(layout)
            self.graph_list.append(plotCanvas)

        # Hmm, maybe make a different button for each graph?
        self.UIE_mgw_plot_clear_plots_qpb.clicked.connect(
            self.clear_all_graphs)

        # # #

        # Set the initial value of the Manual Control 'Position:' spin box.
        self.UIE_mgw_pos_qdsb.setValue(0)

        # Signal-to-slot connections.
        self.UIE_mgw_save_config_qpb.clicked.connect(
            self.show_window_machine_config)
        self.UIE_mgw_scan_qpb.clicked.connect(self.scan_button_pressed)
        self.UIE_mgw_stop_scan_qpb.clicked.connect(
            self.stop_master_button_pressed)

        self.UIE_mgw_move_to_position_qpb.clicked.connect(
            self.move_to_position_button_pressed)
        self.UIE_mgw_start_qdsb.valueChanged.connect(self.start_changed)
        self.UIE_mgw_stop_qdsb.valueChanged.connect(self.stop_changed)
        self.UIE_mgw_step_qdsb.valueChanged.connect(self.step_changed)
        self.UIE_mgw_pos_qdsb.valueChanged.connect(self.manual_pos_changed)

        self.UIE_mgw_machine_conf_qa.triggered.connect(
            self.show_window_machine_config)
        self.UIE_mgw_invert_mes_qa.toggled.connect(self.invert_mes_toggled)
        self.UIE_mgw_autosave_data_qa.toggled.connect(
            self.autosave_data_toggled)
        self.UIE_mgw_autosave_dir_qa.triggered.connect(
            self.autosave_dir_triggered)

        self.UIE_mgw_pop_out_table_qa.toggled.connect(
            self.pop_out_table_toggled)
        self.UIE_mgw_pop_out_plot_qa.toggled.connect(self.pop_out_plot_toggled)
        self.UIE_mgw_about_licensing_qa.triggered.connect(
            self.open_licensing_hyperlink)
        self.UIE_mgw_about_manual_qa.triggered.connect(
            self.open_manual_hyperlink)
        self.UIE_mgw_about_source_qa.triggered.connect(
            self.open_source_hyperlink)

        self.UIE_mgw_home_qpb.clicked.connect(self.manual_home)

        self.UIE_mgw_home_all_axes_qpb.clicked.connect(self.home_all)

        # Other stuff.
        self.scan = scan.Scan(weakref.proxy(self))

        log.debug('UpdatePositionDisplays: Thread start() called.')
        self.update_position_displays_thread.start()

        # Set up the status bar.
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.UIE_mgw_copyright_ql: QLabel = QLabel()
        self.UIE_mgw_copyright_ql.setText('Copyright (c) Mit Bailey 2024')
        self.statusBar.addPermanentWidget(self.UIE_mgw_copyright_ql)

        self.manual_position = (self.UIE_mgw_pos_qdsb.value())
        self.startpos = (self.UIE_mgw_start_qdsb.value())
        self.stoppos = (self.UIE_mgw_stop_qdsb.value())

        self.cw_rules = []  # List to hold the actual rules.
        self.UIEL_mgw_fw_rules_qvbl = []
        self.UIEL_mgw_fw_rules_set_qdsb = []
        self.UIEL_mgw_fw_rules_step_qsb = []
        self.UIEL_mgw_fw_rules_remove_qpb = []
        self.UIEL_mgw_fw_rules_enact_qpb = []
        self.UIE_mgw_fw_rules_qsa: QVBoxLayout = self.findChild(
            QVBoxLayout, 'scroll_area_layout')
        self.UIEL_mgw_fw_misc_tuples_ql = []
        self.new_filter_wheel_rule()

        # Sample Movement UI

        self.UIE_mgw_sm_rhome_qpb.clicked.connect(self.manual_home_smr)
        self.UIE_mgw_sm_thome_qpb.clicked.connect(self.manual_home_smt)

        self.UIE_mgw_sm_rmove_qpb.clicked.connect(
            self.move_to_position_button_pressed_sr)
        self.UIE_mgw_sm_tmove_qpb.clicked.connect(
            self.move_to_position_button_pressed_st)

        self.UIE_mgw_sm_amove_qpb.clicked.connect(
            self.move_to_position_button_pressed_sa)
        self.UIE_mgw_sm_ahome_qpb.clicked.connect(self.manual_home_sma)

        # Detector Movement UI

        self.UIE_mgw_dm_rhome_qpb.clicked.connect(self.manual_home_dmr)

        self.UIE_mgw_dm_rmove_qpb.clicked.connect(
            self.move_to_position_button_pressed_dr)

        if self.mes_sign == -1:
            self.UIE_mgw_invert_mes_qa.setChecked(True)
        else:
            self.UIE_mgw_invert_mes_qa.setChecked(False)

        if self.autosave_data_bool:
            self.UIE_mgw_autosave_data_qa.setChecked(True)
        else:
            self.UIE_mgw_autosave_data_qa.setChecked(False)

        self.update_movement_limits_gui()

        self.table_result.updatePlots(0)
        for table in self.table_list:
            table.updatePlots(0)

        self.UIE_mgw_mda_qw: QWidget = self.findChild(
            QWidget, 'main_drive_area')
        self.UIE_mgw_mda_collapse_qpb: QPushButton = self.findChild(
            QPushButton, 'main_drive_area_collap')
        self.mda_collapsed = False
        self.UIE_mgw_mda_collapse_qpb.clicked.connect(self.collapse_mda)

        self.UIE_mgw_fwa_qw: QWidget = self.findChild(
            QWidget, 'filter_wheel_area')
        self.UIE_mgw_fwa_collapse_qpb: QPushButton = self.findChild(
            QPushButton, 'filter_wheel_area_collap')
        self.fwa_collapsed = False
        self.UIE_mgw_fwa_collapse_qpb.clicked.connect(self.collapse_fwa)

        self.UIE_mgw_sa_qw: QWidget = self.findChild(QWidget, 'sample_area')
        self.UIE_mgw_sa_collapse_qpb: QPushButton = self.findChild(
            QPushButton, 'sample_area_collap')
        self.sa_collapsed = False
        self.UIE_mgw_sa_collapse_qpb.clicked.connect(self.collapse_sa)

        self.UIE_mgw_da_qw: QWidget = self.findChild(QWidget, 'detector_area')
        self.UIE_mgw_da_collapse_qpb: QPushButton = self.findChild(
            QPushButton, 'detector_area_collap')
        self.da_collapsed = False
        self.UIE_mgw_da_collapse_qpb.clicked.connect(self.collapse_da)

        self.collapse_fwa()
        self.collapse_sa()
        self.collapse_da()

        # TEMPORARY DISABLING OF UI ELEMENT UNTIL FUTURE VERSION IMPLEMENTATION.
        if not SHOW_FILTER_WHEEL:
            self.findChild(QLabel, 'label_9').setEnabled(False)
            self.UIE_mgw_filter_wheel_axis_qcb.setMaxCount(0)
            self.UIE_mgw_fwa_collapse_qpb.setText('X')
            self.UIE_mgw_fwa_collapse_qpb.setEnabled(False)
        if not SHOW_SAMPLE_MOVEMENT:
            self.findChild(QLabel, 'label_10').setEnabled(False)
            self.UIE_mgw_sample_rotation_axis_qcb.setMaxCount(0)
            self.UIE_mgw_sample_angle_axis_qcb.setMaxCount(0)
            self.UIE_mgw_sample_translation_axis_qcb.setMaxCount(0)
            self.UIE_mgw_sa_collapse_qpb.setText('X')
            self.UIE_mgw_sa_collapse_qpb.setEnabled(False)
        if not SHOW_DETECTOR_ROTATION:
            self.findChild(QLabel, 'label_11').setEnabled(False)
            self.UIE_mgw_detector_rotation_axis_qcb.setMaxCount(0)
            self.UIE_mgw_da_collapse_qpb.setText('X')
            self.UIE_mgw_da_collapse_qpb.setEnabled(False)

        self.UIE_mgw_sm_scan_type_qcb.addItem('Rotation')
        self.UIE_mgw_sm_scan_type_qcb.addItem('Translation')
        self.UIE_mgw_sm_scan_type_qcb.addItem('Rot-Det Theta2Theta')
        self.UIE_mgw_sm_begin_scan_qpb.clicked.connect(
            self.scan_sm_button_pressed)
        self.UIE_mgw_sm_end_scan_qpb.clicked.connect(
            self.stop_master_button_pressed)

        self.UIE_mgw_dm_begin_scan_qpb.clicked.connect(
            self.scan_dm_button_pressed)
        self.UIE_mgw_dm_end_scan_qpb.clicked.connect(
            self.stop_master_button_pressed)

        movement_sensitive_list = []
        movement_sensitive_list.append(self.UIE_mgw_scan_qpb)
        movement_sensitive_list.append(self.UIE_mgw_save_data_qckbx)
        movement_sensitive_list.append(self.UIE_mgw_dir_box_qle)
        movement_sensitive_list.append(self.UIE_mgw_start_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_stop_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_step_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_save_config_qpb)
        movement_sensitive_list.append(self.UIE_mgw_pos_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_move_to_position_qpb)
        movement_sensitive_list.append(self.UIE_mgw_machine_conf_qa)
        movement_sensitive_list.append(self.UIE_mgw_import_qa)
        movement_sensitive_list.append(self.UIE_mgw_export_qa)
        movement_sensitive_list.append(self.UIE_mgw_save_data_qpb)
        movement_sensitive_list.append(self.UIE_mgw_delete_data_qpb)
        movement_sensitive_list.append(self.UIE_mgw_main_drive_axis_qcb)
        movement_sensitive_list.append(self.UIE_mgw_filter_wheel_axis_qcb)
        movement_sensitive_list.append(self.UIE_mgw_sample_rotation_axis_qcb)
        movement_sensitive_list.append(self.UIE_mgw_sample_angle_axis_qcb)
        movement_sensitive_list.append(
            self.UIE_mgw_sample_translation_axis_qcb)
        movement_sensitive_list.append(self.UIE_mgw_detector_rotation_axis_qcb)
        movement_sensitive_list.append(self.UIE_mgw_fw_mancon_position_set_qsb)
        movement_sensitive_list.append(self.UIE_mgw_fw_mancon_move_pos_qpb)
        movement_sensitive_list.append(self.UIE_mgw_fw_mancon_home_qpb)
        movement_sensitive_list.append(self.UIE_mgw_fw_add_rule_qpb)
        movement_sensitive_list.append(self.UIE_mgw_sm_rpos_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_sm_tpos_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_sm_rhome_qpb)
        movement_sensitive_list.append(self.UIE_mgw_sm_thome_qpb)
        movement_sensitive_list.append(self.UIE_mgw_sm_rmove_qpb)
        movement_sensitive_list.append(self.UIE_mgw_sm_tmove_qpb)
        movement_sensitive_list.append(self.UIE_mgw_dm_rpos_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_dm_rhome_qpb)
        movement_sensitive_list.append(self.UIE_mgw_dm_rmove_qpb)
        movement_sensitive_list.append(self.UIE_mgw_sm_scan_type_qcb)
        movement_sensitive_list.append(self.UIE_mgw_sm_start_set_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_sm_end_set_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_sm_step_set_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_sm_scan_repeats_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_sm_begin_scan_qpb)
        movement_sensitive_list.append(self.UIE_mgw_sm_begin_scan_qpb)
        movement_sensitive_list.append(self.UIE_mgw_dm_start_set_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_dm_end_set_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_dm_step_set_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_dm_scan_repeats_qdsb)
        movement_sensitive_list.append(self.UIE_mgw_dm_begin_scan_qpb)
        movement_sensitive_list.append(self.UIE_mgw_sm_amove_qpb)
        movement_sensitive_list.append(self.UIE_mgw_sm_ahome_qpb)

        self.movement_sensitive_metalist = []
        self.movement_sensitive_metalist.append(movement_sensitive_list)
        self.movement_sensitive_metalist.append(
            self.UIEL_mgw_fw_rules_set_qdsb)
        self.movement_sensitive_metalist.append(
            self.UIEL_mgw_fw_rules_step_qsb)
        self.movement_sensitive_metalist.append(
            self.UIEL_mgw_fw_rules_remove_qpb)
        self.movement_sensitive_metalist.append(
            self.UIEL_mgw_fw_rules_enact_qpb)

        self.UIE_mcw_fw_offset_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_sr_offset_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_sa_offset_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_st_offset_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_dr_offset_qdsb: QDoubleSpinBox = None

        # This is where we disable the scroll function for all spin and combo boxes, because its dumb.
        uiel = self.findChildren(QDoubleSpinBox)
        uiel += self.findChildren(QSpinBox)
        uiel += self.findChildren(QComboBox)
        for uie in uiel:
            uie.installEventFilter(self)

        # Setup the steps_per_nm of the main axis.
        self.UIE_mcw_steps_per_nm_ql = None
        self.calculate_and_apply_steps_per_nm()

        self.load_config(appDir, False)

        self.main_gui_booted = True
        self.show()
        self.dmw.close()

    def clear_all_graphs(self):
        self.table_result.plotsClearedCb()
        self.table_result.updatePlots(-1)

        for i, table in enumerate(self.table_list):
            table.plotsClearedCb()
            table.updatePlots(i)

    def config_import(self):
        loadFileName, _ = QFileDialog.getOpenFileName(
            self, "Load CSV", directory=self.selected_config_save_path)
        fileInfo = QFileInfo(loadFileName)

        if fileInfo.absoluteFilePath() == '':
            log.info('File name empty. User likely exited dialog prematurely.')
            return

        try:
            self.load_config(fileInfo.absoluteFilePath(), True)
        except Exception as e:
            self.QMessageBoxWarning('Import Error', str(e))

    def config_export(self):

        savFileName, _ = QFileDialog.getSaveFileName(
            self, "Save CSV", directory=self.selected_config_save_path, filter='*.csv')
        fileInfo = QFileInfo(savFileName)
        self.selected_config_save_path = savFileName

        if fileInfo.absoluteFilePath() == '':
            log.info('File name empty. User probably exited dialog prematurely.')
            return

        try:
            self.save_config(fileInfo.absoluteFilePath())
        except Exception as e:
            self.QMessageBoxWarning('Import Error', str(e))

    # Triggered from QAction 'Save Current Config'.
    def config_save(self):
        answer = self.QMessageBoxQuestion(
            'Save Configuration', 'Save current configuration? This will override the configuration saved from the previous exit.')

        if answer == QMessageBox.Yes:
            self.save_config(appDir + '/config.ini')

    def save_config(self, path: str):
        md_sp = 0.0
        fw_sp = 0.0
        sr_sp = 0.0
        sa_sp = 0.0
        st_sp = 0.0
        dr_sp = 0.0

        if self.motion_controllers.main_drive_axis is not None:
            md_sp = self.motion_controllers.main_drive_axis.get_steps_per_value()
        if self.motion_controllers.filter_wheel_axis is not None:
            fw_sp = self.motion_controllers.filter_wheel_axis.get_steps_per_value()
        if self.motion_controllers.sample_rotation_axis is not None:
            sr_sp = self.motion_controllers.sample_rotation_axis.get_steps_per_value()
        if self.motion_controllers.sample_angle_axis is not None:
            sa_sp = self.motion_controllers.sample_angle_axis.get_steps_per_value()
        if self.motion_controllers.sample_translation_axis is not None:
            st_sp = self.motion_controllers.sample_translation_axis.get_steps_per_value()
        if self.motion_controllers.detector_rotation_axis is not None:
            dr_sp = self.motion_controllers.detector_rotation_axis.get_steps_per_value()

        log.debug('Saving the following config settings...', path, self.mes_sign, self.autosave_data_bool, self.data_save_directory, self.model_index, self.grating_density, self.zero_ofst, self.max_pos, self.min_pos, self.main_axis_index, self.filter_axis_index, self.rsamp_axis_index, self.asamp_axis_index, self.tsamp_axis_index, self.detector_axis_index, self.main_axis_dev_name, self.filter_axis_dev_name, self.rsamp_axis_dev_name,
                  self.asamp_axis_dev_name, self.tsamp_axis_dev_name, self.detector_axis_dev_name, len(self.mtn_ctrls), self.fw_max_pos, self.fw_min_pos, self.smr_max_pos, self.smr_min_pos, self.sma_max_pos, self.sma_min_pos, self.smt_max_pos, self.smt_min_pos, self.dr_max_pos, self.dr_min_pos, self.fw_offset, self.st_offset, self.sr_offset, self.sa_offset, self.dr_offset, md_sp, fw_sp, sr_sp, sa_sp, st_sp, dr_sp)

        save_config(path, self.mes_sign, self.autosave_data_bool, self.data_save_directory, self.model_index, self.grating_density, self.zero_ofst, self.max_pos, self.min_pos, self.main_axis_index, self.filter_axis_index, self.rsamp_axis_index, self.asamp_axis_index, self.tsamp_axis_index, self.detector_axis_index, self.main_axis_dev_name, self.filter_axis_dev_name, self.rsamp_axis_dev_name,
                    self.asamp_axis_dev_name, self.tsamp_axis_dev_name, self.detector_axis_dev_name, len(self.mtn_ctrls), self.fw_max_pos, self.fw_min_pos, self.smr_max_pos, self.smr_min_pos, self.sma_max_pos, self.sma_min_pos, self.smt_max_pos, self.smt_min_pos, self.dr_max_pos, self.dr_min_pos, self.fw_offset, self.st_offset, self.sr_offset, self.sa_offset, self.dr_offset, md_sp, fw_sp, sr_sp, sa_sp, st_sp, dr_sp)

    def load_config(self, path: str, is_import: bool):
        # Replaces default grating equation values with the values found in the config.ini file.
        try:
            load_dict = load_config(path, is_import)
        except Exception as e:
            log.error(
                "The following exception occurred while attempting to load configuration file: %s" % (e))
            if not is_import:
                log.error("Attempting config file default reset.")
                try:
                    reset_config(path)
                    load_dict = load_config(path, is_import)
                except Exception as e2:
                    log.fatal(
                        "Configuration file recovery failed (exception: %s). Unable to load configuration file. Exiting." % (e2))
                    sys.exit(43)
            else:
                self.QMessageBoxCritical(
                    'Config Import Failure', 'Configuration could not be imported.')

        self.mes_sign = load_dict['measurementSign']

        self.autosave_data_bool = load_dict['autosaveData']
        self.data_save_directory = load_dict['dataSaveDirectory']
        self.model_index = load_dict["modelIndex"]
        self.grating_density = load_dict["gratingDensity"]
        self.zero_ofst = load_dict["zeroOffset"]
        self.max_pos = load_dict["maxPosition"]
        self.min_pos = load_dict["minPosition"]

        self.main_axis_index = load_dict['mainAxisIndex']
        log.info('Loaded main_axis_index value of:', self.main_axis_index)
        self.filter_axis_index = load_dict['filterAxisIndex']
        self.rsamp_axis_index = load_dict['rsampAxisIndex']
        self.asamp_axis_index = load_dict['asampAxisIndex']
        self.tsamp_axis_index = load_dict['tsampAxisIndex']
        self.detector_axis_index = load_dict['detectorAxisIndex']

        self.main_axis_dev_name = load_dict['mainAxisName']
        self.filter_axis_dev_name = load_dict['filterAxisName']
        self.rsamp_axis_dev_name = load_dict['rsampAxisName']
        self.asamp_axis_dev_name = load_dict['asampAxisName']
        self.tsamp_axis_dev_name = load_dict['tsampAxisName']
        self.detector_axis_dev_name = load_dict['detectorAxisName']
        self.num_axes_at_time_of_save = load_dict['numAxes']

        self.fw_max_pos = load_dict['fwMax']
        self.fw_min_pos = load_dict['fwMin']
        self.smr_max_pos = load_dict['smrMax']
        self.smr_min_pos = load_dict['smrMin']
        self.sma_max_pos = load_dict['smaMax']
        self.sma_min_pos = load_dict['smaMin']
        self.smt_max_pos = load_dict['smtMax']
        self.smt_min_pos = load_dict['smtMin']
        self.dr_max_pos = load_dict['drMax']
        self.dr_min_pos = load_dict['drMin']

        self.fw_offset = load_dict['fwOffset']
        self.st_offset = load_dict['stOffset']
        self.sr_offset = load_dict['srOffset']
        self.sa_offset = load_dict['saOffset']
        self.dr_offset = load_dict['drOffset']
        log.debug('load_dict[drOffset]:', load_dict['drOffset'])
        log.debug('dr_offset:', self.dr_offset)

        if self.motion_controllers.main_drive_axis is not None:
            self.motion_controllers.main_drive_axis.set_offset(self.zero_ofst)
        else:
            log.info(
                f'Main Drive Axis is None; cannot set offset to {self.zero_ofst}.')
        if self.motion_controllers.filter_wheel_axis is not None:
            self.motion_controllers.filter_wheel_axis.set_offset(
                self.fw_offset)
        else:
            log.info(
                f'Filter Wheel Axis is None; cannot set offset to {self.fw_offset}.')
        if self.motion_controllers.sample_translation_axis is not None:
            self.motion_controllers.sample_translation_axis.set_offset(
                self.st_offset)
        else:
            log.info(
                f'Sample Translation Axis is None; cannot set offset to {self.st_offset}.')
        if self.motion_controllers.sample_rotation_axis is not None:
            self.motion_controllers.sample_rotation_axis.set_offset(
                self.sr_offset)
        else:
            log.info(
                f'Sample Rotation Axis is None; cannot set offset to {self.sr_offset}.')
        if self.motion_controllers.sample_angle_axis is not None:
            self.motion_controllers.sample_angle_axis.set_offset(
                self.sa_offset)
        else:
            log.info(
                f'Sample Angle Axis is None; cannot set offset to {self.sa_offset}.')
        if self.motion_controllers.detector_rotation_axis is not None:
            self.motion_controllers.detector_rotation_axis.set_offset(
                self.dr_offset)
        else:
            log.info(
                f'Detector Rotation Axis is None; cannot set offset to {self.dr_offset}.')

        self.md_sp = load_dict['mdSp']
        self.fw_sp = load_dict['fwSp']
        self.sr_sp = load_dict['srSp']
        self.sa_sp = load_dict['saSp']
        self.st_sp = load_dict['stSp']
        self.dr_sp = load_dict['drSp']

        if self.motion_controllers.main_drive_axis is not None:
            self.motion_controllers.main_drive_axis.set_steps_per_value(
                self.md_sp)
        else:
            log.info(
                f'Main Drive Axis is None; cannot set steps per value to {self.md_sp}.')
        if self.motion_controllers.filter_wheel_axis is not None:
            self.motion_controllers.filter_wheel_axis.set_steps_per_value(
                self.fw_sp)
        else:
            log.info(
                f'Filter Wheel Axis is None; cannot set steps per value to {self.fw_sp}.')
        if self.motion_controllers.sample_rotation_axis is not None:
            self.motion_controllers.sample_rotation_axis.set_steps_per_value(
                self.sr_sp)
        else:
            log.info(
                f'Sample Rotation Axis is None; cannot set steps per value to {self.sr_sp}.')
        if self.motion_controllers.sample_angle_axis is not None:
            self.motion_controllers.sample_angle_axis.set_steps_per_value(
                self.sa_sp)
        else:
            log.info(
                f'Sample Angle Axis is None; cannot set steps per value to {self.sa_sp}.')
        if self.motion_controllers.sample_translation_axis is not None:
            self.motion_controllers.sample_translation_axis.set_steps_per_value(
                self.st_sp)
        else:
            log.info(
                f'Sample Translation Axis is None; cannot set steps per value to {self.st_sp}.')
        if self.motion_controllers.detector_rotation_axis is not None:
            self.motion_controllers.detector_rotation_axis.set_steps_per_value(
                self.dr_sp)
        else:
            log.info(
                f'Detector Rotation Axis is None; cannot set steps per value to {self.dr_sp}.')

    def save_config_devman(self, path: str):
        pass
        detector_spinbox_indices = []
        detector_model_spinbox_indices = []
        motion_controller_spinbox_indices = []
        motion_controller_model_spinbox_indices = []

        for i in range(self.num_detectors):
            detector_spinbox_indices.append(
                self.UIEL_dmw_detector_qcb[i].currentIndex())
            detector_model_spinbox_indices.append(
                self.UIEL_dmw_detector_model_qcb[i].currentIndex())

        for i in range(self.num_motion_controllers):
            motion_controller_spinbox_indices.append(
                self.UIEL_dmw_mtn_ctrl_qcb[i].currentIndex())
            motion_controller_model_spinbox_indices.append(
                self.UIEL_dmw_mtn_ctrl_model_qcb[i].currentIndex())

        save_config_devman(path, self.dev_list_hash, self.num_detectors, self.num_motion_controllers, detector_spinbox_indices,
                           motion_controller_spinbox_indices, detector_model_spinbox_indices, motion_controller_model_spinbox_indices)

    def load_config_devman(self, path: str):
        pass
        devman_config = load_config_devman(path)

        if devman_config is None:
            log.error('Failed to load previous device manager layout.')
            return None

        if devman_config['devListHash'] != self.dev_list_hash:
            log.info(
                'Cannot load previous device manager layout since the device configuration has changed.')
            return None

        self.num_detectors = devman_config['numDetectors']
        self.num_motion_controllers = devman_config['numMotionControllers']

        self.UIE_dmw_num_detectors_qsb.setValue(self.num_detectors)
        self.update_num_detectors_ui(force=True)

        self.UIE_dmw_num_motion_controllers_qsb.setValue(
            self.num_motion_controllers)
        self.update_num_motion_controllers_ui(force=True)

        for i in range(self.num_detectors):
            self.UIEL_dmw_detector_qcb[i].setCurrentIndex(
                devman_config['detectorIndices'][i])
            self.UIEL_dmw_detector_model_qcb[i].setCurrentIndex(
                devman_config['detectorModelIndices'][i])

        for i in range(self.num_motion_controllers):
            self.UIEL_dmw_mtn_ctrl_qcb[i].setCurrentIndex(
                devman_config['controllerIndices'][i])
            self.UIEL_dmw_mtn_ctrl_model_qcb[i].setCurrentIndex(
                devman_config['controllerModelIndices'][i])

    def load_queue_file(self):
        queueFileName, _ = QFileDialog.getOpenFileName(
            self, "Open Queue File", directory='./queues', filter='*.txt')

        if queueFileName == '':
            log.debug('No file selected.')
            self.QMessageBoxInformation(
                'No File Selected', 'No queue file was selected.')
            return

        with open(queueFileName, 'r') as file:
            lines = file.readlines()

        # Remove newline characters and create a list
        array = [line.strip() for line in lines]

        log.debug(array)
        self.scan_queue = array

    def begin_queue(self):
        if self.scan_queue is None:
            log.warn('Cannot Execute Scan Queue: No queue file loaded.')
            self.QMessageBoxWarning(
                'Cannot Execute Scan Queue', 'No queue file loaded.')
            return

        log.info('Queue Executor Thread starting.')
        self.queue_executor_thread.set_queue(self.scan_queue)
        self.queue_executor_thread.start()

    def collapse_ref(self):
        self.ref_collapsed = not self.ref_collapsed
        self.UIE_mgw_ref_area_qw.setVisible(not self.ref_collapsed)
        if self.ref_collapsed:
            self.UIE_mgw_ref_collap_qpb.setText('∑ ⮜')
        else:
            self.UIE_mgw_ref_collap_qpb.setText('∑ ⮟')

    def collapse_mda(self):
        self.mda_collapsed = not self.mda_collapsed
        self.UIE_mgw_mda_qw.setVisible(not self.mda_collapsed)
        if self.mda_collapsed:
            self.UIE_mgw_mda_collapse_qpb.setText('⮜')
        else:
            self.UIE_mgw_mda_collapse_qpb.setText('⮟')

    def collapse_fwa(self):
        self.fwa_collapsed = not self.fwa_collapsed
        self.UIE_mgw_fwa_qw.setVisible(not self.fwa_collapsed)
        if self.fwa_collapsed:
            self.UIE_mgw_fwa_collapse_qpb.setText('⮜')
        else:
            self.UIE_mgw_fwa_collapse_qpb.setText('⮟')

    def collapse_sa(self):
        self.sa_collapsed = not self.sa_collapsed
        self.UIE_mgw_sa_qw.setVisible(not self.sa_collapsed)
        if self.sa_collapsed:
            self.UIE_mgw_sa_collapse_qpb.setText('⮜')
        else:
            self.UIE_mgw_sa_collapse_qpb.setText('⮟')

    def collapse_da(self):
        self.da_collapsed = not self.da_collapsed
        self.UIE_mgw_da_qw.setVisible(not self.da_collapsed)
        if self.da_collapsed:
            self.UIE_mgw_da_collapse_qpb.setText('⮜')
        else:
            self.UIE_mgw_da_collapse_qpb.setText('⮟')

    def new_filter_wheel_rule(self):
        geq_label: QLabel = QLabel('≥')
        geq_label.setMaximumWidth(13)
        geq_label.setMaximumHeight(29)
        font = QFont('Segoe UI', 14)
        font.setBold(False)
        geq_label.setFont(font)

        goto_label: QLabel = QLabel('nm, go to step')
        goto_label.setMaximumWidth(99)
        goto_label.setMaximumHeight(29)
        font = QFont('Segoe UI', 12)
        font.setBold(False)
        goto_label.setFont(font)

        enact_button: QPushButton = QPushButton('ENACT')
        enact_button.setMaximumWidth(75)
        enact_button.setMaximumHeight(29)
        enact_button.clicked.connect(self.enact_filter_wheel_rule)
        self.UIEL_mgw_fw_rules_enact_qpb.append(enact_button)

        remove_button: QPushButton = QPushButton('-')
        remove_button.setMaximumWidth(29)
        remove_button.setMaximumHeight(29)
        self.UIEL_mgw_fw_rules_remove_qpb.append(remove_button)
        remove_button.clicked.connect(
            partial(self.del_filter_wheel_rule, self.UIEL_mgw_fw_rules_enact_qpb[-1]))
        log.info('Rule added at index:', len(
            self.UIEL_mgw_fw_rules_remove_qpb) - 1)

        rule_set_spinbox: QDoubleSpinBox = QDoubleSpinBox()
        rule_set_spinbox.setRange(0, 9999)
        rule_set_spinbox.setDecimals(2)
        rule_set_spinbox.setMaximumWidth(89)
        rule_set_spinbox.setMaximumHeight(27)
        self.UIEL_mgw_fw_rules_set_qdsb.append(rule_set_spinbox)

        rule_step_spinbox: QSpinBox = QSpinBox()
        rule_step_spinbox.setRange(0, 9999999)
        rule_step_spinbox.setMaximumWidth(84)
        rule_step_spinbox.setMaximumHeight(27)
        self.UIEL_mgw_fw_rules_step_qsb.append(rule_step_spinbox)

        hspacer: QSpacerItem = QSpacerItem(
            20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QHBoxLayout()
        layout.addWidget(geq_label)
        layout.addWidget(rule_set_spinbox)
        layout.addWidget(goto_label)
        layout.addWidget(rule_step_spinbox)
        layout.addWidget(enact_button)
        layout.addItem(hspacer)
        layout.addWidget(remove_button)

        log.debug(layout.spacing())

        self.UIEL_mgw_fw_misc_tuples_ql.append([geq_label, goto_label])

        self.UIEL_mgw_fw_rules_qvbl.append(layout)
        self.UIE_mgw_fw_rules_qsa.addLayout(layout)

    def enact_filter_wheel_rule(self):
        sender = self.sender()
        sidx = -1
        for i in range(len(self.UIEL_mgw_fw_rules_enact_qpb)):
            if self.UIEL_mgw_fw_rules_enact_qpb[i] == sender:
                sidx = i
                break
        if sidx < 0:
            self.QMessageBoxCritical('Error', 'Failed to find sender index.')
            return

        # sender.
        log.debug('SENDER:')
        log.debug(sender)

        dspin = self.UIEL_mgw_fw_rules_set_qdsb[sidx]
        spin = self.UIEL_mgw_fw_rules_step_qsb[sidx]

        log.debug(dspin)
        log.debug(spin)
        log.info('Dspin and spin values are %f and %d.' %
                 (dspin.value(), spin.value()))

    def del_filter_wheel_rule(self, index_finder):
        index = self.UIEL_mgw_fw_rules_enact_qpb.index(index_finder)

        log.info('Rule removed at index:', index)

        self.UIEL_mgw_fw_rules_enact_qpb[index].setParent(None)
        del self.UIEL_mgw_fw_rules_enact_qpb[index]

        log.debug('len', len(self.UIEL_mgw_fw_rules_remove_qpb))
        log.debug('index', index)
        self.UIEL_mgw_fw_rules_remove_qpb[index].setParent(None)
        del self.UIEL_mgw_fw_rules_remove_qpb[index]

        self.UIEL_mgw_fw_rules_set_qdsb[index].setParent(None)
        del self.UIEL_mgw_fw_rules_set_qdsb[index]

        self.UIEL_mgw_fw_rules_step_qsb[index].setParent(None)
        del self.UIEL_mgw_fw_rules_step_qsb[index]

        self.UIEL_mgw_fw_misc_tuples_ql[index][0].setParent(None)
        self.UIEL_mgw_fw_misc_tuples_ql[index][1].setParent(None)
        del self.UIEL_mgw_fw_misc_tuples_ql[index]

        self.UIE_mgw_fw_rules_qsa.removeItem(
            self.UIEL_mgw_fw_rules_qvbl[index])
        del self.UIEL_mgw_fw_rules_qvbl[index]

    def devman_list_devices(self, first_time: bool = False):
        self.dev_list = mw.find_all_ports(ALLOW_DUMMY_MODE)

        dev_list_str = ''
        for dev in self.dev_list:
            dev_list_str += '%s\n' % (dev)

        if (self.dmw_list != "~DEVICE LIST~\n" + dev_list_str):
            for i in range(self.num_detectors):
                self.UIEL_dmw_detector_qcb[i].clear()
                self.UIEL_dmw_detector_qcb[i].addItem('NO DEVICE SELECTED')
                self.UIEL_dmw_detector_qcb[i].setCurrentIndex(0)

                for dev in self.dev_list:
                    self.UIEL_dmw_detector_qcb[i].addItem('%s' % (dev))

            for i in range(self.num_motion_controllers):
                self.UIEL_dmw_mtn_ctrl_qcb[i].clear()
                self.UIEL_dmw_mtn_ctrl_qcb[i].addItem('NO DEVICE SELECTED')
                self.UIEL_dmw_mtn_ctrl_qcb[i].setCurrentIndex(0)

                for dev in self.dev_list:
                    self.UIEL_dmw_mtn_ctrl_qcb[i].addItem('%s' % (dev))

            self.dmw_list = "~DEVICE LIST~\n" + dev_list_str

        if first_time:
            self.dev_list_hash = hashlib.md5(dev_list_str.encode()).hexdigest()
            # Attempt a load of the device manager configuration file.
            self.load_config_devman(appDir + '/devman.ini')

    #     # TODO: Use the ref data

    def _check_table_tab_valid(self):
        if self.UIE_mgw_table_qtw.currentIndex() == 0:
            log.warn('No table selected.')
            self.QMessageBoxWarning(
                'Cannot Set Reference', 'Cannot set reference data from Result tab. Please select a detector table entry.')
            return

        return self.UIE_mgw_table_qtw.currentIndex()

    def set_ref(self):
        """ Sets the data for the reference scan for the basic referencing - pulls from the selected scan.
        """

        log.info('set_ref called.')

        dn = self._check_table_tab_valid()

        table = self.table_list[self.UIE_mgw_table_qtw.currentIndex() - 1]

        # Grab the data from the table.
        data, metadata = table.saveDataCb()

        # Set the reference data.
        self.ref0_data = data

        if metadata is not None:
            log.debug(metadata)
            self.UIE_mgw_setref_qpb.setText(f"D{dn}S{metadata['scan_id']}")
        else:
            self.UIE_mgw_setref_qpb.setText("ERR")

    def set_ref1(self):
        """ Sets the data for the first reference scan (advanced sample scan), pulling from the selected scan.
        """

        dn = self._check_table_tab_valid()

        table = self.table_list[self.UIE_mgw_table_qtw.currentIndex() - 1]

        self.ref1_data, metadata = table.saveDataCb()

        if metadata is not None:
            log.debug(metadata)
            self.UIE_mgw_setr1_qpb.setText(f"D{dn}S{metadata['scan_id']}")
        else:
            self.UIE_mgw_setr1_qpb.setText("ERR")

    def set_ref2(self):
        """ Sets the data for the second reference scan (advanced reference scan), pulling from the selected scan.
        """

        dn = self._check_table_tab_valid()

        table = self.table_list[self.UIE_mgw_table_qtw.currentIndex() - 1]

        self.ref2_data, metadata = table.saveDataCb()

        if metadata is not None:
            log.debug(metadata)
            self.UIE_mgw_setr2_qpb.setText(f"D{dn}S{metadata['scan_id']}")
        else:
            self.UIE_mgw_setr2_qpb.setText("ERR")

    def reset_ref(self):
        """ Resets the reference data to None and disables referencing.
        """

        self.reference_active = False
        self.unregister_ref_data()

        self.UIE_mgw_setref_qpb.setText('Set Reference')
        self.UIE_mgw_setr1_qpb.setText('Set S0')
        self.UIE_mgw_setr2_qpb.setText('Set R0')

        self.UIE_mgw_ref_reset_qpb.setDisabled(True)
        self.UIE_mgw_ref_enact_qpb.setDisabled(False)

    def toggle_ref(self):
        """ Swaps between showing the simple and advanced referencing system.
        """

        if self.UIE_mgw_ref_advanced_qrb.isChecked():
            self.UIE_mgw_simple_opbox_qgb.hide()
            self.UIE_mgw_advanced_opbox_qgb.show()
        else:
            self.UIE_mgw_simple_opbox_qgb.show()
            self.UIE_mgw_advanced_opbox_qgb.hide()

    # The reference value
    # The reference equation is:
    # [%] = (S_i / (R_i * (S_0 / R_0))) * 100.0
    def enact_ref(self):
        """ Sets up the data necessary to perform spectral math.
        """

        advanced_ref = self.UIE_mgw_ref_advanced_qrb.isChecked()
        self.is_advanced_ref = advanced_ref
        self.reference_active = True

        if advanced_ref:
            if self.UIE_mgw_sample_det_qcb.currentIndex() == self.UIE_mgw_ref_det_qcb.currentIndex():
                msg = 'Cannot use the same detector for reference and sample.'
                self.QMessageBoxWarning('Cannot Enact Reference', msg)
                return

            self.sample_det_idx = self.UIE_mgw_sample_det_qcb.currentIndex()
            self.ref_det_idx = self.UIE_mgw_ref_det_qcb.currentIndex()

            if self.ref1_data is None or self.ref2_data is None:
                msg = 'Cannot enact advanced reference without two reference datasets.'
                if self.ref1_data is None:
                    msg += ' Reference 1 dataset is missing.'
                if self.ref2_data is None:
                    msg += ' Reference 2 dataset is missing.'
                self.QMessageBoxWarning('Cannot Enact Reference', msg)
                return

            ref1y = self.ref1_data['y']
            ref2y = self.ref2_data['y']

            res1 = np.divide(ref1y, ref2y)

            # {'id': global_scan_id, 'name': '', 'x': xdata, 'y': ydata, 'plotted': True, 'plot_cb': CustomQCheckBox(global_scan_id)}
            # Fine, I'll do it myself. Manually copy each field since Python sends references everywhere.
            data = {
                'id': self.ref1_data['id'],
                'name': '',
                'x': np.copy(self.ref1_data['x']),
                'y': np.copy(res1),
                'plotted': self.ref1_data['plotted'],
                'plot_cb': self.ref1_data['plot_cb']
            }

            self.register_ref_data(data, advanced_ref)

        else:  # Simple ref
            if self.ref0_data is None:
                self.QMessageBoxWarning(
                    'Cannot Enact Reference', 'Reference data is missing.')
                return

            self.register_ref_data(self.ref0_data)

        self.UIE_mgw_ref_enact_qpb.setDisabled(True)
        self.UIE_mgw_ref_reset_qpb.setDisabled(False)

    # This is the data that will be used to operate on all other scans.
    # The way this will works is as follows:
    #   - All scans will be displayed in the results tab. They will be marked w/ detector and scan #s.
    #   - If ref_data is None, then nothing will be done to the data.
    #   - If ref_data is not None, then the data will be adjusted based on the reference data.
    # THIS IS CALLED FROM WITHIN A DATATABLE OBJECT WHOSE REF CHECKBOX HAS BEEN CLICKED.
    def register_ref_data(self, ref_data, advanced=False):
        self.operated_ref_data = ref_data

        self.table_result.updatePlots(-1)

        # TODO: Figure out how to update the reference / result plot.

    # THIS IS THE LATEST SCAN DATA FROM THE REFERENCE DETECTOR
    def push_latest_ref_data(self, latest_ref_data):
        self.latest_ref_data = latest_ref_data

    # THIS IS CALLED FROM WITHIN A DATATABLE OBJECT WHOSE REF CHECKBOX HAS BEEN CLICKED.
    def unregister_ref_data(self):
        self.operated_ref_data = None
        self.table_result.updatePlots(-1)

    def save_data_cb(self):
        if self.UIE_mgw_table_qtw.currentIndex() == 0:
            table = self.table_result
        else:
            table = self.table_list[self.UIE_mgw_table_qtw.currentIndex() - 1]
        
        (scan_id, det_id) = table.row_to_id_det_map[table.selectedItem]

        return self.save_data_auto(table, det_id, scanIdx=scan_id, button=True)

    def save_data_auto(self, table, which_detector, scanIdx=None, button=False):
        # TODO: Figure out which table were on currently.

        if scanIdx is None:
            log.debug(f'scanIdx is None')
            data, metadata = table.saveDataCb()
        else:
            log.debug(f'scanIdx: {scanIdx}')
            data, metadata = table.save_data_auto(
                scanIdx=scanIdx, which_detector=which_detector)

        log.debug(data, metadata)
        if data is None:
            log.error('Data is None.')
            return
        if metadata is not None:
            try:
                tstamp = metadata['tstamp']
                scan_id = metadata['scan_id']
            except Exception:
                tstamp = dt.datetime.now()
                scan_id = 100
        else:
            log.error('Metadata is None.')
            return

        if self.autosave_next_dir is not None:
            log.debug('Autosave next directory is not None.')
            savFileName = self.autosave_next_dir + \
                '/%s_det-%d_%d.csv' % (tstamp.strftime('%Y%m%d%H%M%S'),
                                       which_detector, scan_id)
            self.autosave_next_dir = None
        elif self.autosave_data_bool:
            log.debug('Autosave data bool is True.')
            savFileName = self.data_save_directory + \
                '/%s_det-%d_%d.csv' % (tstamp.strftime('%Y%m%d%H%M%S'),
                                       which_detector, scan_id)
        elif button is False:
            log.error(
                'save_data_auto was called, but not from a button press, and yet autosave_next_dir and autosave_next_dir are both False...')
        if button:
            log.debug('Save data button was pushed.')
            savFileName, _ = QFileDialog.getSaveFileName(self, "Save CSV", directory=os.path.expanduser(
                '~/Documents') + '/mcpherson_mmc/%s_det-%d_%d.csv' % (tstamp.strftime('%Y%m%d%H%M%S'), which_detector, scan_id), filter='*.csv')
        fileInfo = QFileInfo(savFileName)

        try:
            ofile = open(fileInfo.absoluteFilePath(), 'w', encoding='utf-8')
        except Exception:
            self.QMessageBoxCritical(
                'Error', 'Could not open file %s' % (fileInfo.fileName()))
            return
        ofile.write('# DATA RECORDED IN SOFTWARE VERSION: %sv%s' %
                    (version.__short_name__, version.__version__))
        ofile.write('# %s det#%d\n' %
                    (tstamp.strftime('%Y-%m-%d %H:%M:%S'), which_detector))
        try:
            ofile.write('# Steps/mm: %f\n' % (metadata['steps_per_value']))
        except Exception:
            pass
        try:
            ofile.write('# mm/nm: %e; ' % (metadata['mm_per_nm']))
        except Exception:
            pass
        try:
            ofile.write('lambda_0 (nm): %.4f\n' % (metadata['zero_ofst']))
        except Exception:
            pass
        ofile.write('# Position (nm),Mean Current(A)\n')
        xdata = data['x']
        ydata = data['y']
        for i in range(len(xdata)):
            try:
                ofile.write('%e, %e\n' % (xdata[i], ydata[i]))
            except Exception:
                continue
        ofile.close()

    def delete_data_cb(self):
        # TODO: Move delete button within the tabs and have one per tab.
        for table in self.table_list:
            table.delDataCb()
        return

    def open_manual_hyperlink(self):
        webbrowser.open(
            'https://github.com/mitbailey/MMC/blob/master/documentation/user_manual.pdf')

    def open_source_hyperlink(self):
        webbrowser.open('https://github.com/mitbailey/MMC')

    def open_licensing_hyperlink(self):
        webbrowser.open(
            'https://github.com/mitbailey/MMC/blob/master/README.md#licensing')

    def disable_movement_sensitive_buttons(self, disable: bool):
        for uiel in self.movement_sensitive_metalist:
            for uie in uiel:
                if uie is not None:
                    uie.setDisabled(disable)

        if self.UIE_mgw_move_to_position_qpb is not None:
            self.UIE_mgw_move_to_position_qpb.setDisabled(disable)
        if self.UIE_mgw_scan_qpb is not None:
            self.UIE_mgw_scan_qpb.setDisabled(disable)

        # The stop scan button should always be set based on if a scan is running.
        if self.scanRunning:
            # Always have the Stop Scan button available when a scan is running.
            self.UIE_mgw_stop_scan_qpb.setDisabled(False)
        else:
            self.UIE_mgw_stop_scan_qpb.setDisabled(True)

        if self.UIE_mgw_home_qpb is not None:
            self.UIE_mgw_home_qpb.setDisabled(disable)

    def home_all(self):
        log.info('Homing all axes!')

        if self.motion_controllers.main_drive_axis is not None:
            log.info('Homing main drive axis.')
            self.manual_home()
        if self.motion_controllers.sample_rotation_axis is not None:
            log.info('Homing sample rotation axis.')
            self.manual_home_smr()
        if self.motion_controllers.sample_angle_axis is not None:
            log.info('Homing sample angle axis.')
            self.manual_home_sma()
        if self.motion_controllers.sample_translation_axis is not None:
            log.info('Homing sample translation axis.')
            self.manual_home_smt()
        if self.motion_controllers.detector_rotation_axis is not None:
            log.info('Homing detector rotation axis.')
            self.manual_home_dmr()

    def manual_home(self):
        if self.motion_controllers.main_drive_axis is None:
            log.error('Main drive axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Main drive axis is not set to any motion control channel.')
            return

        self.anim_mgw_mda_load_spinner_start(True)

        log.info('Manual home pressed!')
        self.scan_status_update("HOMING")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        try:
            self.motion_controllers.main_drive_axis.home()
        except Exception as e:
            self.QMessageBoxWarning('Homing Failed', e)
            pass

    def manual_home_smr(self):
        if self.motion_controllers.sample_rotation_axis is None:
            log.error(
                'Sample rotation axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Sample rotation axis is not set to any motion control channel.')
            return

        self.anim_mgw_sra_load_spinner_start(True)

        self.scan_status_update("HOMING SR")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        try:
            self.motion_controllers.sample_rotation_axis.home()
        except Exception as e:
            self.QMessageBoxWarning('Homing Failed', e)

    def manual_home_sma(self):
        if self.motion_controllers.sample_angle_axis is None:
            log.error(
                'Sample angle axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Sample angle axis is not set to any motion control channel.')
            return

        self.anim_mgw_saa_load_spinner_start(True)

        self.scan_status_update("HOMING SA")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        try:
            self.motion_controllers.sample_angle_axis.home()
        except Exception as e:
            self.QMessageBoxWarning('Homing Failed', e)

    def manual_home_smt(self):
        if self.motion_controllers.sample_translation_axis is None:
            log.error(
                'Sample translation axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Sample translation axis is not set to any motion control channel.')
            return

        self.anim_mgw_sta_load_spinner_start(True)

        self.scan_status_update("HOMING ST")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        try:
            self.motion_controllers.sample_translation_axis.home()
        except Exception as e:
            self.QMessageBoxWarning('Homing Failed', e)

    def manual_home_dmr(self):
        if self.motion_controllers.detector_rotation_axis is None:
            log.error(
                'Detector rotation axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Detector rotation axis is not set to any motion control channel.')
            return

        self.anim_mgw_dra_load_spinner_start(True)

        self.scan_status_update("HOMING DR")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        try:
            self.motion_controllers.detector_rotation_axis.home()
        except Exception as e:
            self.QMessageBoxWarning('Homing Failed', e)

    def autosave_dir_triggered(self):
        self.data_save_directory = QFileDialog.getExistingDirectory(
            self, 'Auto logging files location', self.data_save_directory, options=QFileDialog.ShowDirsOnly)

    def invert_mes_toggled(self, state):
        if not self.scanRunning:
            if state:
                self.mes_sign = -1
            else:
                self.mes_sign = 1
            # TODO: Invert the signs of all previously collected data sets.

    def autosave_data_toggled(self, state):
        if not self.scanRunning:
            self.autosave_data_bool = state
        else:
            self.UIE_mgw_autosave_data_qa.setChecked(self.autosave_data_bool)

    def pop_out_table_toggled(self, state):
        self.pop_out_table = state

    def pop_out_plot_toggled(self, state):
        self.pop_out_plot = state

    def update_plots(self, det_idx: int, data: list, is_result: bool = False):
        if self.graph_list is None or len(self.graph_list) == 0:
            return

        if is_result:
            self.graph_result.update_plots(data)
        else:
            self.graph_list[det_idx].update_plots(data)

    def scan_status_update(self, status):
        self.UIE_mgw_scan_status_ql.setText(
            '<html><head/><body><p><span style=" font-weight:600;">%s</span></p></body></html>' % (status))

    def scan_progress(self, curr_percent, secs_remaining):
        """ Updates the progress bar to reflect the current scan progress.
        
        Called from a signal in scan.py. 

        Args:
            curr_percent (_type_): _description_
        """

        self.UIE_mgw_scan_qpbar.setValue(curr_percent)

        # New average = old average * (n-1)/n + new value /n

        MIN_TIME = 10.0

        if secs_remaining < MIN_TIME:
            self.scan_time_left = 0.0
        else:
            n = 10.0
            self.scan_time_left = self.scan_time_left * (n - 1.0) / n + secs_remaining / n

        log.debug('scan_progress:', curr_percent)

    def update_scan_timer_stage1(self):
        try:
            self.scan_remaining_timer.timeout.connect(self.update_scan_timer_stage2)
            self.scan_remaining_timer.start(10)
        except Exception as e:
            log.error(f"Failed to start scan timer: {e}")

    def update_scan_timer_stage2(self):
        try:
            self.scan_time_left -= 0.01

            MIN_TIME = 10.0

            if self.scan_time_left < MIN_TIME:
                self.scan_time_left = 0.0
                self.UIE_mgw_scan_time_ql.setText(f"")
            else:
                self.UIE_mgw_scan_time_ql.setText(f"{self.scan_time_left:.1f} s")
        except Exception as e:
            log.error(f"Failed to update scan timer: {e}")

    def scan_complete(self):
        log.debug('Setting scanRunning to False.')
        self.scanRunning = False

        self.scan_remaining_timer.stop()
        self.UIE_mgw_scan_time_ql.setText(f"")
        
        self.UIE_mgw_scan_qpb.setText('Begin Scan')
        self.UIE_mgw_scan_status_ql.setText(
            '<html><head/><body><p><span style=" font-weight:600;">IDLE</span></p></body></html>')
        self.UIE_mgw_scan_qpbar.reset()

    def scan_data_begin(self, which_detector: int, det_idx: int, scans_global_scan_id: int, metadata: dict):
        self.scan_remaining_timer.stop()

        self.update_scan_timer_stage1()

        if scans_global_scan_id != self.global_scan_id:
            log.error('Global scan ID mismatch %d != %d' %
                      (scans_global_scan_id, self.global_scan_id))

        if self.reference_active and (self.global_scan_id, self.sample_det_idx) not in self.table_result.recordedData:
            self.table_result.insertData(
                self.sample_det_idx, self.global_scan_id, None, None, metadata)

        self.table_list[det_idx].insertData(
            det_idx, self.global_scan_id, None, None, metadata)

    # This function is called via a signal emission from scan.py.
    # The data is actually stored in datatable.py's recordedData.
    def scan_data_update(self, which_detector: int, scan_idx: int, det_idx: int, xdata: float, ydata: float):
        log.debug(f'Data received from detector #{det_idx}: {xdata}; {ydata}')

        # Ok, so we need to perform self.operated_ref_data * Sample/Reference
        # The issue is that we have no way of knowing if the Sample or Reference detection was made first.
        # We want to shove the result into the table_result table.
        # So we want them to both have the same length but also be longer than 0.
        # We actually don't really care whether in this call we are ref or samp det.

        # First, let's just get the raw data put where it needs to go.
        self.table_list[det_idx].insertDataAt(det_idx, scan_idx, xdata, ydata)

        if self.reference_active:
            # Get the corresponding self.operated_ref_data element iff the 'x' matches.
            this_len = len(
                self.table_list[det_idx].recordedData[(scan_idx, det_idx)]['x'])
            this_x = self.table_list[det_idx].recordedData[(
                scan_idx, det_idx)]['x'][this_len - 1]
            operated_ref_x = self.operated_ref_data['x'][this_len - 1]

            if not math.isclose(this_x, operated_ref_x):
                log.error(
                    f"Cannot perform referencing because x-values {this_x} and {operated_ref_x} are not close.")
                return

            operated_ref_y = self.operated_ref_data['y'][this_len - 1]

            if self.is_advanced_ref:
                # Then let's get the lengths of the recorded data.
                samp_len = len(self.table_list[self.sample_det_idx].recordedData[(
                    scan_idx, self.sample_det_idx)]['x'])
                ref_len = len(self.table_list[self.ref_det_idx].recordedData[(
                    scan_idx, self.ref_det_idx)]['x'])

                # ~ Case: Sample First ~
                #
                # S R
                # 0 0 -> Check: fails.
                # Process sample data.
                # 1 0 -> Check: fails.
                # Process ref. data.
                # 1 1 -> Check: passes!
                # Perform ResultTable.push(S/R)
                #
                #
                # ~ Case: Ref. First ~
                #
                # S R
                # 0 0 -> Check: fails.
                # Process ref. data.
                # 0 1 -> Check: fails.
                # Process sample data.
                # 1 1 -> Check: passes!
                # Perform ResultTable.push(S/R)

                if (samp_len == ref_len) and (samp_len > 0):
                    # Get the latest values from the sample and reference scans.
                    numerator = self.table_list[self.sample_det_idx].recordedData[(
                        scan_idx, self.sample_det_idx)]['y'][-1]
                    denominator = self.table_list[self.ref_det_idx].recordedData[(
                        scan_idx, self.ref_det_idx)]['y'][-1]
                    # quotient = numerator/denominator

                    # result = operated_ref_y * quotient

                    result = numerator / (denominator * operated_ref_y)

                    self.table_result.insertDataAt(
                        self.sample_det_idx, scan_idx, xdata, result)

            elif not self.is_advanced_ref:
                if self.UIE_mgw_setop_qcb.currentIndex() == 0:
                    result = ydata * operated_ref_y

                elif self.UIE_mgw_setop_qcb.currentIndex() == 1:
                    result = ydata / operated_ref_y

                elif self.UIE_mgw_setop_qcb.currentIndex() == 2:
                    result = ydata + operated_ref_y

                elif self.UIE_mgw_setop_qcb.currentIndex() == 3:
                    result = ydata - operated_ref_y

                self.table_result.insertDataAt(
                    det_idx, scan_idx, xdata, result)

        # This is where we handle all detectors.
        # self.table_result.insertDataAt(det_idx, scan_idx, xdata, ydata)
        # self.table_list[det_idx].insertDataAt(det_idx, scan_idx, xdata, ydata)
        log.info("Data from detector #%d received." % (det_idx))

    def scan_data_complete(self, which_detector: int, scan_idx: int, scan_class: str):
        # Which detector is just the index of the active detector spinbox when the scan began.

        if which_detector == 0:
            log.info('Scan complete.')

            log.debug(
                f'which_detector: {which_detector}; scan_idx: {scan_idx}; scan_class: {scan_class}')

            # The results tab case.
            # self.table_result.markInsertFinished(-1, scan_idx)
            # self.table_result.updateTableDisplay(-1, self.global_scan_id)
            # All other tabs case.
            for det_idx, table in enumerate(self.table_list):
                self.table_result.markInsertFinished(det_idx, scan_idx)
                self.table_result.updateTableDisplay(
                    det_idx, self.global_scan_id)

                table.markInsertFinished(det_idx, scan_idx)
                table.updateTableDisplay(det_idx, self.global_scan_id)

                if self.autosave_data_bool:
                    log.debug('Autosaving data...')
                    self.save_data_auto(
                        table, which_detector, scanIdx=scan_idx)
                if self.autosave_next_scan:
                    log.debug('Autosaving "next" (this last) scan...')
                    self.save_data_auto(
                        table, which_detector, scanIdx=scan_idx)
                    self.autosave_next_scan = False

        else:
            det_idx = which_detector - 1
            # The results tab case.
            log.info('Detector %d scan complete.' % (det_idx))

            self.table_result.markInsertFinished(det_idx, scan_idx)
            self.table_result.updateTableDisplay(det_idx, self.global_scan_id)
            # All other tabs case.
            self.table_list[det_idx].markInsertFinished(det_idx, scan_idx)
            self.table_list[det_idx].updateTableDisplay(
                det_idx, self.global_scan_id)

            if self.autosave_data_bool:
                self.save_data_auto(
                    self.table_list[det_idx], which_detector, scanIdx=scan_idx)
            if self.autosave_next_scan:
                self.save_data_auto(
                    self.table_list[det_idx], which_detector, scanIdx=scan_idx)
                self.autosave_next_scan = False

        for table in self.table_list:
            if self.scan_repeats.value() > 0:
                if scan_class == 'main':
                    self.scan_repeats.setValue(self.scan_repeats.value() - 1)
                    self.scan_button_pressed()
                elif scan_class == 'sample':
                    self.UIE_mgw_sm_scan_repeats_qdsb.setValue(
                        self.UIE_mgw_sm_scan_repeats_qdsb.value() - 1)
                    self.scan_sm_button_pressed()
                elif scan_class == 'detector':
                    self.UIE_mgw_dm_scan_repeats_qdsb.setValue(
                        self.UIE_mgw_dm_scan_repeats_qdsb.value() - 1)
                    self.scan_dm_button_pressed()
                else:
                    self.QMessageBoxCritical(
                        'Scan Error', 'Unknown scan class %s.' % (scan_class))

        self.global_scan_id += 1

    def update_axes_info(self, mda_pos, mda_moving, mda_homing, fwa_pos, fwa_moving, fwa_homing, sra_pos, sra_moving, sra_homing, saa_pos, saa_moving, saa_homing, sta_pos, sta_moving, sta_homing, dra_pos, dra_moving, dra_homing):

        log.debug('Updating axes info...')

        if (self.scanRunning) or (mda_moving or fwa_moving or sra_moving or saa_moving or sta_moving or dra_moving) or (mda_homing or fwa_homing or sra_homing or saa_homing or sta_homing or dra_homing):  # and not (self.axes_info_prev_moving)
            log.info('One or more axes are moving.')
            log.debug(
                f'scanRunning: {self.scanRunning}; mda_moving: {mda_moving}; fwa_moving: {fwa_moving}; sra_moving: {sra_moving}; saa_moving: {saa_moving}; sta_moving: {sta_moving}; dra_moving: {dra_moving}')
            
            # UIE_mgw_move_to_position_qpb is used to see if /all/ the buttons are disabled, since it would only be disabled if this function disabled it.
            self.disable_movement_sensitive_buttons(True)
        else:
            log.info('Nothing is moving...')
            self.disable_movement_sensitive_buttons(False)
            self.anim_mgw_mda_load_spinner_start(False)
            self.anim_mgw_fwa_load_spinner_start(False)
            self.anim_mgw_saa_load_spinner_start(False)
            self.anim_mgw_sra_load_spinner_start(False)
            self.anim_mgw_sta_load_spinner_start(False)
            self.anim_mgw_dra_load_spinner_start(False)

        self.current_position = mda_pos
        self.moving = mda_moving

        self.UIE_mgw_currpos_nm_disp_ql.setText(
            '%3.4f' % (((self.current_position))))
       
        self.UIE_mgw_fwa_pos_ql.setText('%3.4f' % (fwa_pos))
        self.UIE_mgw_sra_pos_ql.setText('%3.4f' % (sra_pos))
        self.UIE_mgw_saa_pos_ql.setText('%3.4f' % (saa_pos))
        self.UIE_mgw_sta_pos_ql.setText('%3.4f' % (sta_pos))
        self.UIE_mgw_dra_pos_ql.setText('%3.4f' % (dra_pos))

    def scan_button_pressed(self):
        log.debug('scan_button_pressed function called.')
        if not self.scanRunning:
            self.scanRunning = True
            self.disable_movement_sensitive_buttons(True)
            
            self.scan.ctrl_axis = scan.ScanAxis.MAIN
            self.scan.start()
            log.debug('scan_button_press function end.')

    def scan_sm_button_pressed(self):
        if not self.scanRunning:
            self.scanRunning = True
            self.disable_movement_sensitive_buttons(True)
            
            self.scan.ctrl_axis = scan.ScanAxis.SAMPLE
            self.scan.start()

    def scan_dm_button_pressed(self):
        if not self.scanRunning:
            self.scanRunning = True
            self.disable_movement_sensitive_buttons(True)
            
            self.scan.ctrl_axis = scan.ScanAxis.DETECTOR
            self.scan.start()
            

    def stop_master_button_pressed(self):
        log.info('Master stop button pressed.')

        # TODO: Fix the way we handle scan repeats. Right now we decrement the actual spinbox - this is dumb. Store the value internally, then zero it out when we stop a scan.
        self.scan_repeats.setValue(0)

        if self.scanRunning:
            log.debug('Setting scanRunning to False.')
            self.scanRunning = False
            return

        if self.motion_controllers.main_drive_axis is not None:
            self.motion_controllers.main_drive_axis.stop()
        if self.motion_controllers.filter_wheel_axis is not None:
            self.motion_controllers.filter_wheel_axis.stop()
        if self.motion_controllers.detector_rotation_axis is not None:
            self.motion_controllers.detector_rotation_axis.stop()
        if self.motion_controllers.sample_rotation_axis is not None:
            self.motion_controllers.sample_rotation_axis.stop()
        if self.motion_controllers.sample_translation_axis is not None:
            self.motion_controllers.sample_translation_axis.stop()
        if self.motion_controllers.sample_angle_axis is not None:
            self.motion_controllers.sample_angle_axis.stop()

    def anim_mgw_mda_load_spinner_start(self, run: bool):
        if run and not self.anim_mgw_mda_load_spinner_running:
            self.anim_mgw_mda_load_spinner.start()
            self.UIE_mgw_mda_load_spinner_ql.setVisible(True)
            self.anim_mgw_mda_load_spinner_running = True
        elif not run and self.anim_mgw_mda_load_spinner_running:
            self.anim_mgw_mda_load_spinner.stop()
            self.UIE_mgw_mda_load_spinner_ql.setVisible(False)
            self.anim_mgw_mda_load_spinner_running = False
        elif run and self.anim_mgw_mda_load_spinner_running:
            pass
        elif not run and not self.anim_mgw_mda_load_spinner_running:
            pass
        else:
            log.error('Unknown animation state.')

    def anim_mgw_fwa_load_spinner_start(self, run: bool):
        if run and not self.anim_mgw_fwa_load_spinner_running:
            self.anim_mgw_fwa_load_spinner.start()
            self.UIE_mgw_fwa_load_spinner_ql.setVisible(True)
            self.anim_mgw_fwa_load_spinner_running = True
        elif not run and self.anim_mgw_fwa_load_spinner_running:
            self.anim_mgw_fwa_load_spinner.stop()
            self.UIE_mgw_fwa_load_spinner_ql.setVisible(False)
            self.anim_mgw_fwa_load_spinner_running = False
        elif run and self.anim_mgw_fwa_load_spinner_running:
            pass
        elif not run and not self.anim_mgw_fwa_load_spinner_running:
            pass
        else:
            log.error('Unknown animation state.')

    def anim_mgw_saa_load_spinner_start(self, run: bool):
        if run and not self.anim_mgw_saa_load_spinner_running:
            self.anim_mgw_saa_load_spinner.start()
            self.UIE_mgw_saa_load_spinner_ql.setVisible(True)
            self.anim_mgw_saa_load_spinner_running = True
        elif not run and self.anim_mgw_saa_load_spinner_running:
            self.anim_mgw_saa_load_spinner.stop()
            self.UIE_mgw_saa_load_spinner_ql.setVisible(False)
            self.anim_mgw_saa_load_spinner_running = False
        elif run and self.anim_mgw_saa_load_spinner_running:
            pass
        elif not run and not self.anim_mgw_saa_load_spinner_running:
            pass
        else:
            log.error('Unknown animation state.')

    def anim_mgw_sra_load_spinner_start(self, run: bool):
        if run and not self.anim_mgw_sra_load_spinner_running:
            self.anim_mgw_sra_load_spinner.start()
            self.UIE_mgw_sra_load_spinner_ql.setVisible(True)
            self.anim_mgw_sra_load_spinner_running = True
        elif not run and self.anim_mgw_sra_load_spinner_running:
            self.anim_mgw_sra_load_spinner.stop()
            self.UIE_mgw_sra_load_spinner_ql.setVisible(False)
            self.anim_mgw_sra_load_spinner_running = False
        elif run and self.anim_mgw_sra_load_spinner_running:
            pass
        elif not run and not self.anim_mgw_sra_load_spinner_running:
            pass
        else:
            log.error('Unknown animation state.')

    def anim_mgw_sta_load_spinner_start(self, run: bool):
        if run and not self.anim_mgw_sta_load_spinner_running:
            self.anim_mgw_sta_load_spinner.start()
            self.UIE_mgw_sta_load_spinner_ql.setVisible(True)
            self.anim_mgw_sta_load_spinner_running = True
        elif not run and self.anim_mgw_sta_load_spinner_running:
            self.anim_mgw_sta_load_spinner.stop()
            self.UIE_mgw_sta_load_spinner_ql.setVisible(False)
            self.anim_mgw_sta_load_spinner_running = False
        elif run and self.anim_mgw_sta_load_spinner_running:
            pass
        elif not run and not self.anim_mgw_sta_load_spinner_running:
            pass
        else:
            log.error('Unknown animation state.')

    def anim_mgw_dra_load_spinner_start(self, run: bool):
        if run and not self.anim_mgw_dra_load_spinner_running:
            self.anim_mgw_dra_load_spinner.start()
            self.UIE_mgw_dra_load_spinner_ql.setVisible(True)
            self.anim_mgw_dra_load_spinner_running = True
        elif not run and self.anim_mgw_dra_load_spinner_running:
            self.anim_mgw_dra_load_spinner.stop()
            self.UIE_mgw_dra_load_spinner_ql.setVisible(False)
            self.anim_mgw_dra_load_spinner_running = False
        elif run and self.anim_mgw_dra_load_spinner_running:
            pass
        elif not run and not self.anim_mgw_dra_load_spinner_running:
            pass
        else:
            log.error('Unknown animation state.')

    def move_to_position_button_pressed(self):

        if self.motion_controllers.main_drive_axis is None:
            log.error('Main drive axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Main drive axis is not set to any motion control channel.')
            return

        self.anim_mgw_mda_load_spinner_start(True)

        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        log.info("Steps per nm: " +
                 str(self.motion_controllers.main_drive_axis.get_steps_per_value()))
        log.info("Manual position: " + str(self.manual_position))
        log.info("Move to position button pressed, moving to %d nm" %
                 (self.manual_position))
        pos = self.UIE_mgw_pos_qdsb.value()

        try:
            self.motion_controllers.main_drive_axis.move_to(pos, False)
        except Exception as e:
            self.QMessageBoxCritical(
                'Move Failure', 'Main drive axis failed to move: %s.' % (e))
            self.moving = False
            pass

        self.moving = False

    def move_to_position_button_pressed_sr(self):
        if self.motion_controllers.sample_rotation_axis is None:
            log.error(
                'Sample rotation axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Sample rotation axis is not set to any motion control channel.')
            return

        self.anim_mgw_sra_load_spinner_start(True)

        if (self.moving):
            log.warn('ALREADY MOVING!')
            return
        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        pos = self.UIE_mgw_sm_rpos_qdsb.value()

        log.info("Move to position button (SR) pressed, moving to step %d" % (pos))
        try:
            self.motion_controllers.sample_rotation_axis.move_to(pos, False)
        except Exception as e:
            self.QMessageBoxCritical(
                'Move Failure', 'Sample rotation axis failed to move: %s' % (e))
            self.moving = False
            pass
        self.moving = False

    def move_to_position_button_pressed_sa(self):
        if self.motion_controllers.sample_angle_axis is None:
            log.error(
                'Sample angle axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Sample angle axis is not set to any motion control channel.')
            return

        self.anim_mgw_saa_load_spinner_start(True)

        if (self.moving):
            log.warn('ALREADY MOVING!')
            return
        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        pos = self.UIE_mgw_sm_apos_qdsb.value()

        log.info("Move to position button (SA) pressed, moving to step %d" % (pos))
        try:
            self.motion_controllers.sample_angle_axis.move_to(pos, False)
        except Exception as e:
            self.QMessageBoxCritical(
                'Move Failure', 'Sample angle axis failed to move: %s' % (e))
            self.moving = False
            pass
        self.moving = False
        log.debug('Completed move_to_position_button_pressed_sa() function.')

    def move_to_position_button_pressed_st(self):
        if self.motion_controllers.sample_translation_axis is None:
            log.error(
                'Sample translation axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Sample translation axis is not set to any motion control channel.')
            return

        self.anim_mgw_sta_load_spinner_start(True)

        if (self.moving):
            log.warn('ALREADY MOVING!')
            return
        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        pos = self.UIE_mgw_sm_tpos_qdsb.value()

        log.info("Move to position button (ST) pressed, moving to step %d" % (pos))
        try:
            self.motion_controllers.sample_translation_axis.move_to(pos, False)
        except Exception as e:
            self.QMessageBoxCritical(
                'Move Failure', 'Sample translation axis failed to move: %s' % (e))
            self.moving = False
            pass
        self.moving = False

    def move_to_position_button_pressed_dr(self):
        if self.motion_controllers.detector_rotation_axis is None:
            log.error(
                'Detector rotation axis is not set to any motion control channel.')
            self.QMessageBoxCritical(
                'Error', 'Detector rotation axis is not set to any motion control channel.')
            return

        self.anim_mgw_dra_load_spinner_start(True)

        if (self.moving):
            log.warn('ALREADY MOVING!')
            return

        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        pos = self.UIE_mgw_dm_rpos_qdsb.value()

        log.info("Move to position button (DR) pressed, moving to step %d" % (pos))
        try:
            self.motion_controllers.detector_rotation_axis.move_to(pos, False)
        except Exception as e:
            self.QMessageBoxCritical(
                'Move Failure', 'Detector rotation axis failed to move: %s' % (e))
            self.moving = False
            pass
        self.moving = False

    def start_changed(self):
        log.info("Start changed to: %s mm" % (self.UIE_mgw_start_qdsb.value()))
        self.startpos = (self.UIE_mgw_start_qdsb.value())
        log.debug(self.startpos)

    def stop_changed(self):
        log.info("Stop changed to: %s mm" % (self.UIE_mgw_stop_qdsb.value()))
        self.stoppos = (self.UIE_mgw_stop_qdsb.value())
        log.debug(self.stoppos)

    def step_changed(self):
        log.info("Step changed to: %s mm" % (self.UIE_mgw_step_qdsb.value()))
        self.steppos = (self.UIE_mgw_step_qdsb.value())
        log.debug(self.steppos)

    def manual_pos_changed(self):
        log.info("Manual position changed to: %s mm" %
                 (self.UIE_mgw_pos_qdsb.value()))
        self.manual_position = (self.UIE_mgw_pos_qdsb.value())

    def update_model_index(self):
        self.model_index = self.UIE_mcw_model_qcb.currentIndex()

    def show_window_spectral_ops(self):
        if self.spectral_ops_win is None:
            log.info('Setting up spectral operations window.')

            ui_file_name = exeDir + '/ui/spectral_ops.ui'
            ui_file = QFile(ui_file_name)
            if not ui_file.open(QIODevice.ReadOnly):
                log.fatal(
                    f"Cannot open {ui_file_name}: {ui_file.errorString()}")
                raise RuntimeError('Could not load grating input UI file')

            self.spectral_ops_win = QDialog(self)
            uic.loadUi(ui_file, self.spectral_ops_win)

            # Reference system.
            self.UIE_mcw_operation_qcb: QComboBox = self.spectral_ops_win.findChild(
                QComboBox, 'operation_qcb')
            self.UIE_mcw_meas_ref_qrb: QRadioButton = self.spectral_ops_win.findChild(
                QRadioButton, 'order_meas_ref_qrb')
            self.UIE_mcw_ref_meas_qrb: QRadioButton = self.spectral_ops_win.findChild(
                QRadioButton, 'order_ref_meas_qrb')

            self.UIE_mcw_operation_qcb.currentIndexChanged.connect(
                self.reference_operation_changed)
            self.UIE_mcw_meas_ref_qrb.toggled.connect(
                self.reference_order_changed)
            self.UIE_mcw_ref_meas_qrb.toggled.connect(
                self.reference_order_changed)

            self.UIE_sops_accept_qpb = self.spectral_ops_win.findChild(
                QPushButton, 'sops_accept')
            self.UIE_sops_accept_qpb.clicked.connect(self.accept_sops)

        self.spectral_ops_win.exec()

    def show_window_machine_config(self):
        log.debug(f'dr_offset: {self.dr_offset}')
        steps_per_nm = None
        first_time = False

        if self.machine_conf_win is None:
            first_time = True
            log.info('Setting up machine configuration window.')

            ui_file_name = exeDir + '/ui/machine_config.ui'
            ui_file = QFile(ui_file_name)
            if not ui_file.open(QIODevice.ReadOnly):
                log.fatal(
                    f"Cannot open {ui_file_name}: {ui_file.errorString()}")
                raise RuntimeError('Could not load grating input UI file')

            self.machine_conf_win = QDialog(self)  # pass parent window
            uic.loadUi(ui_file, self.machine_conf_win)

            self.machine_conf_win.setWindowTitle('Configuration')

            tabWidget = self.machine_conf_win.findChild(
                QTabWidget, "tabWidget")
            groupBox = self.machine_conf_win.findChild(
                QGroupBox, "speed_groupBox")

            vlayout = QVBoxLayout()
            groupBox.setLayout(vlayout)
            self.UIEL_mcw_move_speed_mults_qbsb = []
            self.UIEL_mcw_home_speed_mults_qbsb = []
            for dev in self.mtn_ctrls:
                if dev is not None:
                    # '%s: %s'%(dev.port_name(), dev.long_name())

                    hlayout1 = QHBoxLayout()
                    hlayout1.addWidget(
                        QLabel(f'{dev.port_name()}: {dev.long_name()}'))
                    hlayout2 = QHBoxLayout()
                    hlayout2.addWidget(QLabel('Move:'))
                    spinbox_move = QDoubleSpinBox()
                    spinbox_move.setMinimum(0.0)
                    spinbox_move.setMaximum(2.0)
                    spinbox_move.setValue(1.0)
                    hlayout2.addWidget(spinbox_move)
                    hlayout2.addWidget(QLabel('Home:'))
                    spinbox_home = QDoubleSpinBox()
                    spinbox_home.setMinimum(0.0)
                    spinbox_home.setMaximum(2.0)
                    spinbox_home.setValue(1.0)
                    hlayout2.addWidget(spinbox_home)
                    vlayout.addLayout(hlayout1)
                    vlayout.addLayout(hlayout2)

                    self.UIEL_mcw_move_speed_mults_qbsb.append(spinbox_move)
                    self.UIEL_mcw_home_speed_mults_qbsb.append(spinbox_home)

            self.UIE_mcw_scan_start_delay_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'scan_start_delay')
            self.UIE_mcw_detection_delay_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'detection_delay')
            self.UIE_mcw_per_detection_averages_qsb: QSpinBox = self.machine_conf_win.findChild(
                QSpinBox, 'per_detection_averages')

            self.UIE_mcw_scan_start_delay_qdsb.valueChanged.connect(
                self.update_scan_start_delay)
            self.UIE_mcw_detection_delay_qdsb.valueChanged.connect(
                self.update_detection_delay)
            self.UIE_mcw_per_detection_averages_qsb.valueChanged.connect(
                self.update_per_detection_averages)

            self.UIE_mcw_model_qcb: QComboBox = self.machine_conf_win.findChild(
                QComboBox, 'models')
            self.UIE_mcw_model_qcb.addItems(McPherson.MONO_MODELS)

            self.UIE_mcw_grating_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'grating_density')

            self.UIE_mcw_zero_ofst_in_qdsb = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'zero_offset_in')

            self.UIE_mcw_max_pos_in_qdsb = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'max_pos_sbox')

            self.UIE_mcw_min_pos_in_qdsb = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'min_pos_sbox')

            self.UIE_mcw_machine_conf_qpb = self.machine_conf_win.findChild(
                QPushButton, 'update_conf_btn')

            self.UIE_mcw_steps_per_nm_ql = self.machine_conf_win.findChild(
                QLabel, 'steps_per_nm')

            try:
                steps_per_nm = self.motion_controllers.main_drive_axis.get_steps_per_value()
            except Exception as e:
                log.warn(
                    'Error getting steps per nm: %s. The Main Drive Axis may not be assigned a motion controller.' % (e))

            self.UIE_mcw_steps_per_nm_override_qdsb = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'steps_per_nm_override')
            self.UIE_mcw_override_steps_per_nm_qckbx = self.machine_conf_win.findChild(
                QCheckBox, 'override_steps_per_nm')
            self.UIE_mcw_enact_override_qpb = self.machine_conf_win.findChild(
                QPushButton, 'enact_override')
            self.UIE_mcw_enact_override_qpb.setEnabled(False)

            self.UIE_mcw_accept_qpb = self.machine_conf_win.findChild(
                QPushButton, 'mcw_accept')

            # Get axes combos.
            self.UIE_mcw_main_drive_axis_qcb: QComboBox = self.machine_conf_win.findChild(
                QComboBox, "main_drive_axis_combo")
            self.UIE_mcw_filter_wheel_axis_qcb: QComboBox = self.machine_conf_win.findChild(
                QComboBox, "filter_wheel_axis_combo")
            self.UIE_mcw_sample_rotation_axis_qcb: QComboBox = self.machine_conf_win.findChild(
                QComboBox, "sample_rotation_axis_combo")
            self.UIE_mcw_sample_angle_axis_qcb: QComboBox = self.machine_conf_win.findChild(
                QComboBox, 'sample_angle_axis_combo')
            self.UIE_mcw_sample_translation_axis_qcb: QComboBox = self.machine_conf_win.findChild(
                QComboBox, "sample_translation_axis_combo")
            self.UIE_mcw_detector_rotation_axis_qcb: QComboBox = self.machine_conf_win.findChild(
                QComboBox, "detector_rotation_axis_combo")

            none = 'No Device Selected'
            self.UIE_mcw_main_drive_axis_qcb.addItem('%s' % (none))
            self.UIE_mcw_filter_wheel_axis_qcb.addItem('%s' % (none))
            self.UIE_mcw_sample_rotation_axis_qcb.addItem('%s' % (none))
            self.UIE_mcw_sample_angle_axis_qcb.addItem('%s' % (none))
            self.UIE_mcw_sample_translation_axis_qcb.addItem('%s' % (none))
            self.UIE_mcw_detector_rotation_axis_qcb.addItem('%s' % (none))

            # Populate axes combos.
            log.debug(self.mtn_ctrls)
            for dev in self.mtn_ctrls:
                if dev is not None:
                    log.info('Adding %s to config list.' % (dev))

                    self.UIE_mcw_main_drive_axis_qcb.addItem(
                        '%s: %s' % (dev.port_name(), dev.long_name()))
                    self.UIE_mcw_filter_wheel_axis_qcb.addItem(
                        '%s: %s' % (dev.port_name(), dev.long_name()))
                    self.UIE_mcw_sample_rotation_axis_qcb.addItem(
                        '%s: %s' % (dev.port_name(), dev.long_name()))
                    self.UIE_mcw_sample_angle_axis_qcb.addItem(
                        '%s: %s' % (dev.port_name(), dev.long_name()))
                    self.UIE_mcw_sample_translation_axis_qcb.addItem(
                        '%s: %s' % (dev.port_name(), dev.long_name()))
                    self.UIE_mcw_detector_rotation_axis_qcb.addItem(
                        '%s: %s' % (dev.port_name(), dev.long_name()))

                    self.UIE_mcw_main_drive_axis_qcb.setCurrentIndex(1)

            self.UIE_mcw_fw_steps_per_rot_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'fw_steps_per_deg')
            self.UIE_mcw_fw_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'fw_max')
            self.UIE_mcw_fw_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'fw_min')
            self.UIE_mcw_sm_steps_per_rot_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'smr_steps_per_deg')
            self.UIE_mcw_smr_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'smr_max')
            self.UIE_mcw_smr_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'smr_min')
            self.UIE_mcw_sm_steps_per_ang_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'sma_steps_per_deg')
            self.UIE_mcw_sma_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'sma_max')
            self.UIE_mcw_sma_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'sma_min')
            self.UIE_mcw_sm_steps_per_trans_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'smt_steps_per_deg')
            self.UIE_mcw_smt_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'smt_max')
            self.UIE_mcw_smt_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'smt_min')
            self.UIE_mcw_dr_steps_per_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'dr_steps_per_deg')
            self.UIE_mcw_dr_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'dr_max')
            self.UIE_mcw_dr_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'dr_min')

            log.debug(f'dr_offset: {self.dr_offset}')
            self.UIE_mcw_fw_offset_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'fw_offset')
            self.UIE_mcw_sr_offset_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'sr_offset')
            self.UIE_mcw_sa_offset_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'sa_offset')
            self.UIE_mcw_st_offset_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'st_offset')
            self.UIE_mcw_dr_offset_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(
                QDoubleSpinBox, 'dr_offset')
            log.debug(f'dr_offset: {self.dr_offset}')

            # TEMPORARY DISABLING OF UI ELEMENT UNTIL FUTURE VERSION IMPLEMENTATION.

            if not SHOW_FILTER_WHEEL:
                tabWidget.removeTab(tabWidget.indexOf(
                    tabWidget.findChild(QWidget, 'filter_wheel_tab')))
            if not SHOW_SAMPLE_MOVEMENT:
                tabWidget.removeTab(tabWidget.indexOf(
                    tabWidget.findChild(QWidget, 'sample_tab')))
            if not SHOW_DETECTOR_ROTATION:
                tabWidget.removeTab(tabWidget.indexOf(
                    tabWidget.findChild(QWidget, 'detector_tab')))

            # TODO: Create and populate new tabs for:
                # Lock-in Amplifiers (1 or 2) [Programmatically?]
                # Generic Detector Math [Should already exist from QtDesigner]

        self.UIE_mcw_scan_start_delay_qdsb.setValue(self.scan_start_delay)
        self.UIE_mcw_detection_delay_qdsb.setValue(self.detection_delay)
        self.UIE_mcw_per_detection_averages_qsb.setValue(
            self.per_detection_averages)

        self.UIE_mcw_model_qcb.setCurrentIndex(self.model_index)

        self.UIE_mcw_grating_qdsb.setValue(self.grating_density)
        # This resets the value of the related variables because its already connected to the update_offsets function, which sets the variables to 0 because thats the default and current value in the spinboxes...
        self.UIE_mcw_zero_ofst_in_qdsb.setValue(self.zero_ofst)
        self.UIE_mcw_max_pos_in_qdsb.setValue(self.max_pos)
        self.UIE_mcw_min_pos_in_qdsb.setValue(self.min_pos)

        try:
            steps_per_nm = self.motion_controllers.main_drive_axis.get_steps_per_value()
        except Exception as e:
            log.warn(
                'Error getting steps per nm: %s. The Main Drive Axis may not be assigned a motion controller.' % (e))

        if steps_per_nm == 0.0:
            self.UIE_mcw_steps_per_nm_ql.setText('NOT CALCULATED')
        else:
            self.UIE_mcw_steps_per_nm_ql.setText(str(steps_per_nm))

        self.UIE_mcw_fw_offset_qdsb.setValue(self.fw_offset)
        self.UIE_mcw_sr_offset_qdsb.setValue(self.sr_offset)
        self.UIE_mcw_st_offset_qdsb.setValue(self.st_offset)
        self.UIE_mcw_sa_offset_qdsb.setValue(self.sa_offset)
        self.UIE_mcw_dr_offset_qdsb.setValue(self.dr_offset)

        self.UIE_mcw_main_drive_axis_qcb.setCurrentIndex(self.main_axis_index)
        self.UIE_mcw_filter_wheel_axis_qcb.setCurrentIndex(
            self.filter_axis_index)
        self.UIE_mcw_sample_rotation_axis_qcb.setCurrentIndex(
            self.rsamp_axis_index)
        self.UIE_mcw_sample_angle_axis_qcb.setCurrentIndex(
            self.asamp_axis_index)
        self.UIE_mcw_sample_translation_axis_qcb.setCurrentIndex(
            self.tsamp_axis_index)
        self.UIE_mcw_detector_rotation_axis_qcb.setCurrentIndex(
            self.detector_axis_index)

        self.UIE_mcw_max_pos_in_qdsb.setValue(self.max_pos)
        self.UIE_mcw_min_pos_in_qdsb.setValue(self.min_pos)
        self.UIE_mcw_fw_max_qdsb.setValue(self.fw_max_pos)
        self.UIE_mcw_fw_min_qdsb.setValue(self.fw_min_pos)
        self.UIE_mcw_smr_max_qdsb.setValue(self.smr_max_pos)
        self.UIE_mcw_smr_min_qdsb.setValue(self.smr_min_pos)
        self.UIE_mcw_sma_max_qdsb.setValue(self.sma_max_pos)
        self.UIE_mcw_sma_min_qdsb.setValue(self.sma_min_pos)
        self.UIE_mcw_smt_max_qdsb.setValue(self.smt_max_pos)
        self.UIE_mcw_smt_min_qdsb.setValue(self.smt_min_pos)
        self.UIE_mcw_dr_max_qdsb.setValue(self.dr_max_pos)
        self.UIE_mcw_dr_min_qdsb.setValue(self.dr_min_pos)

        self.UIE_mcw_fw_steps_per_rot_qdsb.setValue(self.fw_sp)
        self.UIE_mcw_sm_steps_per_rot_qdsb.setValue(self.sr_sp)
        self.UIE_mcw_sm_steps_per_ang_qdsb.setValue(self.sa_sp)
        self.UIE_mcw_sm_steps_per_trans_qdsb.setValue(self.st_sp)
        self.UIE_mcw_dr_steps_per_qdsb.setValue(self.dr_sp)

        if first_time:
            self.UIE_mcw_model_qcb.currentIndexChanged.connect(
                self.update_model_index)
            self.UIE_mcw_machine_conf_qpb.clicked.connect(
                self.apply_machine_conf)
            self.UIE_mcw_override_steps_per_nm_qckbx.stateChanged.connect(
                self.update_override_button)
            self.UIE_mcw_enact_override_qpb.clicked.connect(
                self.override_steps_per_nm)
            self.UIE_mcw_accept_qpb.clicked.connect(self.accept_mcw)

            self.UIE_mcw_main_drive_axis_qcb.currentIndexChanged.connect(
                self.mcw_axis_change_main)
            self.UIE_mcw_filter_wheel_axis_qcb.currentIndexChanged.connect(
                self.mcw_axis_change_filter)
            self.UIE_mcw_sample_rotation_axis_qcb.currentIndexChanged.connect(
                self.mcw_axis_change_rsamp)
            self.UIE_mcw_sample_angle_axis_qcb.currentIndexChanged.connect(
                self.mcw_axis_change_asamp)
            self.UIE_mcw_sample_translation_axis_qcb.currentIndexChanged.connect(
                self.mcw_axis_change_tsamp)
            self.UIE_mcw_detector_rotation_axis_qcb.currentIndexChanged.connect(
                self.mcw_axis_change_detector)

            self.UIE_mcw_sm_steps_per_rot_qdsb.valueChanged.connect(
                self.update_steps_per)
            self.UIE_mcw_sm_steps_per_ang_qdsb.valueChanged.connect(
                self.update_steps_per)
            self.UIE_mcw_sm_steps_per_trans_qdsb.valueChanged.connect(
                self.update_steps_per)
            self.UIE_mcw_dr_steps_per_qdsb.valueChanged.connect(
                self.update_steps_per)

            self.UIE_mcw_zero_ofst_in_qdsb.valueChanged.connect(
                self.update_offsets)
            self.UIE_mcw_fw_offset_qdsb.valueChanged.connect(
                self.update_offsets)
            self.UIE_mcw_sr_offset_qdsb.valueChanged.connect(
                self.update_offsets)
            self.UIE_mcw_sa_offset_qdsb.valueChanged.connect(
                self.update_offsets)
            self.UIE_mcw_st_offset_qdsb.valueChanged.connect(
                self.update_offsets)
            self.UIE_mcw_dr_offset_qdsb.valueChanged.connect(
                self.update_offsets)

        # synchronously run this window so parent window is disabled
        self.machine_conf_win.exec()
        log.debug('Exec done')

    def update_detection_delay(self):
        log.info("Detection delay changed to: %s ms" %
                 (self.UIE_mcw_detection_delay_qdsb.value()))
        self.detection_delay = self.UIE_mcw_detection_delay_qdsb.value()
        for det in self.detectors:
            if det is not None:
                det.detect_delay = self.detection_delay

    def update_scan_start_delay(self):
        log.info("Scan start delay changed to: %s ms" %
                 (self.UIE_mcw_scan_start_delay_qdsb.value()))
        self.scan_start_delay = self.UIE_mcw_scan_start_delay_qdsb.value()

    def update_per_detection_averages(self):
        log.info("Per detection averages changed to: %s" %
                 (self.UIE_mcw_per_detection_averages_qsb.value()))
        self.per_detection_averages = self.UIE_mcw_per_detection_averages_qsb.value()
        for det in self.detectors:
            if det is not None:
                det.per_detection_averages = self.per_detection_averages

    def reference_operation_changed(self):
        self.reference_operation = self.UIE_mcw_operation_qcb.currentIndex()

    def reference_order_changed(self):
        self.reference_order_meas_ref = self.UIE_mcw_meas_ref_qrb.isChecked()

    # None main axis steps per updater
    def update_steps_per(self):
        self.fw_sp = self.UIE_mcw_fw_steps_per_rot_qdsb.value()
        self.sr_sp = self.UIE_mcw_sm_steps_per_rot_qdsb.value()
        self.sa_sp = self.UIE_mcw_sm_steps_per_ang_qdsb.value()
        self.st_sp = self.UIE_mcw_sm_steps_per_trans_qdsb.value()
        self.dr_sp = self.UIE_mcw_dr_steps_per_qdsb.value()

        if self.motion_controllers.filter_wheel_axis is not None:
            self.motion_controllers.filter_wheel_axis.set_steps_per_value(
                self.fw_sp)
        else:
            log.warn('Filter wheel axis not set.')

        if self.motion_controllers.sample_rotation_axis is not None:
            self.motion_controllers.sample_rotation_axis.set_steps_per_value(
                self.sr_sp)
        else:
            log.warn('Sample rotation axis not set.')

        if self.motion_controllers.sample_angle_axis is not None:
            self.motion_controllers.sample_angle_axis.set_steps_per_value(
                self.sa_sp)
        else:
            log.warn('Sample angle axis not set.')

        if self.motion_controllers.sample_translation_axis is not None:
            self.motion_controllers.sample_translation_axis.set_steps_per_value(
                self.st_sp)
        else:
            log.warn('Sample translation axis not set.')

        if self.motion_controllers.detector_rotation_axis is not None:
            self.motion_controllers.detector_rotation_axis.set_steps_per_value(
                self.dr_sp)
        else:
            log.warn('Detector rotation axis not set.')

    def update_offsets(self):
        if self.UIE_mcw_zero_ofst_in_qdsb is not None:
            self.zero_ofst = self.UIE_mcw_zero_ofst_in_qdsb.value()
        if self.UIE_mcw_fw_offset_qdsb is not None:
            self.fw_offset = self.UIE_mcw_fw_offset_qdsb.value()
        if self.UIE_mcw_st_offset_qdsb is not None:
            self.st_offset = self.UIE_mcw_st_offset_qdsb.value()
        if self.UIE_mcw_sr_offset_qdsb is not None:
            self.sr_offset = self.UIE_mcw_sr_offset_qdsb.value()
        if self.UIE_mcw_sa_offset_qdsb is not None:
            self.sa_offset = self.UIE_mcw_sa_offset_qdsb.value()
        if self.UIE_mcw_dr_offset_qdsb is not None:
            self.dr_offset = self.UIE_mcw_dr_offset_qdsb.value()

        if self.motion_controllers.main_drive_axis is not None:

            log.debug('Main drive offset before --- ', self.motion_controllers.main_drive_axis.get_offset(),
                      self.motion_controllers.main_drive_axis._offset)

            self.motion_controllers.main_drive_axis.set_offset(self.zero_ofst)

            log.debug('Main drive offset before --- ', self.motion_controllers.main_drive_axis.get_offset(),
                      self.motion_controllers.main_drive_axis._offset)

        if self.motion_controllers.filter_wheel_axis is not None:
            self.motion_controllers.filter_wheel_axis.set_offset(
                self.fw_offset)
        if self.motion_controllers.sample_translation_axis is not None:
            self.motion_controllers.sample_translation_axis.set_offset(
                self.st_offset)
        if self.motion_controllers.sample_rotation_axis is not None:
            self.motion_controllers.sample_rotation_axis.set_offset(
                self.sr_offset)
        if self.motion_controllers.sample_angle_axis is not None:
            self.motion_controllers.sample_angle_axis.set_offset(
                self.sa_offset)
        if self.motion_controllers.detector_rotation_axis is not None:
            self.motion_controllers.detector_rotation_axis.set_offset(
                self.dr_offset)

    def update_movement_limits_gui(self):
        self.UIE_mgw_pos_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_pos_qdsb.setMinimum(self.min_pos)

        self.UIE_mgw_start_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_start_qdsb.setMinimum(self.min_pos)

        self.UIE_mgw_stop_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_stop_qdsb.setMinimum(self.min_pos)

    def apply_machine_conf(self):  # 'Calculate Steps per Nanometer' button.
        self.grating_density = self.UIE_mcw_grating_qdsb.value()
        log.debug(self.grating_density)

        self.update_movement_limits_gui()

        self.update_offsets()

        self.calculate_and_apply_steps_per_nm()

    def update_override_button(self):
        self.UIE_mcw_enact_override_qpb.setEnabled(
            self.UIE_mcw_override_steps_per_nm_qckbx.isChecked())

    def override_steps_per_nm(self):
        if self.UIE_mcw_override_steps_per_nm_qckbx.isChecked():
            log.info('Desired override value is:',
                     self.UIE_mcw_steps_per_nm_override_qdsb.value())
            if self.motion_controllers.main_drive_axis is not None:
                self.motion_controllers.main_drive_axis.set_steps_per_value(
                    self.UIE_mcw_steps_per_nm_override_qdsb.value())
                log.info('Settings steps_per_value:',
                         self.motion_controllers.main_drive_axis.get_steps_per_value())
            else:
                log.info('Main drive axis is None.')

            if self.UIE_mcw_steps_per_nm_ql is not None:
                self.UIE_mcw_steps_per_nm_ql.setText(
                    str(self.motion_controllers.main_drive_axis.get_steps_per_value()))

    def calculate_and_apply_steps_per_nm(self):
        steps_per_rev = McPherson.MONO_STEPS_PER_REV[McPherson.MONO_MODELS[self.model_index]]

        if self.motion_controllers.main_drive_axis is None:
            log.warn(
                'The main drive axis motion controllers is NoneType. Did you forget to set the main drive axis device?')
            return

        try:
            steps_per_value = McPherson.get_steps_per_nm(
                steps_per_rev, McPherson.MONO_MODELS[self.model_index], self.grating_density)
            self.motion_controllers.main_drive_axis.set_steps_per_value(
                steps_per_value)
        except Exception as e:
            log.error(e)
            self.QMessageBoxCritical(
                'Failed to Update Values', e + ' Please keep in mind that Models 272 and Model 608 Pre-Disperser only accept specific grating densities.')
            pass

        log.info('Settings steps_per_value:',
                 self.motion_controllers.main_drive_axis.get_steps_per_value())
        if self.UIE_mcw_steps_per_nm_ql is not None:
            self.UIE_mcw_steps_per_nm_ql.setText(
                str(self.motion_controllers.main_drive_axis.get_steps_per_value()))

    def mcw_axis_change_main(self):
        log.trace('mcw_axis_change_main')

        if self.machine_conf_win is None:
            log.warn(
                'mcw_axis_change_main called but machine_conf_win is NoneType.')
            return

        self.mgw_axis_change_main(True)

    def mgw_axis_change_main(self, mcw=False):
        log.trace()
        if mcw and self.machine_conf_win is None:
            log.warn(
                'mgw_axis_change_main called with mcw True but machine_conf_win is NoneType.')
            mcw = False
        if self.machine_conf_win is None:
            mcw = False

        if mcw:
            self.main_axis_index = self.UIE_mcw_main_drive_axis_qcb.currentIndex()
        else:
            self.main_axis_index = self.UIE_mgw_main_drive_axis_qcb.currentIndex()
        if self.main_axis_index < 0:
            self.main_axis_index = 0

        idx_list = [self.filter_axis_index, self.rsamp_axis_index,
                    self.asamp_axis_index, self.tsamp_axis_index, self.detector_axis_index]

        if (self.main_axis_index != 0) and (self.main_axis_index in idx_list):
            log.warn('Main axis index found to be duplicate. Resetting.')
            self.QMessageBoxWarning(
                'Invalid Configuration', 'The device selected for one or more axes was found to already be selected for another.')
            self.main_axis_index = 0

        self.motion_controllers.main_drive_axis = self.mtn_ctrls[self.main_axis_index]
        if self.motion_controllers.main_drive_axis is not None:
            self.main_axis_dev_name = self.motion_controllers.main_drive_axis.short_name()
        else:
            self.main_axis_dev_name = 'Loaded Config Name Empty'

        self.UIE_mgw_main_drive_axis_qcb.setCurrentIndex(self.main_axis_index)
        if mcw:
            self.UIE_mcw_main_drive_axis_qcb.setCurrentIndex(
                self.main_axis_index)

        # Sets buttons which operate on this axis to enabled only if the selection index is non-zero.
        is_zero = (self.UIE_mgw_main_drive_axis_qcb.currentIndex() != 0)
        self.UIE_mgw_move_to_position_qpb.setEnabled(is_zero)
        self.UIE_mgw_home_qpb.setEnabled(is_zero)
        self.UIE_mgw_scan_qpb.setEnabled(is_zero)

        self.UIE_mgw_pframe_1_qf.setVisible(is_zero)

        return self.main_axis_index

    def mcw_axis_change_filter(self):
        log.trace('mcw_axis_change_filter')
        if self.machine_conf_win is None:
            log.warn(
                'mcw_axis_change_filter called but machine_conf_win is NoneType.')
            return

        self.mgw_axis_change_filter(True)

    def mgw_axis_change_filter(self, mcw=False):
        log.trace()
        # print(mcw)
        if mcw and self.machine_conf_win is None:
            log.warn(
                'mgw_axis_change_filter called with mcw True but machine_conf_win is NoneType.')
            mcw = False
        if mcw:
            self.filter_axis_index = self.UIE_mcw_filter_wheel_axis_qcb.currentIndex()
        else:
            self.filter_axis_index = self.UIE_mgw_filter_wheel_axis_qcb.currentIndex()
        if self.filter_axis_index < 0:
            self.filter_axis_index = 0

        idx_list = [self.main_axis_index, self.rsamp_axis_index,
                    self.asamp_axis_index, self.tsamp_axis_index, self.detector_axis_index]

        if (self.filter_axis_index != 0) and (self.filter_axis_index in idx_list):
            log.warn('Main axis index found to be duplicate. Resetting.')
            self.QMessageBoxWarning(
                'Invalid Configuration', 'The device selected for one or more axes was found to already be selected for another.')
            self.filter_axis_index = 0

        self.motion_controllers.filter_wheel_axis = self.mtn_ctrls[self.filter_axis_index]
        if self.motion_controllers.filter_wheel_axis is not None:
            self.filter_axis_dev_name = self.motion_controllers.filter_wheel_axis.short_name()
        else:
            self.filter_axis_dev_name = 'Loaded Config Name Empty'

        self.UIE_mgw_filter_wheel_axis_qcb.setCurrentIndex(
            self.filter_axis_index)
        if mcw:
            self.UIE_mcw_filter_wheel_axis_qcb.setCurrentIndex(
                self.filter_axis_index)

        is_zero = (self.UIE_mgw_filter_wheel_axis_qcb.currentIndex() != 0)
        self.UIE_mgw_fw_mancon_move_pos_qpb.setEnabled(is_zero)
        self.UIE_mgw_fw_mancon_home_qpb.setEnabled(is_zero)

        self.UIE_mgw_pframe_2_qf.setVisible(is_zero and SHOW_FILTER_WHEEL)


        return self.filter_axis_index

    def mcw_axis_change_rsamp(self):
        log.trace('mcw_axis_change_rsamp')
        if self.machine_conf_win is None:
            log.warn(
                'mcw_axis_change_rsamp called but machine_conf_win is NoneType.')
            return
        self.mgw_axis_change_rsamp(True)

    def mgw_axis_change_rsamp(self, mcw=False):
        log.trace()
        if mcw and self.machine_conf_win is None:
            log.warn(
                'mgw_axis_change_rsamp called with mcw True but machine_conf_win is NoneType.')
            mcw = False
        if mcw:
            self.rsamp_axis_index = self.UIE_mcw_sample_rotation_axis_qcb.currentIndex()
        else:
            self.rsamp_axis_index = self.UIE_mgw_sample_rotation_axis_qcb.currentIndex()
        if self.rsamp_axis_index < 0:
            self.rsamp_axis_index = 0

        idx_list = [self.main_axis_index, self.filter_axis_index,
                    self.asamp_axis_index, self.tsamp_axis_index, self.detector_axis_index]

        if (self.rsamp_axis_index != 0) and (self.rsamp_axis_index in idx_list):
            log.warn('Main axis index found to be duplicate. Resetting.')
            self.QMessageBoxWarning(
                'Invalid Configuration', 'The device selected for one or more axes was found to already be selected for another.')
            self.rsamp_axis_index = 0

        self.motion_controllers.sample_rotation_axis = self.mtn_ctrls[self.rsamp_axis_index]
        if self.motion_controllers.sample_rotation_axis is not None:
            self.rsamp_axis_dev_name = self.motion_controllers.sample_rotation_axis.short_name()
        else:
            self.rsamp_axis_dev_name = 'Loaded Config Name Empty'

        self.UIE_mgw_sample_rotation_axis_qcb.setCurrentIndex(
            self.rsamp_axis_index)
        if mcw:
            self.UIE_mcw_sample_rotation_axis_qcb.setCurrentIndex(
                self.rsamp_axis_index)

        is_zero = (self.UIE_mgw_sample_rotation_axis_qcb.currentIndex() != 0)
        self.UIE_mgw_sm_rmove_qpb.setEnabled(is_zero)
        self.UIE_mgw_sm_rhome_qpb.setEnabled(is_zero)

        self.UIE_mgw_pframe_3_qf.setVisible(is_zero)

        return self.rsamp_axis_index

    def mcw_axis_change_asamp(self):
        log.trace('mcw_axis_change_asamp')
        if self.machine_conf_win is None:
            log.warn(
                'mcw_axis_change_asamp called but machine_conf_win is NoneType.')
            return
        self.mgw_axis_change_asamp(True)

    def mgw_axis_change_asamp(self, mcw=False):
        log.trace()
        if mcw and self.machine_conf_win is None:
            log.warn(
                'mgw_axis_change_asamp called with mcw True but machine_conf_win is NoneType.')
            mcw = False
        if mcw:
            self.asamp_axis_index = self.UIE_mcw_sample_angle_axis_qcb.currentIndex()
        else:
            self.asamp_axis_index = self.UIE_mgw_sample_angle_axis_qcb.currentIndex()
        if self.asamp_axis_index < 0:
            self.asamp_axis_index = 0

        idx_list = [self.main_axis_index, self.filter_axis_index,
                    self.rsamp_axis_index, self.tsamp_axis_index, self.detector_axis_index]

        if (self.asamp_axis_index != 0) and (self.asamp_axis_index in idx_list):
            log.warn('Main axis index found to be duplicate. Resetting.')
            self.QMessageBoxWarning(
                'Invalid Configuration', 'The device selected for one or more axes was found to already be selected for another.')
            self.asamp_axis_index = 0

        self.motion_controllers.sample_angle_axis = self.mtn_ctrls[self.asamp_axis_index]
        if self.motion_controllers.sample_angle_axis is not None:
            self.asamp_axis_dev_name = self.motion_controllers.sample_angle_axis.short_name()
        else:
            self.asamp_axis_dev_name = 'Loaded Config Name Empty'

        self.UIE_mgw_sample_angle_axis_qcb.setCurrentIndex(
            self.asamp_axis_index)
        if mcw:
            self.UIE_mcw_sample_angle_axis_qcb.setCurrentIndex(
                self.asamp_axis_index)

        is_zero = (self.UIE_mgw_sample_angle_axis_qcb.currentIndex() != 0)
        self.UIE_mgw_sm_amove_qpb.setEnabled(is_zero)
        self.UIE_mgw_sm_ahome_qpb.setEnabled(is_zero)

        self.UIE_mgw_pframe_4_qf.setVisible(is_zero)

        return self.asamp_axis_index

    def mcw_axis_change_tsamp(self):
        log.trace('mcw_axis_change_tsamp')
        if self.machine_conf_win is None:
            log.warn(
                'mcw_axis_change_tsamp called but machine_conf_win is NoneType.')
            return
        self.mgw_axis_change_tsamp(True)

    def mgw_axis_change_tsamp(self, mcw=False):
        log.trace()
        if mcw and self.machine_conf_win is None:
            log.warn(
                'mgw_axis_change_tsamp called with mcw True but machine_conf_win is NoneType.')
            mcw = False
        if mcw:
            self.tsamp_axis_index = self.UIE_mcw_sample_translation_axis_qcb.currentIndex()
        else:
            self.tsamp_axis_index = self.UIE_mgw_sample_translation_axis_qcb.currentIndex()
        if self.tsamp_axis_index < 0:
            self.tsamp_axis_index = 0

        idx_list = [self.main_axis_index, self.filter_axis_index,
                    self.rsamp_axis_index, self.asamp_axis_index, self.detector_axis_index]

        if (self.tsamp_axis_index != 0) and (self.tsamp_axis_index in idx_list):
            log.warn('Main axis index found to be duplicate. Resetting.')
            self.QMessageBoxWarning(
                'Invalid Configuration', 'The device selected for one or more axes was found to already be selected for another.')
            self.tsamp_axis_index = 0

        self.motion_controllers.sample_translation_axis = self.mtn_ctrls[self.tsamp_axis_index]
        if self.motion_controllers.sample_translation_axis is not None:
            self.tsamp_axis_dev_name = self.motion_controllers.sample_translation_axis.short_name()
        else:
            self.tsamp_axis_dev_name = 'Loaded Config Name Empty'

        self.UIE_mgw_sample_translation_axis_qcb.setCurrentIndex(
            self.tsamp_axis_index)
        if mcw:
            self.UIE_mcw_sample_translation_axis_qcb.setCurrentIndex(
                self.tsamp_axis_index)

        is_zero = (self.UIE_mgw_sample_translation_axis_qcb.currentIndex() != 0)
        self.UIE_mgw_sm_tmove_qpb.setEnabled(is_zero)
        self.UIE_mgw_sm_thome_qpb.setEnabled(is_zero)

        self.UIE_mgw_pframe_5_qf.setVisible(is_zero)

        return self.tsamp_axis_index

    def mcw_axis_change_detector(self):
        log.trace('mcw_axis_change_detector')
        if self.machine_conf_win is None:
            log.warn(
                'mcw_axis_change_detector called but machine_conf_win is NoneType.')
            return
        self.mgw_axis_change_detector(True)

    def mgw_axis_change_detector(self, mcw=False):
        log.trace()
        if mcw and self.machine_conf_win is None:
            log.warn(
                'mgw_axis_change_detector called with mcw True but machine_conf_win is NoneType.')
            mcw = False
        if mcw:
            self.detector_axis_index = self.UIE_mcw_detector_rotation_axis_qcb.currentIndex()
        else:
            self.detector_axis_index = self.UIE_mgw_detector_rotation_axis_qcb.currentIndex()
        if self.detector_axis_index < 0:
            self.detector_axis_index = 0

        idx_list = [self.main_axis_index, self.filter_axis_index,
                    self.rsamp_axis_index, self.asamp_axis_index, self.tsamp_axis_index]

        if (self.detector_axis_index != 0) and (self.detector_axis_index in idx_list):
            log.warn('Main axis index found to be duplicate. Resetting.')
            self.QMessageBoxWarning(
                'Invalid Configuration', 'The device selected for one or more axes was found to already be selected for another.')
            self.detector_axis_index = 0

        self.motion_controllers.detector_rotation_axis = self.mtn_ctrls[self.detector_axis_index]
        if self.motion_controllers.detector_rotation_axis is not None:
            self.detector_axis_dev_name = self.motion_controllers.detector_rotation_axis.short_name()
        else:
            self.detector_axis_dev_name = 'Loaded Config Name Empty'

        self.UIE_mgw_detector_rotation_axis_qcb.setCurrentIndex(
            self.detector_axis_index)
        if mcw:
            self.UIE_mcw_detector_rotation_axis_qcb.setCurrentIndex(
                self.detector_axis_index)

        is_zero = (self.UIE_mgw_detector_rotation_axis_qcb.currentIndex() != 0)
        self.UIE_mgw_dm_rmove_qpb.setEnabled(is_zero)
        self.UIE_mgw_dm_rhome_qpb.setEnabled(is_zero)
        self.UIE_mgw_dm_begin_scan_qpb.setEnabled(is_zero)

        self.UIE_mgw_pframe_6_qf.setVisible(is_zero)

        return self.detector_axis_index

    def accept_sops(self):
        self.spectral_ops_win.close()

    def accept_mcw(self):
        log.info('~~MACHINE CONFIGURATION ACCEPT CALLED:')
        log.info('~Main Drive')
        log.info(self.UIE_mcw_main_drive_axis_qcb.currentText())
        log.info('~Color Wheel Axis')
        log.info(self.UIE_mcw_filter_wheel_axis_qcb.currentText())
        log.info('~Sample Axes')
        log.info(self.UIE_mcw_sample_rotation_axis_qcb.currentText())
        log.info(self.UIE_mcw_sample_angle_axis_qcb.currentText())
        log.info(self.UIE_mcw_sample_translation_axis_qcb.currentText())
        log.info('~Detector Rotation Axis')
        log.info(self.UIE_mcw_detector_rotation_axis_qcb.currentText())
        log.info('~~')

        # Auto-apply the steps per nm unless user is overriding.
        if not self.UIE_mcw_override_steps_per_nm_qckbx.isChecked():
            self.calculate_and_apply_steps_per_nm()

        self.mgw_axis_change_main()
        self.mgw_axis_change_filter()
        self.mgw_axis_change_rsamp()
        self.mgw_axis_change_asamp()
        self.mgw_axis_change_tsamp()
        self.mgw_axis_change_detector()

        self.UIE_mgw_main_drive_axis_qcb.setCurrentIndex(self.main_axis_index)
        self.UIE_mgw_filter_wheel_axis_qcb.setCurrentIndex(
            self.filter_axis_index)
        self.UIE_mgw_sample_rotation_axis_qcb.setCurrentIndex(
            self.rsamp_axis_index)
        self.UIE_mgw_sample_angle_axis_qcb.setCurrentIndex(
            self.asamp_axis_index)
        self.UIE_mgw_sample_translation_axis_qcb.setCurrentIndex(
            self.tsamp_axis_index)
        self.UIE_mgw_detector_rotation_axis_qcb.setCurrentIndex(
            self.detector_axis_index)

        self.update_offsets()

        # Set limits.
        self.max_pos = self.UIE_mcw_max_pos_in_qdsb.value()
        self.min_pos = self.UIE_mcw_min_pos_in_qdsb.value()
        self.fw_max_pos = self.UIE_mcw_fw_max_qdsb.value()
        self.fw_min_pos = self.UIE_mcw_fw_min_qdsb.value()
        self.smr_max_pos = self.UIE_mcw_smr_max_qdsb.value()
        self.smr_min_pos = self.UIE_mcw_smr_min_qdsb.value()
        self.sma_max_pos = self.UIE_mcw_sma_max_qdsb.value()
        self.sma_min_pos = self.UIE_mcw_sma_min_qdsb.value()
        self.smt_max_pos = self.UIE_mcw_smt_max_qdsb.value()
        self.smt_min_pos = self.UIE_mcw_smt_min_qdsb.value()
        self.dr_max_pos = self.UIE_mcw_dr_max_qdsb.value()
        self.dr_min_pos = self.UIE_mcw_dr_min_qdsb.value()

        if self.motion_controllers.main_drive_axis is not None:
            self.motion_controllers.main_drive_axis.set_limits(
                self.max_pos, self.min_pos)
        if self.motion_controllers.filter_wheel_axis is not None:
            self.motion_controllers.filter_wheel_axis.set_limits(
                self.fw_max_pos, self.fw_min_pos)
        if self.motion_controllers.sample_rotation_axis is not None:
            self.motion_controllers.sample_rotation_axis.set_limits(
                self.smr_max_pos, self.smr_min_pos)
        if self.motion_controllers.sample_angle_axis is not None:
            self.motion_controllers.sample_angle_axis.set_limits(
                self.sma_max_pos, self.sma_min_pos)
        if self.motion_controllers.sample_translation_axis is not None:
            self.motion_controllers.sample_translation_axis.set_limits(
                self.smt_max_pos, self.smt_min_pos)
        if self.motion_controllers.detector_rotation_axis is not None:
            self.motion_controllers.detector_rotation_axis.set_limits(
                self.dr_max_pos, self.dr_min_pos)

        self.update_movement_limits_gui()

        if self.motion_controllers.filter_wheel_axis is not None:
            self.motion_controllers.filter_wheel_axis.set_steps_per_value(
                self.UIE_mcw_fw_steps_per_rot_qdsb.value())
        if self.motion_controllers.sample_rotation_axis is not None:
            self.motion_controllers.sample_rotation_axis.set_steps_per_value(
                self.UIE_mcw_sm_steps_per_rot_qdsb.value())
        if self.motion_controllers.sample_angle_axis is not None:
            self.motion_controllers.sample_angle_axis.set_steps_per_value(
                self.UIE_mcw_sm_steps_per_ang_qdsb.value())
        if self.motion_controllers.sample_translation_axis is not None:
            self.motion_controllers.sample_translation_axis.set_steps_per_value(
                self.UIE_mcw_sm_steps_per_trans_qdsb.value())
        if self.motion_controllers.detector_rotation_axis is not None:
            self.motion_controllers.detector_rotation_axis.set_steps_per_value(
                self.UIE_mcw_dr_steps_per_qdsb.value())

        log.info('APPLIED GRAT DENSITY:', self.grating_density)
        if self.motion_controllers.main_drive_axis is not None:
            log.info('APPLIED STEPS PER NM:',
                     self.motion_controllers.main_drive_axis.get_steps_per_value())
        else:
            log.info(
                'APPLIED STEPS PER NM: Unable due to main_drive_axis being NoneType.')

        if self.motion_controllers.main_drive_axis is not None:
            log.debug('Main drive steps-per: %f' %
                      (self.motion_controllers.main_drive_axis.get_steps_per_value()))
        else:
            log.debug('Main drive axis is NoneType.')
        if self.motion_controllers.filter_wheel_axis is not None:
            log.debug('Filter wheel steps-per: %f' %
                      (self.motion_controllers.filter_wheel_axis.get_steps_per_value()))
        else:
            log.debug('Filter wheel axis is NoneType.')
        if self.motion_controllers.sample_rotation_axis is not None:
            log.debug('Sample rotation steps-per: %f' %
                      (self.motion_controllers.sample_rotation_axis.get_steps_per_value()))
        else:
            log.debug('Sample rotation axis is NoneType.')
        if self.motion_controllers.sample_angle_axis is not None:
            log.debug('Sample angle steps-per: %f' %
                      (self.motion_controllers.sample_angle_axis.get_steps_per_value()))
        else:
            log.debug('Sample angle axis is NoneType.')
        if self.motion_controllers.sample_translation_axis is not None:
            log.debug('Sample translation steps-per: %f' %
                      (self.motion_controllers.sample_translation_axis.get_steps_per_value()))
        else:
            log.debug('Sample translation axis is NoneType.')
        if self.motion_controllers.detector_rotation_axis is not None:
            log.debug('Detector rotation steps-per: %f' %
                      (self.motion_controllers.detector_rotation_axis.get_steps_per_value()))
        else:
            log.debug('Detector rotation axis is NoneType.')

        s = 0
        for i, dev in enumerate(self.mtn_ctrls):
            try:
                if dev is not None:
                    log.info('Device %d: %s' % (i-s, dev.short_name()))
                    log.info(
                        f'Setting home speed multiplier to {self.UIEL_mcw_home_speed_mults_qbsb[i-s].value()}')
                    dev.set_home_speed_mult(
                        self.UIEL_mcw_home_speed_mults_qbsb[i-s].value())
                    log.info(
                        f'Setting move speed multiplier to {self.UIEL_mcw_move_speed_mults_qbsb[i-s].value()}')
                    dev.set_move_speed_mult(
                        self.UIEL_mcw_move_speed_mults_qbsb[i-s].value())
                else:
                    log.info('Device %d: None' % (i-s))
                    s += 1
            except Exception as e:
                log.error(
                    f'Failed to set home/move speed multiplier for device {i-s}: {e}')
                continue

        self.machine_conf_win.close()

    def QMessageBoxYNC(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        log.info('QMessageBoxYNC:', title, msg)
        msgbox = QMessageBox()
        msgbox.setWindowTitle(title)
        msgbox.setText(msg)
        save_button = msgbox.addButton(
            QPushButton('Save'), QMessageBox.YesRole)
        msgbox.addButton(QPushButton("Don't Save"), QMessageBox.NoRole)
        msgbox.addButton(QPushButton('Cancel'), QMessageBox.RejectRole)
        msgbox.setDefaultButton(save_button)
        application.setQuitOnLastWindowClosed(True)
        retval = msgbox.exec()
        return retval

    def QMessageBoxQuestion(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        log.info('QMessageBoxInformation:', title, msg)
        retval = QMessageBox.question(self, title, msg,
                                      QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        application.setQuitOnLastWindowClosed(True)
        return retval

    def QMessageBoxInformation(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        log.info('QMessageBoxInformation:', title, msg)
        retval = QMessageBox.information(self, title, msg)
        application.setQuitOnLastWindowClosed(True)
        return retval

    def QMessageBoxWarning(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        log.warn('QMessageBoxWarning:', title, msg)
        retval = QMessageBox.warning(self, title, msg)
        application.setQuitOnLastWindowClosed(True)
        return retval

    def QMessageBoxCritical(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        log.error('QMessageBoxCritical:', title, msg)
        retval = QMessageBox.critical(self, title, msg)
        application.setQuitOnLastWindowClosed(True)
        return retval


# Main function.
if __name__ == '__main__':
    log.register()

    sys._excepthook = sys.excepthook

    def exception_hook(exctype, value, traceback):
        traceback_formatted = tb.format_exception(exctype, value, traceback)
        traceback_string = "".join(traceback_formatted)

        log.error('Exception caught by main hook.')
        log.error(traceback_string)
        log.error('Hooked exception complete.')
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)
    sys.excepthook = exception_hook

    try:
        application = QApplication(sys.argv)

        # Main GUI and child-window setup.
        ui_file_name = exeDir + '/ui/machine_config.ui'
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            log.fatal(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
            sys.exit(-1)

        ui_file_name = exeDir + '/ui/device_manager.ui'
        # workaround to load UI file with pyinstaller
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            log.fatal(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
            sys.exit(-1)

        ui_file_name = exeDir + '/ui/main_window.ui'
        # workaround to load UI file with pyinstaller
        ui_file = QFile(ui_file_name)
        if not ui_file.open(QIODevice.ReadOnly):
            log.fatal(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
            sys.exit(-1)

        exit_code = MMC_Main.EXIT_CODE_REBOOT
        while exit_code == MMC_Main.EXIT_CODE_REBOOT:
            exit_code = MMC_Main.EXIT_CODE_FINISHED

            # Initializes the GUI / Main GUI bootup.
            mainWindow = MMC_Main(application, ui_file)

            # Wait for the Qt loop to exit before exiting.
            exit_code = application.exec()  # block until

            # Cleanup.
            del mainWindow

    except Exception as e:
        log.error('A GLOBAL EXCEPTION HAS BEEN DETECTED:')
        log.error(e)

    log.info('Exiting program...')

    log.finish()

    os._exit(exit_code)
