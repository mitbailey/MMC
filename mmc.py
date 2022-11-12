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
                             QSizePolicy, QSlider, QStyle, QToolButton, QVBoxLayout, QWidget, QLineEdit, QPlainTextEdit,
                             QTableWidget, QTableWidgetItem, QSplitter, QAbstractItemView, QStyledItemDelegate, QHeaderView, QFrame, QProgressBar, QCheckBox, QToolTip, QGridLayout, QSpinBox,
                             QLCDNumber, QAbstractSpinBox, QStatusBar, QAction)
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
        del self.mtn_ctrls
        del self.samplers
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

        # if len(self._startup_args) != 1:
        #     self.dummy = False
        # else:
        #     self.dummy = True

        self.dev_man_win_enabled = False
        self.main_gui_booted = False
        self.dev_man_win = None
        self.show_window_device_manager()
        self.dev_finder = None

        # TODO: These indices will keep track of which drives correspond to which controllers.
        self.main_drive_i = 0

    # Screen shown during startup to disable premature user interaction as well as handle device-not-found issues.
    def show_window_device_manager(self):
        self.device_timer = None
        if self.dev_man_win is None:
            ui_file_name = exeDir + '/ui/device_manager.ui'
            ui_file = QFile(ui_file_name)
            if not ui_file.open(QIODevice.ReadOnly):
                print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
                raise RuntimeError('Could not load grating input UI file')

            self.dev_man_win = QDialog(self) # pass parent window
            uic.loadUi(ui_file, self.dev_man_win)

            self.dev_man_win.setWindowTitle('Device Manager')

            self.dm_prompt_label: QLabel = self.dev_man_win.findChild(QLabel, "explanation_label")

            self.dm_list_label: QLabel = self.dev_man_win.findChild(QLabel, "devices_label")

            self.dm_sampler_layouts = []
            self.dm_sampler_layouts.append(self.dev_man_win.findChild(QHBoxLayout, "sampler_combo_sublayout"))

            self.dm_mtn_ctrl_layouts = []
            self.dm_mtn_ctrl_layouts.append(self.dev_man_win.findChild(QHBoxLayout, "mtn_ctrl_combo_sublayout"))

            self.dm_sampler_combos = []
            # self.dm_sampler_combos.clear()
            # self.dm_sampler_combo: QComboBox = self.dev_man_win.findChild(QComboBox, "samp_combo")
            # self.dm_sampler_combo.addItem("Auto-Connect")
            self.dm_sampler_combos.append(self.dev_man_win.findChild(QComboBox, "samp_combo"))
            self.dm_sampler_combos[0].addItem("Auto-Connect")
            self.dm_sampler_model_combos = []
            self.dm_sampler_model_combos.append(self.dev_man_win.findChild(QComboBox, "samp_model_combo"))
            # self.dm_sampler_model_combos[0].addItem('<SELECT>')
            for device in DataSampler.SupportedDevices:
                self.dm_sampler_model_combos[0].addItem(device)

            self.dm_mtn_ctrl_combos = []
            # self.dm_mtn_ctrl_combos.clear()
            # self.dm_mtn_ctrl_combo: QComboBox = self.dev_man_win.findChild(QComboBox, "mtn_combo")
            # self.dm_mtn_ctrl_combo.addItem("Auto-Connect")
            self.dm_mtn_ctrl_combos.append(self.dev_man_win.findChild(QComboBox, "mtn_combo"))
            self.dm_mtn_ctrl_combos[0].addItem("Auto-Connect")
            self.dm_mtn_ctrl_model_combos = []
            self.dm_mtn_ctrl_model_combos.append(self.dev_man_win.findChild(QComboBox, "mtn_model_combo"))
            # self.dm_mtn_ctrl_model_combos[0].addItem('<SELECT>')
            for device in MotionController.SupportedDevices:
                self.dm_mtn_ctrl_model_combos[0].addItem(device)

            self.dm_accept_button: QPushButton = self.dev_man_win.findChild(QPushButton, "acc_button")
            self.dm_accept_button.clicked.connect(self.connect_devices)
            # self.dm_accept_button.setDisabled(True)
            self.dm_dummy_checkbox: QCheckBox = self.dev_man_win.findChild(QCheckBox, "dum_checkbox")
            self.dm_dummy_checkbox.setChecked(len(self._startup_args) == 2)

            self.dm_num_samplers_spin: QSpinBox = self.dev_man_win.findChild(QSpinBox, "num_samplers")
            self.dm_num_samplers_spin.valueChanged.connect(self.update_num_samplers_ui)
            self.num_samplers = 1

            self.dm_num_motion_controllers_spin: QSpinBox = self.dev_man_win.findChild(QSpinBox, "num_motion_controllers")
            self.dm_num_motion_controllers_spin.valueChanged.connect(self.update_num_motion_controllers_ui)
            self.num_motion_controllers = 1

            self.sampler_combo_layout: QVBoxLayout = self.dev_man_win.findChild(QVBoxLayout, "sampler_combo_layout")
            self.mtn_ctrl_combo_layout: QVBoxLayout = self.dev_man_win.findChild(QVBoxLayout, "mtn_ctrl_combo_layout")

            self.dev_man_win.show()

        self.application.processEvents()
        self.SIGNAL_device_manager_ready.emit()

    def update_num_samplers_ui(self):
        if self.num_samplers != self.dm_num_samplers_spin.value():
            self.num_samplers = self.dm_num_samplers_spin.value()
            for widget in self.dm_sampler_combos:
                widget.setParent(None)
            for widget in self.dm_sampler_model_combos:
                widget.setParent(None)
            for layout in self.dm_sampler_layouts:
                self.sampler_combo_layout.removeItem(layout)

            self.dm_sampler_combos = []
            self.dm_sampler_model_combos = []
            self.dm_sampler_layouts = []

            for i in range(self.num_samplers):
                s_combo = QComboBox()
                s_combo.addItem("Auto-Connect")
                for dev in self.dev_list:
                    s_combo.addItem('%s'%(dev))
                m_combo = QComboBox()
                # m_combo.addItem('<SELECT>')
                for device in DataSampler.SupportedDevices:
                    m_combo.addItem(device)
                layout = QHBoxLayout()
                layout.addWidget(s_combo)
                layout.addStretch(4)
                layout.addWidget(m_combo)
                layout.addStretch(1)
                self.sampler_combo_layout.addLayout(layout)
                self.dm_sampler_combos.append(s_combo)
                self.dm_sampler_model_combos.append(m_combo)
                self.dm_sampler_layouts.append(layout)

        print('new samplers combo list len: %d'%(len(self.dm_sampler_combos)))

    def update_num_motion_controllers_ui(self):
        if self.num_motion_controllers != self.dm_num_motion_controllers_spin.value():
            self.num_motion_controllers = self.dm_num_motion_controllers_spin.value()
            for widget in self.dm_mtn_ctrl_combos:
                widget.setParent(None)
            for widget in self.dm_mtn_ctrl_model_combos:
                widget.setParent(None)
            for layout in self.dm_mtn_ctrl_layouts:
                self.mtn_ctrl_combo_layout.removeItem(layout)

            # Very important - must reset the combos list.
            self.dm_mtn_ctrl_combos = []
            self.dm_mtn_ctrl_model_combos = []
            self.dm_mtn_ctrl_layouts = []

            for i in range(self.num_motion_controllers):
                s_combo = QComboBox()
                s_combo.addItem("Auto-Connect")
                for dev in self.dev_list:
                    s_combo.addItem('%s'%(dev))
                m_combo = QComboBox()
                # m_combo.addItem('<SELECT>')
                for device in MotionController.SupportedDevices:
                    m_combo.addItem(device)
                layout = QHBoxLayout()
                layout.addWidget(s_combo)
                layout.addStretch(4)
                layout.addWidget(m_combo)
                layout.addStretch(1)
                self.mtn_ctrl_combo_layout.addLayout(layout)
                self.dm_mtn_ctrl_combos.append(s_combo)
                self.dm_mtn_ctrl_model_combos.append(m_combo)
                self.dm_mtn_ctrl_layouts.append(layout)

        print('new mtn ctrls combo list len: %d'%(len(self.dm_mtn_ctrl_combos)))

    def connect_devices(self):
        print('\n\n')
        print("connect_devices")

        self.dm_prompt_label.setText("Attempting to connect...")
        self.application.processEvents()

        dummy = self.dm_dummy_checkbox.isChecked()
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
                if self.dm_sampler_combos[i].currentIndex() != 0:
                    print("Using manual port: %s"%(self.dm_sampler_combos[i].currentText().split(' ')[0]))
                    self.samplers[i] = DataSampler(dummy, self.dm_sampler_model_combos[i].currentText(), self.dm_sampler_combos[i].currentText().split(' ')[0])
                else:
                    # Auto-Connect
                    # self.samplers[i] = DataSampler(dummy, DataSampler.SupportedDevices[0])
                    print('currentIndex', self.dm_sampler_combos[i].currentIndex(), self.dm_sampler_combos[i].currentText())
                    print(len(self.dm_sampler_combos))
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
                if self.dm_mtn_ctrl_combos[i].currentIndex() != 0:
                    print("Using manual port: %s"%(self.dm_mtn_ctrl_combos[i].currentText().split(' ')[0]))
                    self.mtn_ctrls[i] = MotionController(dummy, self.dm_mtn_ctrl_model_combos[i].currentText(), self.dm_mtn_ctrl_combos[i].currentText().split(' ')[0])
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
            self.dev_man_win.close()
            self._show_main_gui(dummy)
            return
        
        # If we are here, then we have not automatically connected to all required devices. We must now enable the device manager.
        if not self.dev_man_win_enabled:
            self.dev_man_win_enabled = True
            self.device_timer = QTimer()
            self.device_timer.timeout.connect(self.devman_list_devices)
            self.device_timer.start(1000)
        self.dm_prompt_label.setText('Auto-connect failed.')   

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
        self.diff_order_in: QDoubleSpinBox = None
        self.max_pos_in: QDoubleSpinBox = None
        self.min_pos_in: QDoubleSpinBox = None
        self.zero_ofst_in: QDoubleSpinBox = None
        self.arm_length_in: QDoubleSpinBox = None
        self.incidence_ang_in: QDoubleSpinBox = None
        self.tangent_ang_in: QDoubleSpinBox = None
        self.machine_conf_btn: QPushButton = None

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
        self.scan_button = self.findChild(QPushButton, "begin_scan_button") # Scanning Control 'Begin Scan' Button
        pixmapi = getattr(QStyle, 'SP_ArrowForward')
        icon = self.style().standardIcon(pixmapi)
        self.scan_button.setIcon(icon)
        self.stop_scan_button: QPushButton = self.findChild(QPushButton, "stop_scan_button")
        pixmapi = getattr(QStyle, 'SP_BrowserStop')
        icon = self.style().standardIcon(pixmapi)
        self.stop_scan_button.setIcon(icon)
        self.stop_scan_button.setEnabled(False)
        self.save_data_checkbox = self.findChild(QCheckBox, "save_data_checkbox") # Scanning Control 'Save Data' Checkbox
        self.dir_box = self.findChild(QLineEdit, "save_dir_lineedit")
        self.start_spin = self.findChild(QDoubleSpinBox, "start_set_spinbox")
        self.stop_spin = self.findChild(QDoubleSpinBox, "end_set_spinbox")

        if dummy:
            self.stop_spin.setValue(0.2)

        self.step_spin = self.findChild(QDoubleSpinBox, "step_set_spinbox")
        self.currpos_nm_disp = self.findChild(QLabel, "currpos_nm")
        self.scan_status = self.findChild(QLabel, "status_label")
        self.scan_progressbar = self.findChild(QProgressBar, "progressbar")
        save_config_btn: QPushButton = self.findChild(QPushButton, 'save_config_button')
        self.pos_spin: QDoubleSpinBox = self.findChild(QDoubleSpinBox, "pos_set_spinbox") # Manual Control 'Position:' Spin Box
        self.move_to_position_button: QPushButton = self.findChild(QPushButton, "move_pos_button")
        self.plotFrame: QWidget = self.findChild(QWidget, "data_graph")
        self.xmin_in: QLineEdit = self.findChild(QLineEdit, "xmin_in")
        self.ymin_in: QLineEdit = self.findChild(QLineEdit, "ymin_in")
        self.xmax_in: QLineEdit = self.findChild(QLineEdit, "xmax_in")
        self.ymax_in: QLineEdit = self.findChild(QLineEdit, "ymax_in")
        self.plot_autorange: QCheckBox = self.findChild(QCheckBox, "autorange_checkbox")
        self.plot_clear_plots: QPushButton = self.findChild(QPushButton, "clear_plots_button")

        self.machine_conf_act: QAction = self.findChild(QAction, "machine_configuration")
        self.invert_mes_act: QAction = self.findChild(QAction, "invert_mes")
        self.autosave_data_act: QAction = self.findChild(QAction, "autosave_data")
        self.autosave_dir_act: QAction = self.findChild(QAction, "autosave_dir_prompt")
        self.preferences_act: QAction = self.findChild(QAction, "preferences")
        self.pop_out_table_act: QAction = self.findChild(QAction, "pop_out_table")
        self.pop_out_plot_act: QAction = self.findChild(QAction, "pop_out_plot")
        self.about_source_act: QAction = self.findChild(QAction, "actionSource_Code")
        self.about_licensing_act: QAction = self.findChild(QAction, "actionLicensing")
        self.about_manual_act: QAction = self.findChild(QAction, "actionManual_2")

        self.save_data_btn: QPushButton = self.findChild(QPushButton, 'save_data_button')
        self.save_data_btn.clicked.connect(self.save_data_cb)
        self.delete_data_btn: QPushButton = self.findChild(QPushButton, 'delete_data_button')
        self.delete_data_btn.clicked.connect(self.delete_data_cb)
        
        table_frame: QFrame = self.findChild(QFrame, "table_frame")
        self.table = DataTableWidget(self)
        VLayout = QVBoxLayout()
        VLayout.addWidget(self.table)
        table_frame.setLayout(VLayout)
        self.home_button: QPushButton = self.findChild(QPushButton, "home_button")
        
        self.homing_started = False
        if not dummy:
            self.homing_started = True
            self.disable_movement_sensitive_buttons(True)
            self.scan_status_update("HOMING")
            self.mtn_ctrls[self.main_drive_i].home()

        # Get and set the palette.
        palette = self.currpos_nm_disp.palette()
        palette.setColor(palette.WindowText, QColor(255, 0, 0))
        palette.setColor(palette.Background, QColor(0, 170, 255))
        palette.setColor(palette.Light, QColor(80, 80, 255))
        palette.setColor(palette.Dark, QColor(0, 255, 0))
        self.currpos_nm_disp.setPalette(palette)

        self.plotCanvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.plotCanvas.clear_plot_fcn()
        self.plotCanvas.set_table_clear_cb(self.table.plotsClearedCb)
        toolbar = self.plotCanvas.get_toolbar(self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self.plotCanvas)
        self.plotFrame.setLayout(layout)

        self.plot_clear_plots.clicked.connect(self.plotCanvas.clear_plot_fcn)

        # Set the initial value of the Manual Control 'Position:' spin box.
        self.pos_spin.setValue(0)

        # Signal-to-slot connections.
        save_config_btn.clicked.connect(self.show_window_machine_config)
        self.scan_button.clicked.connect(self.scan_button_pressed)
        self.stop_scan_button.clicked.connect(self.stop_scan_button_pressed)
        # self.collect_data.clicked.connect(self.manual_collect_button_pressed)
        self.move_to_position_button.clicked.connect(self.move_to_position_button_pressed)
        self.start_spin.valueChanged.connect(self.start_changed)
        self.stop_spin.valueChanged.connect(self.stop_changed)
        self.step_spin.valueChanged.connect(self.step_changed)
        self.pos_spin.valueChanged.connect(self.manual_pos_changed)

        self.machine_conf_act.triggered.connect(self.show_window_machine_config)
        self.invert_mes_act.toggled.connect(self.invert_mes_toggled)
        self.autosave_data_act.toggled.connect(self.autosave_data_toggled)
        self.autosave_dir_act.triggered.connect(self.autosave_dir_triggered)
        self.preferences_act.triggered.connect(self.preferences_triggered)
        self.pop_out_table_act.toggled.connect(self.pop_out_table_toggled)
        self.pop_out_plot_act.toggled.connect(self.pop_out_plot_toggled)
        self.about_licensing_act.triggered.connect(self.open_licensing_hyperlink)
        self.about_manual_act.triggered.connect(self.open_manual_hyperlink)
        self.about_source_act.triggered.connect(self.open_source_hyperlink)

        self.home_button.clicked.connect(self.manual_home)

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

        self.manual_position = (self.pos_spin.value() + self.zero_ofst) * self.conversion_slope
        self.startpos = (self.start_spin.value() + self.zero_ofst) * self.conversion_slope
        self.stoppos = (self.stop_spin.value() + self.zero_ofst) * self.conversion_slope

        if self.mes_sign == -1:
            self.invert_mes_act.setChecked(True)
        else:
            self.invert_mes_act.setChecked(False)

        if self.autosave_data_bool:
            self.autosave_data_act.setChecked(True)
        else:
            self.autosave_data_act.setChecked(False)

        self.update_movement_limits()

        self.table.updatePlots()

        self.dev_man_win.close()
        self.main_gui_booted = True
        self.show()  

    def devman_list_devices(self):
        # self.dev_list = ports_finder.find_all_ports()
        # if self.dev_finder is None:
            # self.dev_finder = DevFinder()
        # self.dev_list = self.dev_finder.get_dev_list()
        self.dev_list = mw.find_all_ports()

        dev_list_str = ''
        for dev in self.dev_list:
            dev_list_str += '%s\n'%(dev)

        if (self.dm_list_label.text() != "~DEVICE LIST~\n" + dev_list_str):
            for i in range(self.num_samplers):
                self.dm_sampler_combos[i].clear()
                self.dm_sampler_combos[i].addItem('Auto-Connect')
                self.dm_sampler_combos[i].setCurrentIndex(0)

                for dev in self.dev_list:
                    self.dm_sampler_combos[i].addItem('%s'%(dev))

            for i in range(self.num_motion_controllers):
                self.dm_mtn_ctrl_combos[i].clear()
                self.dm_mtn_ctrl_combos[i].addItem('Auto-Connect')
                self.dm_mtn_ctrl_combos[i].setCurrentIndex(0)

                for dev in self.dev_list:
                    self.dm_mtn_ctrl_combos[i].addItem('%s'%(dev))

            self.dm_list_label.setText("~DEVICE LIST~\n" + dev_list_str)

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
        if self.move_to_position_button is not None:
            self.move_to_position_button.setDisabled(disable)
        if self.scan_button is not None:
            self.scan_button.setDisabled(disable)

        # The stop scan button should always be set based on if a scan is running.
        if self.scanRunning:
            # Always have the Stop Scan button available when a scan is running.
            self.stop_scan_button.setDisabled(False)
        else:
            self.stop_scan_button.setDisabled(True)

        if self.home_button is not None:
            self.home_button.setDisabled(disable)

    def manual_home(self):
        self.scan_status_update("HOMING")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        self.mtn_ctrls[self.main_drive_i].home()

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
            self.autosave_data_act.setChecked(self.autosave_data_bool)
            
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
        self.scan_status.setText('<html><head/><body><p><span style=" font-weight:600;">%s</span></p></body></html>'%(status))

    def scan_progress(self, curr_percent):
        self.scan_progressbar.setValue(curr_percent)

    def scan_complete(self):
        self.scanRunning = False
        self.disable_movement_sensitive_buttons(False)
        self.scan_button.setText('Begin Scan')
        self.scan_status.setText('<html><head/><body><p><span style=" font-weight:600;">IDLE</span></p></body></html>')
        self.scan_progressbar.reset()

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

    def update_position_displays(self):
        self.current_position = self.mtn_ctrls[self.main_drive_i].get_position()
        
        if self.homing_started: # set this to True at __init__ because we are homing, and disable everything. same goes for 'Home' button
            home_status = self.mtn_ctrls[self.main_drive_i].is_homing() # explore possibility of replacing this with is_homed()

            if home_status:
                # Detect if the device is saying its homing, but its not actually moving.
                if self.current_position == self.previous_position:
                    self.immobile_count += 1
                if self.immobile_count >= 3:
                    self.mtn_ctrls[self.main_drive_i].home()
                    self.immobile_count = 0

            if not home_status:
                # enable stuff here
                print(home_status)
                self.immobile_count = 0
                self.scan_status_update("IDLE")
                self.disable_movement_sensitive_buttons(False)
                self.homing_started = False
                pass
        move_status = self.mtn_ctrls[self.main_drive_i].is_moving()
        
        if not move_status and self.moving and not self.scanRunning:
            self.disable_movement_sensitive_buttons(False)

        self.moving = move_status
        self.previous_position = self.current_position

        self.currpos_nm_disp.setText('<b><i>%3.4f</i></b>'%(((self.current_position / self.mtn_ctrls[self.main_drive_i].mm_to_idx) / self.conversion_slope) - self.zero_ofst))

    def scan_button_pressed(self):
        # self.moving = True
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
        pos = int((self.pos_spin.value() + self.zero_ofst) * self.conversion_slope * self.mtn_ctrls[self.main_drive_i].mm_to_idx)
        self.mtn_ctrls[self.main_drive_i].move_to(pos, False)

    def start_changed(self):
        print("Start changed to: %s mm"%(self.start_spin.value()))
        self.startpos = (self.start_spin.value() + self.zero_ofst) * self.conversion_slope
        print(self.startpos)

    def stop_changed(self):
        print("Stop changed to: %s mm"%(self.stop_spin.value()))
        self.stoppos = (self.stop_spin.value() + self.zero_ofst) * self.conversion_slope
        print(self.stoppos)

    def step_changed(self):
        print("Step changed to: %s mm"%(self.step_spin.value()))
        self.steppos = (self.step_spin.value()) * self.conversion_slope
        print(self.steppos)

    def manual_pos_changed(self):
        print("Manual position changed to: %s mm"%(self.pos_spin.value()))
        self.manual_position = (self.pos_spin.value() + self.zero_ofst) * self.conversion_slope

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
            self.grating_combo.insertItem(self.grating_combo.count() - 1, self.grating_combo_lstr[-2])
            self.grating_combo.setCurrentIndex(self.grating_combo.count() - 2)
        self.grating_conf_win.close()    

    def new_grating_item(self, idx: int):
        slen = len(self.grating_combo_lstr) # old length
        if idx == slen - 1:
            self.show_window_grating_config()
            if len(self.grating_combo_lstr) != slen: # new length is different, new entry has been added
                self.current_grating_idx = self.grating_combo.setCurrentIndex(idx)
            else: # new entry has not been added
                self.grating_combo.setCurrentIndex(self.current_grating_idx)

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

            self.grating_combo: QComboBox = self.machine_conf_win.findChild(QComboBox, 'grating_combo_2')
            self.grating_combo.addItems(self.grating_combo_lstr)
            print(self.current_grating_idx)
            self.grating_combo.setCurrentIndex(self.current_grating_idx)
            self.grating_combo.activated.connect(self.new_grating_item)
            
            self.zero_ofst_in = self.machine_conf_win.findChild(QDoubleSpinBox, 'zero_offset_in')
            self.zero_ofst_in.setValue(self.zero_ofst)
            
            self.incidence_ang_in = self.machine_conf_win.findChild(QDoubleSpinBox, 'incidence_angle_in')
            self.incidence_ang_in.setValue(self.incidence_ang)
            
            self.tangent_ang_in = self.machine_conf_win.findChild(QDoubleSpinBox, 'tangent_angle_in')
            self.tangent_ang_in.setValue(self.tangent_ang)

            self.arm_length_in = self.machine_conf_win.findChild(QDoubleSpinBox, 'arm_length_in')
            self.arm_length_in.setValue(self.arm_length)

            self.diff_order_in = self.machine_conf_win.findChild(QDoubleSpinBox, 'diff_order_in')
            self.diff_order_in.setValue(self.diff_order)

            self.max_pos_in = self.machine_conf_win.findChild(QDoubleSpinBox, 'max_pos_sbox')
            self.max_pos_in.setValue(self.max_pos)

            self.min_pos_in = self.machine_conf_win.findChild(QDoubleSpinBox, 'min_pos_sbox')
            self.min_pos_in.setValue(self.min_pos)

            self.machine_conf_btn = self.machine_conf_win.findChild(QPushButton, 'update_conf_btn')
            self.machine_conf_btn.clicked.connect(self.apply_machine_conf)

            # Get axes combos.
            self.mc_main_drive_axis_combo: QComboBox = self.machine_conf_win.findChild(QComboBox, "main_drive_axis_combo")
            self.mc_color_wheel_axis_combo: QComboBox = self.machine_conf_win.findChild(QComboBox, "color_wheel_axis_combo")
            self.mc_sample_rotation_axis_combo: QComboBox = self.machine_conf_win.findChild(QComboBox, "sample_rotation_axis_combo")
            self.mc_sample_translation_axis_combo: QComboBox = self.machine_conf_win.findChild(QComboBox, "sample_translation_axis_combo")
            self.mc_detector_rotation_axis_combo: QComboBox = self.machine_conf_win.findChild(QComboBox, "detector_rotation_axis_combo")

            none = 'No Device Selected'
            self.mc_main_drive_axis_combo.addItem('%s'%(none))
            self.mc_color_wheel_axis_combo.addItem('%s'%(none))
            self.mc_sample_rotation_axis_combo.addItem('%s'%(none))
            self.mc_sample_translation_axis_combo.addItem('%s'%(none))
            self.mc_detector_rotation_axis_combo.addItem('%s'%(none))

            # Populate axes combos.
            for dev in self.dev_list:
                print('Adding %s to config list.'%(dev))
                self.mc_main_drive_axis_combo.addItem('%s'%(dev))
                self.mc_color_wheel_axis_combo.addItem('%s'%(dev))
                self.mc_sample_rotation_axis_combo.addItem('%s'%(dev))
                self.mc_sample_translation_axis_combo.addItem('%s'%(dev))
                self.mc_detector_rotation_axis_combo.addItem('%s'%(dev))
        
        self.machine_conf_win.exec() # synchronously run this window so parent window is disabled
        print('Exec done', self.current_grating_idx, self.grating_combo.currentIndex())
        if self.current_grating_idx != self.grating_combo.currentIndex():
            self.grating_combo.setCurrentIndex(self.current_grating_idx)

    def update_movement_limits(self):
        self.pos_spin.setMaximum(self.max_pos)
        self.pos_spin.setMinimum(self.min_pos)

        self.start_spin.setMaximum(self.max_pos)
        self.start_spin.setMinimum(self.min_pos)

        self.stop_spin.setMaximum(self.max_pos)
        self.stop_spin.setMinimum(self.min_pos)

    def apply_machine_conf(self):
        print('Apply config called')
        idx = self.grating_combo.currentIndex()
        if idx < len(self.grating_combo_lstr) - 1:
            self.current_grating_idx = idx
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx])
        print(self.grating_density)
        self.diff_order = int(self.diff_order_in.value())
        self.max_pos = self.max_pos_in.value()
        self.min_pos = self.min_pos_in.value()

        self.update_movement_limits()

        self.zero_ofst = self.zero_ofst_in.value()
        self.incidence_ang = self.incidence_ang_in.value()
        self.tangent_ang = self.tangent_ang_in.value()
        self.arm_length = self.arm_length_in.value()

        self.calculate_conversion_slope()

        self.update_status_bar_grating_equation_values()

        self.machine_conf_win.close()
    
    def calculate_conversion_slope(self):
        self.conversion_slope = ((self.arm_length * self.diff_order * self.grating_density)/(2 * (m.cos(m.radians(self.tangent_ang))) * (m.cos(m.radians(self.incidence_ang))) * 1e6))

