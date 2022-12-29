#
# @file mmc.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief The MMC GUI and program.
# @version See Git tags for version information.
# @date 2022.08.03
# 
# @copyright Copyright (c) 2022
# 
#

# TODO: Change all instances of 'Color Wheel' to 'Filter Wheel'.
# TODO: Change 'Data Sampler' and 'Sampler' to 'Detector'.
# TODO: Other re-naming, such as 'mtn_ctrl' to 'motion_controller', etc.

""" 
UI Element Naming Scheme
------------------------
All UI elements should be named in the following format:
UIE_[window code]_[subsection code]_[Chosen Name]_[Q-type]

Device Manager Window       dmw_
Main GUI Window             mgw_
Machine Config. Window       mcw_

Main Drive                  md_
Color Wheel                 cw_
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


# %% OS and SYS Imports
import os
import sys

try:
    exeDir = sys._MEIPASS
except Exception:
    exeDir = os.getcwd()

if getattr(sys, 'frozen', False):
    appDir = os.path.dirname(sys.executable)
elif __file__:
    appDir = os.path.dirname(__file__)

# %% PyQt Imports
from PyQt5 import uic
from PyQt5.Qt import QTextOption
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ARG, QAbstractItemModel,
                          QFileInfo, qFuzzyCompare, QMetaObject, QModelIndex, QObject, Qt,
                          QThread, QTime, QUrl, QSize, QEvent, QCoreApplication, QFile, QIODevice, QMutex, QWaitCondition)
from PyQt5.QtGui import QColor, qGray, QImage, QPainter, QPalette, QIcon, QKeyEvent, QMouseEvent, QFontDatabase, QFont
from PyQt5.QtMultimedia import (QAbstractVideoBuffer, QMediaContent,
                                QMediaMetaData, QMediaPlayer, QMediaPlaylist, QVideoFrame, QVideoProbe)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QMainWindow, QDoubleSpinBox, QApplication, QComboBox, QDialog, QFileDialog,
                             QFormLayout, QHBoxLayout, QLabel, QListView, QMessageBox, QPushButton,
                             QSizePolicy, QSlider, QStyle, QToolButton, QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QPlainTextEdit,
                             QTableWidget, QTableWidgetItem, QSplitter, QAbstractItemView, QStyledItemDelegate, QHeaderView, QFrame, QProgressBar, QCheckBox, QToolTip, QGridLayout, QSpinBox,
                             QLCDNumber, QAbstractSpinBox, QStatusBar, QAction, QScrollArea, QSpacerItem)
from PyQt5.QtCore import QTimer
from PyQt5 import QtCore, QtWidgets

#%% More Standard Imports
import configparser as confp
from email.charset import QP
from time import sleep
import weakref
from io import TextIOWrapper
import math as m
import numpy as np
import datetime as dt
from functools import partial
# import serial.tools.list_ports
# from utilities import ports_finder

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# %% Custom Imports
from utilities.config import load_config, save_config, reset_config
import webbrowser
from utilities.datatable import DataTableWidget

import motion_controller_list as mcl
import middleware as mw
from middleware import MotionController#, list_all_devices
from middleware import DataSampler
from middleware import DevFinder

# %% Fonts
digital_7_italic_22 = None
digital_7_16 = None

# %% Classes
class NavigationToolbar(NavigationToolbar2QT):
    def edit_parameters(self):
        super(NavigationToolbar, self).edit_parameters()

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout = True)
        self.parent = weakref.proxy(parent)
        self.axes = fig.add_subplot(111)
        self.axes.set_xlabel('Position (nm)')
        self.axes.set_ylabel('Current (pA)')
        self.axes.grid()
        self.lines = dict()
        self.colors = ['b', 'r', 'k', 'c', 'g', 'm', 'tab:orange']
        self._tableClearCb = None
        super(MplCanvas, self).__init__(fig)

    def get_toolbar(self, parent) -> NavigationToolbar:
        self.toolbar = NavigationToolbar(self, parent)
        return self.toolbar

    def set_table_clear_cb(self, fcn):
        self._tableClearCb = fcn

    def clear_plot_fcn(self):
        if not self.parent.scanRunning:
            self.axes.cla()
            self.axes.set_xlabel('Location (nm)')
            self.axes.set_ylabel('Photo Current (pA)')
            self.axes.grid()
            self.draw()
            if self._tableClearCb is not None:
                self._tableClearCb()
        return

    def update_plots(self, data):
        self.axes.cla()
        self.axes.set_xlabel('Location (nm)')
        self.axes.set_ylabel('Photo Current (pA)')
        for row in data:
            c = self.colors[row[-1] % len(self.colors)]
            self.lines[row[-1]], = self.axes.plot(row[0], row[1], label=row[2], color = c)
        self.axes.legend()
        self.axes.grid()
        self.draw()
        return

    def append_plot(self, idx, xdata, ydata):
        if idx not in self.lines.keys():
            c = self.colors[idx % len(self.colors)]
            self.lines[idx], = self.axes.plot(xdata, ydata, label = 'Scan #%d'%(idx), color = c)
        else:
            self.lines[idx].set_data(xdata, ydata)
        self.draw()

# Forward declaration of Scan class.
class Scan(QThread):
    pass

# The main MMC program and GUI class.
class MMC_Main(QMainWindow):
    # STARTUP PROCEDURE
    # 
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
        if self.samplers is not None:
            del self.samplers
        if self.dev_finder is not None:
            self.dev_finder.done = True
            del self.dev_finder

    # Constructor
    def __init__(self, application, uiresource = None):
        # Handles the initial showing of the UI.
        self.application: QApplication = application
        self._startup_args = self.application.arguments()
        super(MMC_Main, self).__init__()
        uic.loadUi(uiresource, self)
        self.SIGNAL_device_manager_ready.connect(self.connect_devices)
        self.SIGNAL_devices_connection_check.connect(self.devices_connection_check)

        self.dev_man_win_enabled = False
        self.main_gui_booted = False
        self.dmw = None
        self.show_window_device_manager()
        self.dev_finder = None

        self.motion_controllers = mcl.MotionControllerList()

        # TODO: These indices will keep track of which drives correspond to which controllers.
        self.main_drive_i = 0

    # Screen shown during startup to disable premature user interaction as well as handle device-not-found issues.
    def show_window_device_manager(self):
        self.device_timer = None
        if self.dmw is None:
            ui_file_name = exeDir + '/ui/device_manager.ui'
            ui_file = QFile(ui_file_name)
            if not ui_file.open(QIODevice.ReadOnly):
                print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
                raise RuntimeError('Could not load grating input UI file')

            self.dmw = QDialog(self) # pass parent window
            uic.loadUi(ui_file, self.dmw)

            self.dmw.setWindowTitle('Device Manager')

            self.UIE_dmw_explanation_ql: QLabel = self.dmw.findChild(QLabel, "dmw_explanation_ql")
            
            self.UIE_dmw_list_ql: QLabel = self.dmw.findChild(QLabel, "devices_label")

            self.UIEL_dmw_sampler_qhbl = []
            self.UIEL_dmw_sampler_qhbl.append(self.dmw.findChild(QHBoxLayout, "sampler_combo_sublayout"))

            self.UIEL_dmw_mtn_ctrl_qhbl = []
            self.UIEL_dmw_mtn_ctrl_qhbl.append(self.dmw.findChild(QHBoxLayout, "mtn_ctrl_combo_sublayout"))

            self.UIEL_dmw_sampler_qcb = []
            self.UIEL_dmw_sampler_qcb.append(self.dmw.findChild(QComboBox, "samp_combo"))
            self.UIEL_dmw_sampler_qcb[0].addItem("Auto-Connect")
            self.UIEL_dmw_sampler_model_qcb = []
            self.UIEL_dmw_sampler_model_qcb.append(self.dmw.findChild(QComboBox, "samp_model_combo"))
            for device in DataSampler.SupportedDevices:
                self.UIEL_dmw_sampler_model_qcb[0].addItem(device)

            self.UIEL_dmw_mtn_ctrl_qcb = []
            self.UIEL_dmw_mtn_ctrl_qcb.append(self.dmw.findChild(QComboBox, "mtn_combo"))
            self.UIEL_dmw_mtn_ctrl_qcb[0].addItem("Auto-Connect")
            self.UIEL_dmw_mtn_ctrl_model_qcb = []
            self.UIEL_dmw_mtn_ctrl_model_qcb.append(self.dmw.findChild(QComboBox, "mtn_model_combo"))
            for device in MotionController.SupportedDevices:
                self.UIEL_dmw_mtn_ctrl_model_qcb[0].addItem(device)

            self.UIE_dmw_accept_qpb: QPushButton = self.dmw.findChild(QPushButton, "acc_button")
            self.UIE_dmw_accept_qpb.clicked.connect(self.connect_devices)
            self.UIE_dmw_dummy_qckbx: QCheckBox = self.dmw.findChild(QCheckBox, "dum_checkbox")
            self.UIE_dmw_dummy_qckbx.setChecked(len(self._startup_args) == 2)

            self.UIE_dmw_num_samplers_qsb: QSpinBox = self.dmw.findChild(QSpinBox, "num_samplers")
            self.UIE_dmw_num_samplers_qsb.valueChanged.connect(self.update_num_samplers_ui)
            self.num_samplers = 1

            self.UIE_dmw_num_motion_controllers_qsb: QSpinBox = self.dmw.findChild(QSpinBox, "num_motion_controllers")
            self.UIE_dmw_num_motion_controllers_qsb.valueChanged.connect(self.update_num_motion_controllers_ui)
            self.num_motion_controllers = 1

            self.UIE_dmw_sampler_combo_qvbl: QVBoxLayout = self.dmw.findChild(QVBoxLayout, "sampler_combo_layout")
            self.UIE_dmw_mtn_ctrl_combo_qvbl: QVBoxLayout = self.dmw.findChild(QVBoxLayout, "mtn_ctrl_combo_layout")

            self.dmw.show()

        self.application.processEvents()
        self.SIGNAL_device_manager_ready.emit()

    def update_num_samplers_ui(self):
        if self.num_samplers != self.UIE_dmw_num_samplers_qsb.value():
            self.num_samplers = self.UIE_dmw_num_samplers_qsb.value()
            for widget in self.UIEL_dmw_sampler_qcb:
                widget.setParent(None)
            for widget in self.UIEL_dmw_sampler_model_qcb:
                widget.setParent(None)
            for layout in self.UIEL_dmw_sampler_qhbl:
                self.UIE_dmw_sampler_combo_qvbl.removeItem(layout)

            self.UIEL_dmw_sampler_qcb = []
            self.UIEL_dmw_sampler_model_qcb = []
            self.UIEL_dmw_sampler_qhbl = []

            for i in range(self.num_samplers):
                s_combo = QComboBox()
                s_combo.addItem("Auto-Connect")
                for dev in self.dev_list:
                    s_combo.addItem('%s'%(dev))
                m_combo = QComboBox()
                for device in DataSampler.SupportedDevices:
                    m_combo.addItem(device)
                layout = QHBoxLayout()
                layout.addWidget(s_combo)
                layout.addStretch(4)
                layout.addWidget(m_combo)
                layout.addStretch(1)
                self.UIE_dmw_sampler_combo_qvbl.addLayout(layout)
                self.UIEL_dmw_sampler_qcb.append(s_combo)
                self.UIEL_dmw_sampler_model_qcb.append(m_combo)
                self.UIEL_dmw_sampler_qhbl.append(layout)

        print('new samplers combo list len: %d'%(len(self.UIEL_dmw_sampler_qcb)))

    def update_num_motion_controllers_ui(self):
        if self.num_motion_controllers != self.UIE_dmw_num_motion_controllers_qsb.value():
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
                s_combo.addItem("Auto-Connect")
                for dev in self.dev_list:
                    s_combo.addItem('%s'%(dev))
                m_combo = QComboBox()
                for device in MotionController.SupportedDevices:
                    m_combo.addItem(device)
                layout = QHBoxLayout()
                layout.addWidget(s_combo)
                layout.addStretch(4)
                layout.addWidget(m_combo)
                layout.addStretch(1)
                self.UIE_dmw_mtn_ctrl_combo_qvbl.addLayout(layout)
                self.UIEL_dmw_mtn_ctrl_qcb.append(s_combo)
                self.UIEL_dmw_mtn_ctrl_model_qcb.append(m_combo)
                self.UIEL_dmw_mtn_ctrl_qhbl.append(layout)

        print('new mtn ctrls combo list len: %d'%(len(self.UIEL_dmw_mtn_ctrl_qcb)))

    def connect_devices(self):
        print('\n\n')
        print("connect_devices")

        self.UIE_dmw_explanation_ql.setText("Attempting to connect...")
        self.application.processEvents()

        dummy = self.UIE_dmw_dummy_qckbx.isChecked()
        print("Dummy Mode: " + str(dummy))

        # Motion Controller and Sampler initialization.
        # Note that, for now, the Keithley 6485 and KST101 are the defaults.
        samplers_connected = [False] * self.num_samplers
        mtn_ctrls_connected = [False] * self.num_motion_controllers

        self.samplers = [None] * self.num_samplers
        self.mtn_ctrls = [None] * self.num_motion_controllers

        print('Samplers: %d'%(self.num_samplers))
        print('Motion controllers: %d'%(self.num_motion_controllers))

        # TODO: Re-instate some sort of auto-connect.

        for i in range(self.num_samplers):
            print('Instantiation attempt for sampler #%d.'%(i))
            try:
                if self.UIEL_dmw_sampler_qcb[i].currentIndex() != 0:
                    print("Using manual port: %s"%(self.UIEL_dmw_sampler_qcb[i].currentText().split(' ')[0]))
                    self.samplers[i] = DataSampler(dummy, self.UIEL_dmw_sampler_model_qcb[i].currentText(), self.UIEL_dmw_sampler_qcb[i].currentText().split(' ')[0])
                else:
                    # Auto-Connect
                    # self.samplers[i] = DataSampler(dummy, DataSampler.SupportedDevices[0])
                    print('currentIndex', self.UIEL_dmw_sampler_qcb[i].currentIndex(), self.UIEL_dmw_sampler_qcb[i].currentText())
                    print(len(self.UIEL_dmw_sampler_qcb))
                    print('AUTO-CONNECT CURRENTLY DISABLED!')

            except Exception as e:
                print(e)
                print("Failed to find sampler (%s)."%(e))
                self.samplers[i] = None
                samplers_connected[i] = False
            if self.samplers[i] is None:
                samplers_connected[i] = False
            else:
                samplers_connected[i] = True

        # for i, combo in self.dm_sampler_combos:
        for i in range(self.num_motion_controllers):
            print('Instantiation attempt for motion controller #%d.'%(i))
            try:
                if self.UIEL_dmw_mtn_ctrl_qcb[i].currentIndex() != 0:
                    print("Using manual port: %s"%(self.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0]))
                    self.mtn_ctrls[i] = MotionController(dummy, self.UIEL_dmw_mtn_ctrl_model_qcb[i].currentText(), self.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0])
                # else:
                #     # Auto-Connect
                #     self.mtn_ctrls[i] = MotionController(dummy, MotionController.SupportedDevices[0])

            except Exception as e:
                print("Failed to find motion controller (%s)."%(e))
                self.mtn_ctrls[i] = None
                mtn_ctrls_connected[i] = False
                pass
            if self.mtn_ctrls[i] is None:
                mtn_ctrls_connected[i] = False
            else:
                mtn_ctrls_connected[i] = True

        # Emits a success or fail or whatever signals here so that device manager can react accordingly. If successes, then just boot the GUI. If failure then the device manager needs to allow the selection of device(s).
        
        self.SIGNAL_devices_connection_check.emit(dummy, samplers_connected, mtn_ctrls_connected)

    # If things are connected, boot main GUI.
    # If somethings wrong, enable advanced dev man functions.
    def devices_connection_check(self, dummy: bool, samplers: list, mtn_ctrls: list):
        connected = True
        for status in samplers:
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
                print('WARNING: STOPPING DEVICE TIMER!')
                self.device_timer.stop()
            self.dmw.close()
            self._show_main_gui(dummy)
            return
        
        # If we are here, then we have not automatically connected to all required devices. We must now enable the device manager.
        if not self.dev_man_win_enabled:
            self.dev_man_win_enabled = True
            self.device_timer = QTimer()
            self.device_timer.timeout.connect(self.devman_list_devices)
            self.device_timer.start(1000)
        self.UIE_dmw_explanation_ql.setText('Auto-connect failed.')   

    def _show_main_gui(self, dummy: bool):
        # Set this via the QMenu QAction Edit->Change Auto-log Directory
        self.data_save_directory = os.path.expanduser('~/Documents')
        self.data_save_directory += '/mcpherson_mmc/%s/'%(dt.datetime.now().strftime('%Y%m%d'))
        if not os.path.exists(self.data_save_directory):
            os.makedirs(self.data_save_directory)

        self.plotCanvas = None

        self.num_scans = 0
        self.previous_position = -9999
        self.immobile_count = 0

        self.mes_sign = 1
        self.autosave_data_bool = False
        self.pop_out_table = False
        self.pop_out_plot = False
        self.moving = False
        self.scanRunning = False

        self.machine_conf_win: QDialog = None
        self.grating_conf_win: QDialog = None
        self.grating_density_in: QDoubleSpinBox = None
        self.UIE_mcw_diff_order_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_max_pos_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_min_pos_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_zero_ofst_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_arm_length_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_incidence_ang_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_tangent_ang_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_machine_conf_qpb: QPushButton = None

        self.grating_combo_lstr = ['1200', '2400', '* New Entry']
        self.current_grating_idx = 0

        # Default grating equation values.
        self.arm_length = 56.53654 # mm
        self.diff_order = 1
        self.max_pos = 600.0
        self.min_pos = -40.0
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx]) # grooves/mm
        self.tangent_ang = 0 # deg
        self.incidence_ang = 32 # deg
        self.zero_ofst = 37.8461 # nm

        # Replaces default grating equation values with the values found in the config.ini file.
        try:
            load_dict = load_config(appDir)
        except Exception as e:
            print("The following exception occurred while attempting to load configuration file: %s"%(e))
            try:
                reset_config(appDir)
                load_dict = load_config(appDir)
            except Exception as e2:
                print("Configuration file recovery failed (exception: %s). Unable to load configuration file. Exiting."%(e2))
                exit(43)
        self.mes_sign = load_dict['measurementSign']
        self.autosave_data_bool = load_dict['autosaveData']
        self.data_save_directory = load_dict['dataSaveDirectory']
        self.grating_combo_lstr = load_dict["gratingDensities"]
        self.current_grating_idx = load_dict["gratingDensityIndex"]
        self.diff_order = load_dict["diffractionOrder"]
        self.zero_ofst = load_dict["zeroOffset"]
        self.incidence_ang = load_dict["incidenceAngle"]
        self.tangent_ang = load_dict["tangentAngle"]
        self.arm_length = load_dict["armLength"]
        self.max_pos = load_dict["maxPosition"]
        self.min_pos = load_dict["minPosition"]
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx])

        # Sets the conversion slope based on the found (or default) values.
        self.calculate_conversion_slope()

        print('\n\nConversion constant: %f\n'%(self.conversion_slope))

        self.manual_position = 0 # 0 nm
        self.startpos = 0
        self.stoppos = 0
        self.steppos = 0.1

        if dummy:
            self.setWindowTitle("McPherson Monochromator Control (Debug Mode) v0.5")
        else:
            self.setWindowTitle("McPherson Monochromator Control (Hardware Mode) v0.5")

        self.is_conv_set = False # Use this flag to set conversion

        # GUI initialization, gets the UI elements from the .ui file.
        self.UIE_mgw_scan_qpb: QPushButton = self.findChild(QPushButton, "begin_scan_button") # Scanning Control 'Begin Scan' Button
        pixmapi = getattr(QStyle, 'SP_ArrowForward')
        icon = self.style().standardIcon(pixmapi)
        self.UIE_mgw_scan_qpb.setIcon(icon)
        self.UIE_mgw_stop_scan_qpb: QPushButton = self.findChild(QPushButton, "stop_scan_button")
        pixmapi = getattr(QStyle, 'SP_BrowserStop')
        icon = self.style().standardIcon(pixmapi)
        self.UIE_mgw_stop_scan_qpb.setIcon(icon)
        self.UIE_mgw_stop_scan_qpb.setEnabled(False)
        self.UIE_mgw_save_data_qckbx: QCheckBox = self.findChild(QCheckBox, "save_data_checkbox") # Scanning Control 'Save Data' Checkbox
        self.UIE_mgw_dir_box_qle = self.findChild(QLineEdit, "save_dir_lineedit")
        self.UIE_mgw_start_qdsb = self.findChild(QDoubleSpinBox, "start_set_spinbox")
        self.UIE_mgw_stop_qdsb = self.findChild(QDoubleSpinBox, "end_set_spinbox")

        if dummy:
            self.UIE_mgw_stop_qdsb.setValue(0.2)

        self.UIE_mgw_step_qdsb = self.findChild(QDoubleSpinBox, "step_set_spinbox")
        self.UIE_mgw_currpos_nm_disp_ql = self.findChild(QLabel, "currpos_nm")
        self.UIE_mgw_scan_status_ql = self.findChild(QLabel, "status_label")
        self.UIE_mgw_scan_qpbar = self.findChild(QProgressBar, "progressbar")
        UIE_mgw_save_config_qpb: QPushButton = self.findChild(QPushButton, 'save_config_button')
        self.UIE_mgw_pos_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, "pos_set_spinbox") # Manual Control 'Position:' Spin Box
        self.UIE_mgw_move_to_position_qpb: QPushButton = self.findChild(QPushButton, "move_pos_button")
        self.UIE_mgw_plot_frame_qw: QWidget = self.findChild(QWidget, "data_graph")
        self.UIE_mgw_xmin_in_qle: QLineEdit = self.findChild(QLineEdit, "xmin_in")
        self.UIE_mgw_ymin_in_qle: QLineEdit = self.findChild(QLineEdit, "ymin_in")
        self.UIE_mgw_xmax_in_qle: QLineEdit = self.findChild(QLineEdit, "xmax_in")
        self.UIE_mgw_ymax_in_qle: QLineEdit = self.findChild(QLineEdit, "ymax_in")
        self.UIE_mgw_plot_autorange_qckbx: QCheckBox = self.findChild(QCheckBox, "autorange_checkbox")
        self.UIE_mgw_plot_clear_plots_qpb: QPushButton = self.findChild(QPushButton, "clear_plots_button")

        self.UIE_mgw_machine_conf_qa: QAction = self.findChild(QAction, "machine_configuration")
        self.UIE_mgw_invert_mes_qa: QAction = self.findChild(QAction, "invert_mes")
        self.UIE_mgw_autosave_data_qa: QAction = self.findChild(QAction, "autosave_data")
        self.UIE_mgw_autosave_dir_qa: QAction = self.findChild(QAction, "autosave_dir_prompt")
        self.UIE_mgw_preferences_qa: QAction = self.findChild(QAction, "preferences")
        self.UIE_mgw_pop_out_table_qa: QAction = self.findChild(QAction, "pop_out_table")
        self.UIE_mgw_pop_out_plot_qa: QAction = self.findChild(QAction, "pop_out_plot")
        self.UIE_mgw_about_source_qa: QAction = self.findChild(QAction, "actionSource_Code")
        self.UIE_mgw_about_licensing_qa: QAction = self.findChild(QAction, "actionLicensing")
        self.UIE_mgw_about_manual_qa: QAction = self.findChild(QAction, "actionManual_2")

        self.UIE_mgw_save_data_qpb: QPushButton = self.findChild(QPushButton, 'save_data_button')
        self.UIE_mgw_save_data_qpb.clicked.connect(self.save_data_cb)
        self.UIE_mgw_delete_data_qpb: QPushButton = self.findChild(QPushButton, 'delete_data_button')
        self.UIE_mgw_delete_data_qpb.clicked.connect(self.delete_data_cb)
        
        UIE_mgw_table_qf: QFrame = self.findChild(QFrame, "table_frame")
        self.table = DataTableWidget(self)
        VLayout = QVBoxLayout()
        VLayout.addWidget(self.table)
        UIE_mgw_table_qf.setLayout(VLayout)
        self.UIE_mgw_home_qpb: QPushButton = self.findChild(QPushButton, "home_button")
        
        self.motion_controllers.main_drive_axis = self.mtn_ctrls[0]

        self.homing_started = False
        if not dummy:
            self.homing_started = True
            self.disable_movement_sensitive_buttons(True)
            self.scan_status_update("HOMING")
            # self.mtn_ctrls[self.main_drive_i].home()
            self.motion_controllers.main_drive_axis.home()

        # Get and set the palette.
        palette = self.UIE_mgw_currpos_nm_disp_ql.palette()
        palette.setColor(palette.WindowText, QColor(255, 0, 0))
        palette.setColor(palette.Background, QColor(0, 170, 255))
        palette.setColor(palette.Light, QColor(80, 80, 255))
        palette.setColor(palette.Dark, QColor(0, 255, 0))
        self.UIE_mgw_currpos_nm_disp_ql.setPalette(palette)

        self.plotCanvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.plotCanvas.clear_plot_fcn()
        self.plotCanvas.set_table_clear_cb(self.table.plotsClearedCb)
        toolbar = self.plotCanvas.get_toolbar(self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self.plotCanvas)
        self.UIE_mgw_plot_frame_qw.setLayout(layout)

        self.UIE_mgw_plot_clear_plots_qpb.clicked.connect(self.plotCanvas.clear_plot_fcn)

        # Set the initial value of the Manual Control 'Position:' spin box.
        self.UIE_mgw_pos_qdsb.setValue(0)

        # Signal-to-slot connections.
        UIE_mgw_save_config_qpb.clicked.connect(self.show_window_machine_config)
        self.UIE_mgw_scan_qpb.clicked.connect(self.scan_button_pressed)
        self.UIE_mgw_stop_scan_qpb.clicked.connect(self.stop_scan_button_pressed)
        # self.collect_data.clicked.connect(self.manual_collect_button_pressed)
        self.UIE_mgw_move_to_position_qpb.clicked.connect(self.move_to_position_button_pressed)
        self.UIE_mgw_start_qdsb.valueChanged.connect(self.start_changed)
        self.UIE_mgw_stop_qdsb.valueChanged.connect(self.stop_changed)
        self.UIE_mgw_step_qdsb.valueChanged.connect(self.step_changed)
        self.UIE_mgw_pos_qdsb.valueChanged.connect(self.manual_pos_changed)

        self.UIE_mgw_machine_conf_qa.triggered.connect(self.show_window_machine_config)
        self.UIE_mgw_invert_mes_qa.toggled.connect(self.invert_mes_toggled)
        self.UIE_mgw_autosave_data_qa.toggled.connect(self.autosave_data_toggled)
        self.UIE_mgw_autosave_dir_qa.triggered.connect(self.autosave_dir_triggered)
        self.UIE_mgw_preferences_qa.triggered.connect(self.preferences_triggered)
        self.UIE_mgw_pop_out_table_qa.toggled.connect(self.pop_out_table_toggled)
        self.UIE_mgw_pop_out_plot_qa.toggled.connect(self.pop_out_plot_toggled)
        self.UIE_mgw_about_licensing_qa.triggered.connect(self.open_licensing_hyperlink)
        self.UIE_mgw_about_manual_qa.triggered.connect(self.open_manual_hyperlink)
        self.UIE_mgw_about_source_qa.triggered.connect(self.open_source_hyperlink)

        self.UIE_mgw_home_qpb.clicked.connect(self.manual_home)

        # Other stuff.
        self.scan = Scan(weakref.proxy(self))

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position_displays)
        self.timer.start(100)

        # Set up the status bar.
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.sb_grating_density: QLabel = QLabel()
        self.sb_zero_offset: QLabel = QLabel()
        self.sb_inc_ang: QLabel = QLabel()
        self.sb_tan_ang: QLabel = QLabel()
        self.sb_arm_len: QLabel = QLabel()
        self.sb_diff_order: QLabel = QLabel()
        self.sb_conv_slope: QLabel = QLabel()
        self.statusBar.addPermanentWidget(self.sb_grating_density)
        self.statusBar.addPermanentWidget(self.sb_zero_offset)
        self.statusBar.addPermanentWidget(self.sb_inc_ang)
        self.statusBar.addPermanentWidget(self.sb_tan_ang)
        self.statusBar.addPermanentWidget(self.sb_arm_len)
        self.statusBar.addPermanentWidget(self.sb_diff_order)
        self.statusBar.addPermanentWidget(self.sb_conv_slope)
        self.update_status_bar_grating_equation_values()

        self.manual_position = (self.UIE_mgw_pos_qdsb.value() + self.zero_ofst) * self.conversion_slope
        self.startpos = (self.UIE_mgw_start_qdsb.value() + self.zero_ofst) * self.conversion_slope
        self.stoppos = (self.UIE_mgw_stop_qdsb.value() + self.zero_ofst) * self.conversion_slope

        self.UIE_mgw_cw_mancon_position_set_qsb: QSpinBox = self.findChild(QSpinBox, 'color_wheel_pos_set_spinbox')
        self.UIE_mgw_cw_mancon_move_pos_qpb: QPushButton = self.findChild(QPushButton, 'color_wheel_move_pos_button')
        self.UIE_mgw_cw_mancon_home_qpb: QPushButton = self.findChild(QPushButton, 'color_wheel_home_button')
        self.UIE_mgw_cw_add_rule_qpb: QPushButton = self.findChild(QPushButton, 'color_wheel_add_rule_button')
        self.UIE_mgw_cw_add_rule_qpb.clicked.connect(self.new_color_wheel_rule)
        
        self.cw_rules = [] # List to hold the actual rules.
        self.UIEL_mgw_cw_rules_qvbl = []
        # self.UIEL_mgw_cw_rules_qvbl.append(self.scroll_area_layout)
        self.UIEL_mgw_cw_rules_set_qdsb = []
        # self.UIEL_mgw_cw_rules_set_qdsb.append(self.findChild(QDoubleSpinBox, 'color_wheel_rule_set_spinbox'))
        self.UIEL_mgw_cw_rules_step_qsb = []
        # self.UIEL_mgw_cw_rules_step_qsb.append(self.findChild(QSpinBox, 'color_wheel_rule_step_spinbox'))
        self.UIEL_mgw_cw_rules_remove_qpb = []
        # self.UIEL_mgw_cw_rules_remove_qpb.append(self.findChild(QPushButton, 'color_wheel_remove_rule_button'))
        # self.UIEL_mgw_cw_rules_remove_qpb[0].clicked.connect(partial(self.del_color_wheel_rule, 0))
        self.UIEL_mgw_cw_rules_enact_qpb = []
        # self.UIEL_mgw_cw_rules_enact_qpb.append(self.findChild(QPushButton, 'color_wheel_enact_rule_button'))
        self.UIE_mgw_cw_rules_qsa: QVBoxLayout = self.findChild(QVBoxLayout, 'scroll_area_layout')
        self.UIEL_mgw_cw_misc_tuples_ql = []
        # self.UIEL_mgw_cw_misc_tuples_ql.append([self.label_4, self.label_5])
        self.new_color_wheel_rule()

        if self.mes_sign == -1:
            self.UIE_mgw_invert_mes_qa.setChecked(True)
        else:
            self.UIE_mgw_invert_mes_qa.setChecked(False)

        if self.autosave_data_bool:
            self.UIE_mgw_autosave_data_qa.setChecked(True)
        else:
            self.UIE_mgw_autosave_data_qa.setChecked(False)

        self.update_movement_limits()

        self.table.updatePlots()

        self.dmw.close()
        self.main_gui_booted = True
        self.show()  

    def new_color_wheel_rule(self):
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
        self.UIEL_mgw_cw_rules_enact_qpb.append(enact_button)

        remove_button: QPushButton = QPushButton('-')
        remove_button.setMaximumWidth(29)
        remove_button.setMaximumHeight(29)
        self.UIEL_mgw_cw_rules_remove_qpb.append(remove_button)
        remove_button.clicked.connect(partial(self.del_color_wheel_rule, self.UIEL_mgw_cw_rules_enact_qpb[-1]))
        print('RULE ADDED AT INDEX:', len(self.UIEL_mgw_cw_rules_remove_qpb) - 1)

        rule_set_spinbox: QDoubleSpinBox = QDoubleSpinBox()
        rule_set_spinbox.setRange(0, 9999)
        rule_set_spinbox.setDecimals(2)
        rule_set_spinbox.setMaximumWidth(89)
        rule_set_spinbox.setMaximumHeight(27)
        self.UIEL_mgw_cw_rules_set_qdsb.append(rule_set_spinbox)

        rule_step_spinbox: QSpinBox = QSpinBox()
        rule_step_spinbox.setRange(0, 9999999)
        rule_step_spinbox.setMaximumWidth(84)
        rule_step_spinbox.setMaximumHeight(27)
        self.UIEL_mgw_cw_rules_step_qsb.append(rule_step_spinbox)

        hspacer: QSpacerItem = QSpacerItem(20, 40, QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QHBoxLayout()
        layout.addWidget(geq_label)
        layout.addWidget(rule_set_spinbox)
        layout.addWidget(goto_label)
        layout.addWidget(rule_step_spinbox)
        layout.addWidget(enact_button)
        layout.addItem(hspacer)
        layout.addWidget(remove_button)

        print(layout.spacing())

        self.UIEL_mgw_cw_misc_tuples_ql.append([geq_label, goto_label])

        self.UIEL_mgw_cw_rules_qvbl.append(layout)
        self.UIE_mgw_cw_rules_qsa.addLayout(layout)
    
    def enact_filter_wheel_rule(self):
        sender = self.sender()
        sidx = -1
        for i in range(len(self.UIEL_mgw_cw_rules_enact_qpb)):
            if self.UIEL_mgw_cw_rules_enact_qpb[i] == sender:
                sidx = i
                break
        if sidx < 0:
            print('FAILED TO FIND SENDER INDEX!')
            return

        # sender.
        print('SENDER:')
        print(sender)

        dspin = self.UIEL_mgw_cw_rules_set_qdsb[sidx]
        spin = self.UIEL_mgw_cw_rules_step_qsb[sidx]

        print(dspin)
        print(spin)
        print('Values are %f and %d.'%(dspin.value(), spin.value()))

    def del_color_wheel_rule(self, index_finder):
        # TODO: Currently an issue where if a lower index is removed first, then the higher index remains the same.

        index = self.UIEL_mgw_cw_rules_enact_qpb.index(index_finder)

        # button_index tells is which button it is
        print('RULE REMOVAL AT INDEX:', index)

        # self.UIEL_mgw_cw_rules_qvbl[index].removeWidget(self.UIEL_mgw_cw_rules_enact_qpb[index])
        self.UIEL_mgw_cw_rules_enact_qpb[index].setParent(None)
        del self.UIEL_mgw_cw_rules_enact_qpb[index]

        # self.UIEL_mgw_cw_rules_qvbl[index].removeWidget(self.UIEL_mgw_cw_rules_remove_qpb[index])
        print('len', len(self.UIEL_mgw_cw_rules_remove_qpb))
        print('index', index)
        self.UIEL_mgw_cw_rules_remove_qpb[index].setParent(None)
        del self.UIEL_mgw_cw_rules_remove_qpb[index]

        # self.UIEL_mgw_cw_rules_qvbl[index].removeWidget(self.UIEL_mgw_cw_rules_set_qdsb[index])
        self.UIEL_mgw_cw_rules_set_qdsb[index].setParent(None)
        del self.UIEL_mgw_cw_rules_set_qdsb[index]

        # self.UIEL_mgw_cw_rules_qvbl[index].removeWidget(self.UIEL_mgw_cw_rules_step_qsb[index])
        self.UIEL_mgw_cw_rules_step_qsb[index].setParent(None)
        del self.UIEL_mgw_cw_rules_step_qsb[index]

        # self.UIEL_mgw_cw_rules_qvbl[index].removeWidget(self.UIEL_mgw_cw_misc_tuples_ql[index][0])
        # self.UIEL_mgw_cw_rules_qvbl[index].removeWidget(self.UIEL_mgw_cw_misc_tuples_ql[index][1])

        self.UIEL_mgw_cw_misc_tuples_ql[index][0].setParent(None)
        self.UIEL_mgw_cw_misc_tuples_ql[index][1].setParent(None)
        del self.UIEL_mgw_cw_misc_tuples_ql[index]

        # self.UIEL_mgw_cw_rules_qvbl[index].removeWidget(self.UIEL_mgw_cw_misc_tuples_ql[index][2])
        # del self.UIEL_mgw_cw_rules_qvbl[index]
        
        self.UIE_mgw_cw_rules_qsa.removeItem(self.UIEL_mgw_cw_rules_qvbl[index])
        del self.UIEL_mgw_cw_rules_qvbl[index]

    def devman_list_devices(self):
        # self.dev_list = ports_finder.find_all_ports()
        # if self.dev_finder is None:
            # self.dev_finder = DevFinder()
        # self.dev_list = self.dev_finder.get_dev_list()
        self.dev_list = mw.find_all_ports()

        dev_list_str = ''
        for dev in self.dev_list:
            dev_list_str += '%s\n'%(dev)

        if (self.UIE_dmw_list_ql.text() != "~DEVICE LIST~\n" + dev_list_str):
            for i in range(self.num_samplers):
                self.UIEL_dmw_sampler_qcb[i].clear()
                self.UIEL_dmw_sampler_qcb[i].addItem('Auto-Connect')
                self.UIEL_dmw_sampler_qcb[i].setCurrentIndex(0)

                for dev in self.dev_list:
                    self.UIEL_dmw_sampler_qcb[i].addItem('%s'%(dev))

            for i in range(self.num_motion_controllers):
                self.UIEL_dmw_mtn_ctrl_qcb[i].clear()
                self.UIEL_dmw_mtn_ctrl_qcb[i].addItem('Auto-Connect')
                self.UIEL_dmw_mtn_ctrl_qcb[i].setCurrentIndex(0)

                for dev in self.dev_list:
                    self.UIEL_dmw_mtn_ctrl_qcb[i].addItem('%s'%(dev))

            self.UIE_dmw_list_ql.setText("~DEVICE LIST~\n" + dev_list_str)

    def save_data_cb(self):
        if self.table is None:
            return
        data, metadata = self.table.saveDataCb()
        print(data, metadata)
        if data is None:
            return
        if metadata is not None:
            try:
                tstamp = metadata['tstamp']
                scan_id = metadata['scan_id']
            except Exception:
                tstamp = dt.datetime.now()
                scan_id = 100
        savFileName, _ = QFileDialog.getSaveFileName(self, "Save CSV", directory=os.path.expanduser('~/Documents') + '/mcpherson_mmc/%s_%d.csv'%(tstamp.strftime('%Y%m%d%H%M%S'), scan_id), filter='*.csv')
        fileInfo = QFileInfo(savFileName)
        try:
            ofile = open(fileInfo.absoluteFilePath(), 'w', encoding='utf-8')
        except Exception:
            print('Could not open file %s'%(fileInfo.fileName()))
            return
        ofile.write('# %s\n'%(tstamp.strftime('%Y-%m-%d %H:%M:%S')))
        try:
            ofile.write('# Steps/mm: %f\n'%(metadata['mm_to_idx']))
        except Exception:
            pass
        try:
            ofile.write('# mm/nm: %e; '%(metadata['mm_per_nm']))
        except Exception:
            pass
        try:
            ofile.write('lambda_0 (nm): %.4f\n'%(metadata['zero_ofst']))
        except Exception:
            pass
        ofile.write('# Position (nm),Mean Current(A)\n')
        xdata = data['x']
        ydata = data['y']
        for i in range(len(xdata)):
            try:
                ofile.write('%e, %e\n'%(xdata[i], ydata[i]))
            except Exception:
                continue
        ofile.close()

    def delete_data_cb(self):
        self.table.delDataCb()
        return

    def open_manual_hyperlink(self):
        webbrowser.open('https://github.com/mitbailey/MMC')

    def open_source_hyperlink(self):
        webbrowser.open('https://github.com/mitbailey/MMC')

    def open_licensing_hyperlink(self):
        webbrowser.open('https://github.com/mitbailey/MMC')

    def disable_movement_sensitive_buttons(self, disable: bool):
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

    def manual_home(self):
        self.scan_status_update("HOMING")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        # self.mtn_ctrls[self.main_drive_i].home()
        self.motion_controllers.main_drive_axis.home()

    def table_log(self, data, scan_type: str, start: float, stop: float = -1, step: float = -1, data_points: int = 1):
        self.scan_number += 1

        if scan_type == 'Automatic':
            row_pos = 0
            if self.table_has_manual_entry:
                row_pos = 1
            self.table.insertRow(row_pos)
            self.table.setItem(row_pos, 0, QTableWidgetItem(str(self.scan_number)))
            self.table.setItem(row_pos, 1, QTableWidgetItem(scan_type))
            self.table.setItem(row_pos, 2, QTableWidgetItem(str(data_points)))
            self.table.setItem(row_pos, 3, QTableWidgetItem(str(start)))
            self.table.setItem(row_pos, 4, QTableWidgetItem(str(stop)))
            self.table.setItem(row_pos, 5, QTableWidgetItem(str(step)))

            # Add or update data entry.
            self.auto_data_dict.update({self.scan_number: data})
            print(self.auto_data_dict)

        elif scan_type == 'Manual':
            if self.table_has_manual_entry:
                self.table_manual_points += 1
                print("TABLE MANUAL POINTS: " + str(self.table_manual_points))
                self.table.setItem(self.table_manual_row, 2, QTableWidgetItem(str(self.table_manual_points)))

                # Append to manual data CSV string.
                self.man_data_str += data
                print(self.man_data_str)

            else:
                self.table_has_manual_entry = True
                self.table.insertRow(0)
                self.table.setItem(0, 0, QTableWidgetItem(str(self.scan_number)))
                self.table.setItem(0, 1, QTableWidgetItem(scan_type))
                self.table.setItem(0, 2, QTableWidgetItem(str(data_points)))
                self.table.setItem(0, 3, QTableWidgetItem(str(start)))
                self.table.setItem(0, 4, QTableWidgetItem(str(stop)))
                self.table.setItem(0, 5, QTableWidgetItem(str(step)))

                # Set manual data CSV string.
                self.man_data_str = data
                print(self.man_data_str)

    def autosave_dir_triggered(self):
        self.data_save_directory = QFileDialog.getExistingDirectory(self, 'Auto logging files location', self.data_save_directory, options=QFileDialog.ShowDirsOnly)

    # TODO: Delete?
    def preferences_triggered(self):
        pass

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


    def update_status_bar_grating_equation_values(self):
        self.sb_grating_density.setText("  <i>G</i> " + str(self.grating_density) + " grooves/mm    ")
        self.sb_zero_offset.setText("  <i>&lambda;</i><sub>0</sub> " + str(self.zero_ofst) + " nm    ")
        self.sb_inc_ang.setText("  <i>&theta;</i><sub>inc</sub> " + str(self.incidence_ang) + " deg    ")
        self.sb_tan_ang.setText("  <i>&theta;</i><sub>tan</sub> " + str(self.tangent_ang) + " deg    ")
        self.sb_arm_len.setText("  <i>L</i> " + str(self.arm_length) + " mm    ")
        self.sb_diff_order.setText("  <i>m</i> " + str(self.diff_order) + "    ")
        self.sb_conv_slope.setText("   %.06f slope    "%(self.conversion_slope))

    def update_plots(self, data: list):
        if self.plotCanvas is None:
            return
        self.plotCanvas.update_plots(data)

    def scan_status_update(self, status):
        self.UIE_mgw_scan_status_ql.setText('<html><head/><body><p><span style=" font-weight:600;">%s</span></p></body></html>'%(status))

    def scan_progress(self, curr_percent):
        self.UIE_mgw_scan_qpbar.setValue(curr_percent)

    def scan_complete(self):
        self.scanRunning = False
        self.disable_movement_sensitive_buttons(False)
        self.UIE_mgw_scan_qpb.setText('Begin Scan')
        self.UIE_mgw_scan_status_ql.setText('<html><head/><body><p><span style=" font-weight:600;">IDLE</span></p></body></html>')
        self.UIE_mgw_scan_qpbar.reset()

    def scan_data_begin(self, scan_idx: int, metadata: dict):
        n_scan_idx = self.table.insertData(None, None, metadata)
        if n_scan_idx != scan_idx:
            print('\n\n CHECK INSERTION ID MISMATCH %d != %d\n\n'%(scan_idx, n_scan_idx))

    def scan_data_update(self, scan_idx: int, which_sampler: int, xdata: float, ydata: float):
        # TODO: Add the ability to plot multiple sampler's data. These will come in distinguished by the which_sampler variable, which is equivalent to that sampler's index in the samplers list. This is a slot and will be called via a signal in Scan.run().
        # TODO: This is going to require an overhaul to datatable.py, allowing two X and two Y axes.
        
        if which_sampler == 0:
            self.table.insertDataAt(scan_idx, xdata, ydata)

    def scan_data_complete(self, scan_idx: int):
        self.table.markInsertFinished(scan_idx)
        self.table.updateTableDisplay()
        if self.scan_repeats.value() > 0:
            self.scan_repeats.setValue(self.scan_repeats.value() - 1)
            self.scan_button_pressed()

    def update_position_displays(self):
        self.current_position = self.motion_controllers.main_drive_axis.get_position()
        
        if self.homing_started: # set this to True at __init__ because we are homing, and disable everything. same goes for 'Home' button
            home_status = self.motion_controllers.main_drive_axis.is_homing() # explore possibility of replacing this with is_homed()

            if home_status:
                # Detect if the device is saying its homing, but its not actually moving.
                if self.current_position == self.previous_position:
                    self.immobile_count += 1
                if self.immobile_count >= 3:
                    self.motion_controllers.main_drive_axis.home()
                    self.immobile_count = 0

            if not home_status:
                # enable stuff here
                print(home_status)
                self.immobile_count = 0
                self.scan_status_update("IDLE")
                self.disable_movement_sensitive_buttons(False)
                self.homing_started = False
                pass
        move_status = self.motion_controllers.main_drive_axis.is_moving()
        
        if not move_status and self.moving and not self.scanRunning:
            self.disable_movement_sensitive_buttons(False)

        self.moving = move_status
        self.previous_position = self.current_position

        self.UIE_mgw_currpos_nm_disp_ql.setText('<b><i>%3.4f</i></b>'%(((self.current_position / self.motion_controllers.main_drive_axis.mm_to_idx) / self.conversion_slope) - self.zero_ofst))

    def scan_button_pressed(self):
        if not self.scanRunning:
            self.scanRunning = True
            self.disable_movement_sensitive_buttons(True)
            self.scan.start()

    def stop_scan_button_pressed(self):
        if self.scanRunning:
            self.scanRunning = False

    def move_to_position_button_pressed(self):
        self.moving = True

        self.disable_movement_sensitive_buttons(True)

        print("Conversion slope: " + str(self.conversion_slope))
        print("Manual position: " + str(self.manual_position))
        print("Move to position button pressed, moving to %d nm"%(self.manual_position))
        pos = int((self.UIE_mgw_pos_qdsb.value() + self.zero_ofst) * self.conversion_slope * self.motion_controllers.main_drive_axis.mm_to_idx)
        self.motion_controllers.main_drive_axis.move_to(pos, False)

    def start_changed(self):
        print("Start changed to: %s mm"%(self.UIE_mgw_start_qdsb.value()))
        self.startpos = (self.UIE_mgw_start_qdsb.value() + self.zero_ofst) * self.conversion_slope
        print(self.startpos)

    def stop_changed(self):
        print("Stop changed to: %s mm"%(self.UIE_mgw_stop_qdsb.value()))
        self.stoppos = (self.UIE_mgw_stop_qdsb.value() + self.zero_ofst) * self.conversion_slope
        print(self.stoppos)

    def step_changed(self):
        print("Step changed to: %s mm"%(self.UIE_mgw_step_qdsb.value()))
        self.steppos = (self.UIE_mgw_step_qdsb.value()) * self.conversion_slope
        print(self.steppos)

    def manual_pos_changed(self):
        print("Manual position changed to: %s mm"%(self.UIE_mgw_pos_qdsb.value()))
        self.manual_position = (self.UIE_mgw_pos_qdsb.value() + self.zero_ofst) * self.conversion_slope

    def show_window_grating_config(self):
        print('show_window_grating_config')
        if self.grating_conf_win is None: 
            self.grating_conf_win = QDialog(self)

            self.grating_conf_win.setWindowTitle('Grating Density Input')
            self.grating_conf_win.setMinimumSize(320, 320)

            # self.grating_spinbox: SelectAllDoubleSpinBox = SelectAllDoubleSpinBox()
            self.grating_spinbox: QDoubleSpinBox = QDoubleSpinBox()
            self.grating_spinbox.setMinimum(0)
            self.grating_spinbox.setMaximum(50000)
            self.grating_spinbox.setButtonSymbols(QAbstractSpinBox.NoButtons)
            self.grating_spinbox.setDecimals(4)

            apply_button = QPushButton('Add Entry')
            apply_button.clicked.connect(self.apply_grating_input)

            layout = QVBoxLayout()
            layout.addWidget(self.grating_spinbox)
            layout.addStretch(1)
            layout2 = QHBoxLayout()
            layout2.addStretch(1)
            layout2.addWidget(apply_button)
            layout2.addStretch(1)
            layout.addLayout(layout2)

            # layout.addWidget(self.apply_button)
            self.grating_conf_win.setLayout(layout)

        self.grating_spinbox.setFocus() # Automatically sets this as focus.
        self.grating_spinbox.selectAll()
        self.grating_conf_win.exec()

    def apply_grating_input(self):
        val = self.grating_spinbox.value()
        exists = False
        for v in self.grating_combo_lstr[:-1]:
            if float(v) == val:
                exists = True
                break
        if not exists:
            out = str(self.grating_spinbox.value())
            if int(float(out)) == float(out):
                out = out.split('.')[0]
            self.grating_combo_lstr.insert(-1, out)
            self.UIE_mcw_grating_qcb.insertItem(self.UIE_mcw_grating_qcb.count() - 1, self.grating_combo_lstr[-2])
            self.UIE_mcw_grating_qcb.setCurrentIndex(self.UIE_mcw_grating_qcb.count() - 2)
        self.grating_conf_win.close()    

    def new_grating_item(self, idx: int):
        slen = len(self.grating_combo_lstr) # old length
        if idx == slen - 1:
            self.show_window_grating_config()
            if len(self.grating_combo_lstr) != slen: # new length is different, new entry has been added
                self.current_grating_idx = self.UIE_mcw_grating_qcb.setCurrentIndex(idx)
            else: # new entry has not been added
                self.UIE_mcw_grating_qcb.setCurrentIndex(self.current_grating_idx)

    # def dm_retry_button(self):
    #     # self.application.exit(MMC_Main.EXIT_CODE_REBOOT)
    #     self.dm_list_label.setText("Attempting to autoconnect...")
    #     self.application.processEvents()
    #     self.autoconnect_devices()

    def show_window_machine_config(self):
        if self.machine_conf_win is None:
            ui_file_name = exeDir + '/ui/grating_input.ui'
            ui_file = QFile(ui_file_name)
            if not ui_file.open(QIODevice.ReadOnly):
                print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
                raise RuntimeError('Could not load grating input UI file')
            
            self.machine_conf_win = QDialog(self) # pass parent window
            uic.loadUi(ui_file, self.machine_conf_win)

            self.machine_conf_win.setWindowTitle('Monochromator Configuration')

            self.UIE_mcw_grating_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, 'grating_combo_2')
            self.UIE_mcw_grating_qcb.addItems(self.grating_combo_lstr)
            print(self.current_grating_idx)
            self.UIE_mcw_grating_qcb.setCurrentIndex(self.current_grating_idx)
            self.UIE_mcw_grating_qcb.activated.connect(self.new_grating_item)
            
            self.UIE_mcw_zero_ofst_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'zero_offset_in')
            self.UIE_mcw_zero_ofst_in_qdsb.setValue(self.zero_ofst)
            
            self.UIE_mcw_incidence_ang_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'incidence_angle_in')
            self.UIE_mcw_incidence_ang_in_qdsb.setValue(self.incidence_ang)
            
            self.UIE_mcw_tangent_ang_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'tangent_angle_in')
            self.UIE_mcw_tangent_ang_in_qdsb.setValue(self.tangent_ang)

            self.UIE_mcw_arm_length_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'arm_length_in')
            self.UIE_mcw_arm_length_in_qdsb.setValue(self.arm_length)

            self.UIE_mcw_diff_order_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'diff_order_in')
            self.UIE_mcw_diff_order_in_qdsb.setValue(self.diff_order)

            self.UIE_mcw_max_pos_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'max_pos_sbox')
            self.UIE_mcw_max_pos_in_qdsb.setValue(self.max_pos)

            self.UIE_mcw_min_pos_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'min_pos_sbox')
            self.UIE_mcw_min_pos_in_qdsb.setValue(self.min_pos)

            self.UIE_mcw_machine_conf_qpb = self.machine_conf_win.findChild(QPushButton, 'update_conf_btn')
            self.UIE_mcw_machine_conf_qpb.clicked.connect(self.apply_machine_conf)

            self.UIE_mcw_accept_qpb = self.machine_conf_win.findChild(QPushButton, 'mcw_accept')
            self.UIE_mcw_accept_qpb.clicked.connect(self.accept_mcw)

            # Get axes combos.
            self.UIE_mcw_main_drive_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "main_drive_axis_combo")
            self.UIE_mcw_color_wheel_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "color_wheel_axis_combo")
            self.UIE_mcw_sample_rotation_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "sample_rotation_axis_combo")
            self.UIE_mcw_sample_translation_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "sample_translation_axis_combo")
            self.UIE_mcw_detector_rotation_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "detector_rotation_axis_combo")

            none = 'No Device Selected'
            self.UIE_mcw_main_drive_axis_qcb.addItem('%s'%(none))
            self.UIE_mcw_color_wheel_axis_qcb.addItem('%s'%(none))
            self.UIE_mcw_sample_rotation_axis_qcb.addItem('%s'%(none))
            self.UIE_mcw_sample_translation_axis_qcb.addItem('%s'%(none))
            self.UIE_mcw_detector_rotation_axis_qcb.addItem('%s'%(none))

            # Populate axes combos.
            for dev in self.mtn_ctrls:
                # TODO: Have selected the current one.
                print('Adding %s to config list.'%(dev))
                self.UIE_mcw_main_drive_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))
                self.UIE_mcw_main_drive_axis_qcb.setCurrentIndex(1)
                self.UIE_mcw_color_wheel_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))
                self.UIE_mcw_sample_rotation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))
                self.UIE_mcw_sample_translation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))
                self.UIE_mcw_detector_rotation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))

            # Select the devices selected in device manager.
            
        self.machine_conf_win.exec() # synchronously run this window so parent window is disabled
        print('Exec done', self.current_grating_idx, self.UIE_mcw_grating_qcb.currentIndex())
        if self.current_grating_idx != self.UIE_mcw_grating_qcb.currentIndex():
            self.UIE_mcw_grating_qcb.setCurrentIndex(self.current_grating_idx)

    def update_movement_limits(self):
        self.UIE_mgw_pos_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_pos_qdsb.setMinimum(self.min_pos)

        self.UIE_mgw_start_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_start_qdsb.setMinimum(self.min_pos)

        self.UIE_mgw_stop_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_stop_qdsb.setMinimum(self.min_pos)

    def apply_machine_conf(self):
        print('Apply config called')
        idx = self.UIE_mcw_grating_qcb.currentIndex()
        if idx < len(self.grating_combo_lstr) - 1:
            self.current_grating_idx = idx
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx])
        print(self.grating_density)
        self.diff_order = int(self.UIE_mcw_diff_order_in_qdsb.value())
        self.max_pos = self.UIE_mcw_max_pos_in_qdsb.value()
        self.min_pos = self.UIE_mcw_min_pos_in_qdsb.value()

        self.update_movement_limits()

        self.zero_ofst = self.UIE_mcw_zero_ofst_in_qdsb.value()
        self.incidence_ang = self.UIE_mcw_incidence_ang_in_qdsb.value()
        self.tangent_ang = self.UIE_mcw_tangent_ang_in_qdsb.value()
        self.arm_length = self.UIE_mcw_arm_length_in_qdsb.value()

        self.calculate_conversion_slope()

        self.update_status_bar_grating_equation_values()

    def accept_mcw(self):


        print('~~MACHINE CONFIGURATION ACCEPT CALLED:')
        print('~Main Drive')
        print(self.UIE_mcw_main_drive_axis_qcb.currentText())
        print('~Color Wheel Axis')
        print(self.UIE_mcw_color_wheel_axis_qcb.currentText())
        print('~Sample Axes')
        print(self.UIE_mcw_sample_rotation_axis_qcb.currentText())
        print(self.UIE_mcw_sample_translation_axis_qcb.currentText())
        print('~Detector Rotation Axis')
        print(self.UIE_mcw_detector_rotation_axis_qcb.currentText())
        print('~~')

        # print(self.dev_list)

        self.motion_controllers.main_drive_axis = self.mtn_ctrls[self.UIE_mcw_main_drive_axis_qcb.currentIndex() - 1]
        self.motion_controllers.color_wheel_axis = self.mtn_ctrls[self.UIE_mcw_color_wheel_axis_qcb.currentIndex() - 1]
        self.motion_controllers.sample_rotation_axis = self.mtn_ctrls[self.UIE_mcw_sample_rotation_axis_qcb.currentIndex() - 1]
        self.motion_controllers.sample_translation_axis = self.mtn_ctrls[self.UIE_mcw_sample_translation_axis_qcb.currentIndex() - 1]
        self.motion_controllers.detector_rotation_axis = self.mtn_ctrls[self.UIE_mcw_detector_rotation_axis_qcb.currentIndex() - 1]

        self.machine_conf_win.close()

    
    def calculate_conversion_slope(self):
        self.conversion_slope = ((self.arm_length * self.diff_order * self.grating_density)/(2 * (m.cos(m.radians(self.tangent_ang))) * (m.cos(m.radians(self.incidence_ang))) * 1e6))

class Scan(QThread):
    SIGNAL_status_update = pyqtSignal(str)
    SIGNAL_progress = pyqtSignal(int)
    SIGNAL_complete = pyqtSignal()

    SIGNAL_data_begin = pyqtSignal(int, dict) # scan index, which sampler, redundant
    SIGNAL_data_update = pyqtSignal(int, int, float, float) # scan index, which sampler, xdata, ydata (to be appended into index)
    SIGNAL_data_complete = pyqtSignal(int) # scan index, which sampler, redundant

    def __init__(self, parent: QMainWindow):
        super(Scan, self).__init__()
        self.other: MMC_Main = parent
        self.SIGNAL_status_update.connect(self.other.scan_status_update)
        self.SIGNAL_progress.connect(self.other.scan_progress)
        self.SIGNAL_complete.connect(self.other.scan_complete)
        self.SIGNAL_data_begin.connect(self.other.scan_data_begin)
        self.SIGNAL_data_update.connect(self.other.scan_data_update)
        self.SIGNAL_data_complete.connect(self.other.scan_data_complete)
        print('mainWindow reference in scan init: %d'%(sys.getrefcount(self.other) - 1))
        self._last_scan = -1

    def __del__(self):
        self.wait()

    def run(self):
        print('\n\n\n')
        self.other.disable_movement_sensitive_buttons(True)

        print(self.other)
        print("Save to file? " + str(self.other.autosave_data_bool))

        self.SIGNAL_status_update.emit("PREPARING")
        sav_files = []
        tnow = dt.datetime.now()
        if (self.other.autosave_data_bool):
            filetime = tnow.strftime('%Y%m%d%H%M%S')
            for sampler in self.other.samplers:
                filename = '%s%s_%s_data.csv'%(self.other.data_save_directory, filetime, sampler.short_name())
                # filename = self.other.data_save_directory + tnow.strftime('%Y%m%d%H%M%S') + "_data.csv"
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                sav_files.append(open(filename, 'w'))

        print("SCAN QTHREAD")
        print("Start | Stop | Step")
        print(self.other.startpos, self.other.stoppos, self.other.steppos)
        self.other.startpos = (self.other.UIE_mgw_start_qdsb.value() + self.other.zero_ofst) * self.other.conversion_slope
        self.other.stoppos = (self.other.UIE_mgw_stop_qdsb.value() + self.other.zero_ofst) * self.other.conversion_slope
        self.other.steppos = (self.other.UIE_mgw_step_qdsb.value()) * self.other.conversion_slope
        if self.other.steppos == 0 or self.other.startpos == self.other.stoppos:
            for f in sav_files:
                if (f is not None):
                    f.close()
            self.SIGNAL_complete.emit()
            return
        scanrange = np.arange(self.other.startpos, self.other.stoppos + self.other.steppos, self.other.steppos)
        nidx = len(scanrange)

        # MOVES TO ZERO PRIOR TO BEGINNING A SCAN
        self.SIGNAL_status_update.emit("ZEROING")
        prep_pos = int((0 + self.other.zero_ofst) * self.other.conversion_slope * self.other.motion_controllers.main_drive_axis.mm_to_idx)
        self.other.motion_controllers.main_drive_axis.move_to(prep_pos, True)
        self.SIGNAL_status_update.emit("HOLDING")
        sleep(1)

        self._xdata = []
        self._ydata = []

        for sampler in self.other.samplers:
            self._xdata.append([])
            self._ydata.append([])

        self._scan_id = self.other.table.scanId
        metadata = {'tstamp': tnow, 'mm_to_idx': self.other.motion_controllers.main_drive_axis.mm_to_idx, 'mm_per_nm': self.other.conversion_slope, 'lam_0': self.other.zero_ofst, 'scan_id': self.scanId}
        self.SIGNAL_data_begin.emit(self.scanId,  metadata) # emit scan ID so that the empty data can be appended and table scan ID can be incremented
        while self.scanId == self.other.table.scanId: # spin until that happens
            continue
        for idx, dpos in enumerate(scanrange):
            if not self.other.scanRunning:
                break
            self.SIGNAL_status_update.emit("MOVING")
            self.other.motion_controllers.main_drive_axis.move_to(dpos * self.other.motion_controllers.main_drive_axis.mm_to_idx, True)
            pos = self.other.motion_controllers.main_drive_axis.get_position()
            self.SIGNAL_status_update.emit("SAMPLING")

            i=0
            for sampler in self.other.samplers:
                buf = sampler.sample_data()
                print(buf)
                self.SIGNAL_progress.emit(round(((idx + 1) * 100 / nidx)/len(self.other.samplers)))
                # process buf
                words = buf.split(',') # split at comma
                if len(words) != 3:
                    continue
                try:
                    mes = float(words[0][:-1]) # skip the A (unit suffix)
                    err = int(float(words[2])) # skip timestamp
                except Exception:
                    continue
                self._xdata[i].append((((pos / self.other.motion_controllers.main_drive_axis.mm_to_idx) / self.other.conversion_slope)) - self.other.zero_ofst)
                self._ydata[i].append(self.other.mes_sign * mes * 1e12)
                self.SIGNAL_data_update.emit(self.scanId, i, self._xdata[i][-1], self._ydata[i][-1])

                if sav_files[i] is not None:
                    if idx == 0:
                        sav_files[i].write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
                        sav_files[i].write('# Steps/mm: %f\n'%(self.other.motion_controllers.main_drive_axis.mm_to_idx))
                        sav_files[i].write('# mm/nm: %e; lambda_0 (nm): %e\n'%(self.other.conversion_slope, self.other.zero_ofst))
                        sav_files[i].write('# Position (step),Position (nm),Mean Current(A),Status/Error Code\n')
                    # process buf
                    # 1. split by \n
                    buf = '%d,%e,%e,%d\n'%(pos, ((pos / self.other.motion_controllers.main_drive_axis.mm_to_idx) / self.other.conversion_slope) - self.other.zero_ofst, self.other.mes_sign * mes, err)
                    sav_files[i].write(buf)

                i += 1

        for sav_file in sav_files:
            if (sav_file is not None):
                sav_file.close()
        self.other.num_scans += 1

        self.SIGNAL_complete.emit()
        self.SIGNAL_data_complete.emit(self.scanId)
        print('mainWindow reference in scan end: %d'%(sys.getrefcount(self.other) - 1))
    
    @property
    def xdata(self, which_sampler: int):
        return np.array(self._xdata[which_sampler], dtype=float)
    
    @property
    def ydata(self, which_sampler: int):
        return np.array(self._ydata[which_sampler], dtype=float)

    @property
    def scanId(self):
        return self._scan_id


# Main function.
if __name__ == '__main__':
    # There will be three separate GUIs:
    # 1. Initialization loading screen, where devices are being searched for and the current status and tasks are displayed. If none are found, display an error and an exit button.
    # 2. The device selection display, where devices can be selected and their settings can be changed prior to entering the control program.
    # 3. The control GUI (mainwindow.ui), where the user has control over what the device(s) do.
    
    application = QApplication(sys.argv)

    # Finding and setting of fonts.
    try:
        fid = QFontDatabase.addApplicationFont(exeDir + '/fonts/digital-7 (mono italic).ttf')
        # fstr = QFontDatabase.applicationFontFamilies(fid)[0]
        # digital_7_italic_22 = QFont(fstr, 22)
    except Exception as e:
        print(e.what())

    try:
        fid = QFontDatabase.addApplicationFont(exeDir + '/fonts/digital-7 (mono).ttf')
        # fstr = QFontDatabase.applicationFontFamilies(fid)[0]
        # digital_7_16 = QFont(fstr, 16)
    except Exception as e:
        print(e.what())

    # Main GUI and child-window setup.
    ui_file_name = exeDir + '/ui/grating_input.ui'
    ui_file = QFile(ui_file_name)
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)

    ui_file_name = exeDir + '/ui/device_manager.ui'
    ui_file = QFile(ui_file_name) # workaround to load UI file with pyinstaller
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)

    ui_file_name = exeDir + '/ui/mainwindow_mk2.ui'
    ui_file = QFile(ui_file_name) # workaround to load UI file with pyinstaller
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)

    exit_code = MMC_Main.EXIT_CODE_REBOOT
    while exit_code == MMC_Main.EXIT_CODE_REBOOT:
        exit_code = MMC_Main.EXIT_CODE_FINISHED

        # Initializes the GUI / Main GUI bootup.
        mainWindow = MMC_Main(application, ui_file)
        
        # Wait for the Qt loop to exit before exiting.
        exit_code = application.exec_() # block until

        # Save the current configuration when exiting. If the program crashes, it doesn't save your config.
        if mainWindow.main_gui_booted:
            save_config(appDir, mainWindow.mes_sign, mainWindow.autosave_data_bool, mainWindow.data_save_directory, mainWindow.grating_combo_lstr, mainWindow.current_grating_idx, mainWindow.diff_order, mainWindow.zero_ofst, mainWindow.incidence_ang, mainWindow.tangent_ang, mainWindow.arm_length, mainWindow.max_pos, mainWindow.min_pos)    

        # Cleanup.
        del mainWindow

    print('Exiting program...')

    # Exit.
    # sys.exit(exit_code)
    os._exit(exit_code)
# %%