# TODO: QThread which will be run by the loading UI to initialize communication with devices. Will need to save important data. This functionality currently handled by the MainWindow UI.
class Boot(QThread):
    pass

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
        self.other.startpos = (self.other.start_spin.value() + self.other.zero_ofst) * self.other.conversion_slope
        self.other.stoppos = (self.other.stop_spin.value() + self.other.zero_ofst) * self.other.conversion_slope
        self.other.steppos = (self.other.step_spin.value()) * self.other.conversion_slope
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
        prep_pos = int((0 + self.other.zero_ofst) * self.other.conversion_slope * self.other.mtn_ctrls[self.other.main_drive_i].mm_to_idx)
        self.other.mtn_ctrls[self.other.main_drive_i].move_to(prep_pos, True)
        self.SIGNAL_status_update.emit("HOLDING")
        sleep(1)

        self._xdata = []
        self._ydata = []

        for sampler in self.other.samplers:
            self._xdata.append([])
            self._ydata.append([])

        self._scan_id = self.other.table.scanId
        metadata = {'tstamp': tnow, 'mm_to_idx': self.other.mtn_ctrls[self.other.main_drive_i].mm_to_idx, 'mm_per_nm': self.other.conversion_slope, 'lam_0': self.other.zero_ofst, 'scan_id': self.scanId}
        self.SIGNAL_data_begin.emit(self.scanId,  metadata) # emit scan ID so that the empty data can be appended and table scan ID can be incremented
        while self.scanId == self.other.table.scanId: # spin until that happens
            continue
        for idx, dpos in enumerate(scanrange):
            if not self.other.scanRunning:
                break
            self.SIGNAL_status_update.emit("MOVING")
            self.other.mtn_ctrls[self.other.main_drive_i].move_to(dpos * self.other.mtn_ctrls[self.other.main_drive_i].mm_to_idx, True)
            pos = self.other.mtn_ctrls[self.other.main_drive_i].get_position()
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
                self._xdata[i].append((((pos / self.other.mtn_ctrls[self.other.main_drive_i].mm_to_idx) / self.other.conversion_slope)) - self.other.zero_ofst)
                self._ydata[i].append(self.other.mes_sign * mes * 1e12)
                self.SIGNAL_data_update.emit(self.scanId, i, self._xdata[i][-1], self._ydata[i][-1])

                if sav_files[i] is not None:
                    if idx == 0:
                        sav_files[i].write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
                        sav_files[i].write('# Steps/mm: %f\n'%(self.other.mtn_ctrls[self.other.main_drive_i].mm_to_idx))
                        sav_files[i].write('# mm/nm: %e; lambda_0 (nm): %e\n'%(self.other.conversion_slope, self.other.zero_ofst))
                        sav_files[i].write('# Position (step),Position (nm),Mean Current(A),Status/Error Code\n')
                    # process buf
                    # 1. split by \n
                    buf = '%d,%e,%e,%d\n'%(pos, ((pos / self.other.mtn_ctrls[self.other.main_drive_i].mm_to_idx) / self.other.conversion_slope) - self.other.zero_ofst, self.other.mes_sign * mes, err)
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

    # Exit.
    sys.exit(exit_code)
# %%
