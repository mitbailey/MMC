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
Machine Config. Window       mcw_

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

# TODO: Set up each model's unique configuration and export them to files. Then run the machines with these setups and see if it works. This will also be a handy test of the import/export system.

# OS and SYS Imports
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

# PyQt Imports
from PyQt5 import uic
from PyQt5.Qt import QTextOption
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ARG, QAbstractItemModel,
                          QFileInfo, qFuzzyCompare, QMetaObject, QModelIndex, QObject, Qt,
                          QThread, QTime, QUrl, QSize, QEvent, QCoreApplication, QFile, QIODevice, QMutex, QWaitCondition, QTimer, QPropertyAnimation, QPoint, QEasingCurve)
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

# More Standard Imports
from time import sleep
import weakref
import numpy as np
import datetime as dt
from functools import partial

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# Custom Imports
from utilities.config import load_config, save_config, reset_config
import webbrowser
from utilities_qt.datatable import DataTableWidget
from utilities_qt import scan
from utilities_qt import update_position_displays
from utilities_qt import connect_devices
from instruments.mcpherson import McPherson

from utilities import motion_controller_list as mcl
import middleware as mw
from middleware import MotionController#, list_all_devices
from middleware import Detector

# Fonts
digital_7_italic_22 = None
digital_7_16 = None

# Classes
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
        if self.detectors is not None:
            del self.detectors
        if self.dev_finder is not None:
            self.dev_finder.done = True
            del self.dev_finder

    # Constructor
    def __init__(self, application, uiresource = None):

        # application.setQuitOnLastWindowClosed(False)

        # Handles the initial showing of the UI.
        self.mtn_ctrls = []
        self.detectors = []

        self.connect_devices_thread = connect_devices.ConnectDevices(weakref.proxy(self))
        self.connecting_devices = False

        self.update_position_displays_thread = update_position_displays.UpdatePositionDisplays(weakref.proxy(self))

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

        # Load Configuration File

        # Default grating equation values.
        self.max_pos = 600.0
        self.min_pos = -40.0
        self.model_index = 0
        self.grating_density = 0 # grooves/mm
        self.zero_ofst = 37.8461 # nm

        # Other settings' default values.
        self.main_axis_index = 0
        self.filter_axis_index = 0
        self.rsamp_axis_index = 0
        self.tsamp_axis_index = 0
        self.detector_axis_index = 0

        self.main_axis_dev_name = 'none'
        self.filter_axis_dev_name = 'none'
        self.rsamp_axis_dev_name = 'none'
        self.tsamp_axis_dev_name = 'none'
        self.detector_axis_dev_name = 'none'
        self.num_axes_at_time_of_save = 0

        self.fw_max_pos = 9999
        self.fw_min_pos = -9999
        self.smr_max_pos = 9999
        self.smr_min_pos = -9999
        self.smt_max_pos = 9999
        self.smt_min_pos = -9999
        self.dr_max_pos = 9999
        self.dr_min_pos = -9999

        self.load_config(appDir, False)

        self.manual_position = 0 # 0 nm
        self.startpos = 0
        self.stoppos = 0
        self.steppos = 0.1

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
                print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
                raise RuntimeError('Could not load grating input UI file')

            self.dmw = QDialog(self) # pass parent window
            uic.loadUi(ui_file, self.dmw)

            self.dmw.setWindowTitle('Device Manager')
            self.dmw_list = ''


            self.UIEL_dmw_detector_qhbl = []
            self.UIEL_dmw_detector_qhbl.append(self.dmw.findChild(QHBoxLayout, "detector_combo_sublayout"))

            self.UIEL_dmw_mtn_ctrl_qhbl = []
            self.UIEL_dmw_mtn_ctrl_qhbl.append(self.dmw.findChild(QHBoxLayout, "mtn_ctrl_combo_sublayout"))

            self.UIEL_dmw_detector_qcb = []
            self.UIEL_dmw_detector_qcb.append(self.dmw.findChild(QComboBox, "samp_combo"))
            self.UIEL_dmw_detector_qcb[0].addItem("NO DEVICE SELECTED")
            self.UIEL_dmw_detector_model_qcb = []
            self.UIEL_dmw_detector_model_qcb.append(self.dmw.findChild(QComboBox, "samp_model_combo"))
            for device in Detector.SupportedDevices:
                self.UIEL_dmw_detector_model_qcb[0].addItem(device)

            self.UIEL_dmw_mtn_ctrl_qcb = []
            self.UIEL_dmw_mtn_ctrl_qcb.append(self.dmw.findChild(QComboBox, "mtn_combo"))
            self.UIEL_dmw_mtn_ctrl_qcb[0].addItem("NO DEVICE SELECTED")
            self.UIEL_dmw_mtn_ctrl_model_qcb = []
            self.UIEL_dmw_mtn_ctrl_model_qcb.append(self.dmw.findChild(QComboBox, "mtn_model_combo"))
            for device in MotionController.SupportedDevices:
                self.UIEL_dmw_mtn_ctrl_model_qcb[0].addItem(device)

            self.UIE_dmw_accept_qpb: QPushButton = self.dmw.findChild(QPushButton, "acc_button")
            self.UIE_dmw_accept_qpb.clicked.connect(self.connect_devices)
            self.UIE_dmw_dummy_qckbx: QCheckBox = self.dmw.findChild(QCheckBox, "dum_checkbox")
            self.UIE_dmw_dummy_qckbx.setChecked(len(self._startup_args) == 2)

            self.UIE_dmw_num_detectors_qsb: QSpinBox = self.dmw.findChild(QSpinBox, "num_detectors")
            self.UIE_dmw_num_detectors_qsb.valueChanged.connect(self.update_num_detectors_ui)
            self.num_detectors = 1

            self.UIE_dmw_num_motion_controllers_qsb: QSpinBox = self.dmw.findChild(QSpinBox, "num_motion_controllers")
            self.UIE_dmw_num_motion_controllers_qsb.valueChanged.connect(self.update_num_motion_controllers_ui)
            self.num_motion_controllers = 1

            self.UIE_dmw_detector_combo_qvbl: QVBoxLayout = self.dmw.findChild(QVBoxLayout, "detector_combo_layout")
            self.UIE_dmw_mtn_ctrl_combo_qvbl: QVBoxLayout = self.dmw.findChild(QVBoxLayout, "mtn_ctrl_combo_layout")
            self.UIE_dmw_load_bar_qpb: QProgressBar = self.dmw.findChild(QProgressBar, "loading_bar")

            self.devman_list_devices()

            # 
            self.dmw.show()

        self.application.processEvents()
        # self.SIGNAL_device_manager_ready.emit()

        if not self.dev_man_win_enabled:
            self.dev_man_win_enabled = True
            self.device_timer = QTimer()
            self.device_timer.timeout.connect(self.devman_list_devices)
            self.device_timer.start(1000)

    def closeEvent(self, event):
        answer = self.QMessageBoxQuestion('Exit Confirmation', "Are you sure you want to exit? All settings and values will be saved.")
        event.ignore()
        if answer == QtWidgets.QMessageBox.Yes:
            event.accept()

    def update_num_detectors_ui(self):
        if self.num_detectors != self.UIE_dmw_num_detectors_qsb.value():
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
                    s_combo.addItem('%s'%(dev))
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

        print('new detectors combo list len: %d'%(len(self.UIEL_dmw_detector_qcb)))

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
                s_combo.addItem("NO DEVICE SELECTED")
                for dev in self.dev_list:
                    s_combo.addItem('%s'%(dev))
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

        print('new mtn ctrls combo list len: %d'%(len(self.UIEL_dmw_mtn_ctrl_qcb)))

    def connect_devices(self):
        # application.setQuitOnLastWindowClosed(False)
        for i in range(self.num_detectors):
            if self.UIEL_dmw_detector_qcb[i].currentIndex() == 0:
                self.QMessageBoxInformation('Connection Failure', 'No detector was selected for entry #%d.'%(i))
                # application.setQuitOnLastWindowClosed(True)
                return
        for i in range(self.num_motion_controllers):
            if self.UIEL_dmw_mtn_ctrl_qcb[i].currentIndex() == 0:
                self.QMessageBoxInformation('Connection Failure', 'No motion controller was selected for entry #%d.'%(i))
                # application.setQuitOnLastWindowClosed(True)
                return
        
        if not self.connecting_devices:
            self.connect_devices = True

            self.UIE_dmw_accept_qpb.setEnabled(False)
            self.application.processEvents()
            self.dummy = self.UIE_dmw_dummy_qckbx.isChecked()

            self.connect_devices_thread.start()

    def _connect_devices(self, detectors_connected, mtn_ctrls_connected):
        self.connecting_devices = False
        self.UIE_dmw_accept_qpb.setEnabled(True)
        self.SIGNAL_devices_connection_check.emit(self.dummy, detectors_connected, mtn_ctrls_connected)

    def _connect_devices_failure_cleanup(self):
        self.connecting_devices = False
        self.UIE_dmw_accept_qpb.setEnabled(True)

    def _connect_devices_progress_anim(self, value):
        self.anim = QPropertyAnimation(targetObject=self.UIE_dmw_load_bar_qpb, propertyName=b"value")
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
                print('WARNING: STOPPING DEVICE TIMER!')
                self.device_timer.stop()
            # self.dmw.close()
            # self.anim.stop()
            self._show_main_gui(dummy)
            return
        
        # If we are here, then we have not automatically connected to all required devices. We must now enable the device manager.

        # self.UIE_dmw_explanation_ql.setText('Auto-connect failed.')  
        QMessageBox.warning(self.dmw, 'Connection Failure', 'Connection attempt has failed!\n%s'%(mtn_ctrls)) 

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
        # self.UIE_mcw_diff_order_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_max_pos_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_min_pos_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_zero_ofst_in_qdsb: QDoubleSpinBox = None
        # self.UIE_mcw_arm_length_in_qdsb: QDoubleSpinBox = None
        # self.UIE_mcw_incidence_ang_in_qdsb: QDoubleSpinBox = None
        # self.UIE_mcw_tangent_ang_in_qdsb: QDoubleSpinBox = None
        self.UIE_mcw_machine_conf_qpb: QPushButton = None

        self.UIE_mcw_steps_per_nm_qdsb: QDoubleSpinBox = None

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
        self.UIE_mgw_save_config_qpb: QPushButton = self.findChild(QPushButton, 'save_config_button')
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

        self.UIE_mgw_import_qa: QAction = self.findChild(QAction, "actionImport_Config")
        self.UIE_mgw_export_qa: QAction = self.findChild(QAction, "actionExport_Config")
        self.UIE_mgw_import_qa.triggered.connect(self.config_import)
        self.UIE_mgw_export_qa.triggered.connect(self.config_export)

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

        # Get axes combos.
        self.UIE_mgw_main_drive_axis_qcb: QComboBox = self.findChild(QComboBox, "main_drive_axis")
        self.UIE_mgw_filter_wheel_axis_qcb: QComboBox = self.findChild(QComboBox, "filter_wheel_axis")
        self.UIE_mgw_sample_rotation_axis_qcb: QComboBox = self.findChild(QComboBox, "sample_rot_axis")
        self.UIE_mgw_sample_translation_axis_qcb: QComboBox = self.findChild(QComboBox, "sample_trans_axis")
        self.UIE_mgw_detector_rotation_axis_qcb: QComboBox = self.findChild(QComboBox, "detector_axis")

        self.UIE_mgw_main_drive_axis_qcb.addItem('%s'%('Select Main Drive Axis'))
        self.UIE_mgw_filter_wheel_axis_qcb.addItem('%s'%('Select Filter Wheel Axis'))
        self.UIE_mgw_sample_rotation_axis_qcb.addItem('%s'%('Select Sample Rotation Axis'))
        self.UIE_mgw_sample_translation_axis_qcb.addItem('%s'%('Select Sample Translation Axis'))
        self.UIE_mgw_detector_rotation_axis_qcb.addItem('%s'%('Select Detector Rotation Axis'))

        self.UIE_mgw_main_drive_axis_qcb.currentIndexChanged.connect(self.mgw_axis_change_main)
        self.UIE_mgw_filter_wheel_axis_qcb.currentIndexChanged.connect(self.mgw_axis_change_filter)
        self.UIE_mgw_sample_rotation_axis_qcb.currentIndexChanged.connect(self.mgw_axis_change_rsamp)
        self.UIE_mgw_sample_translation_axis_qcb.currentIndexChanged.connect(self.mgw_axis_change_tsamp)
        self.UIE_mgw_detector_rotation_axis_qcb.currentIndexChanged.connect(self.mgw_axis_change_detector)

        # If anything has changed, we must use default values.
        if len(self.mtn_ctrls) != self.num_axes_at_time_of_save or self.mtn_ctrls[self.main_axis_index - 1].short_name() != self.main_axis_dev_name or self.mtn_ctrls[self.filter_axis_index - 1].short_name() != self.filter_axis_dev_name or self.mtn_ctrls[self.rsamp_axis_index - 1].short_name() != self.rsamp_axis_dev_name or self.mtn_ctrls[self.tsamp_axis_index - 1].short_name() != self.tsamp_axis_dev_name or self.mtn_ctrls[self.detector_axis_index - 1].short_name() != self.detector_axis_dev_name:

                print('Using default CONNECTIONS values.')
                self.main_axis_index = 1
                print('AA', self.main_axis_index)
                self.filter_axis_index = 0
                self.rsamp_axis_index = 0
                self.tsamp_axis_index = 0
                self.detector_axis_index = 0
            
        print('Amain axis idx:', self.main_axis_index)

        # Populate axes combos.
        print('Bmain axis idx:', self.main_axis_index)
        for dev in self.mtn_ctrls:
            print('Adding %s to config list.'%(dev))

            self.UIE_mgw_main_drive_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.short_name()))
            self.UIE_mgw_filter_wheel_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.short_name()))
            self.UIE_mgw_sample_rotation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.short_name()))
            self.UIE_mgw_sample_translation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.short_name()))
            self.UIE_mgw_detector_rotation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.short_name()))

        # Set the combo boxes to display the correct axes.
        print('Cmain axis idx:', self.main_axis_index)
        self.UIE_mgw_main_drive_axis_qcb.setCurrentIndex(self.main_axis_index)
        self.UIE_mgw_filter_wheel_axis_qcb.setCurrentIndex(self.filter_axis_index)
        self.UIE_mgw_sample_rotation_axis_qcb.setCurrentIndex(self.rsamp_axis_index)
        self.UIE_mgw_sample_translation_axis_qcb.setCurrentIndex(self.tsamp_axis_index)
        self.UIE_mgw_detector_rotation_axis_qcb.setCurrentIndex(self.detector_axis_index)
        
        # Update the actual axes pointers.
        print('Dmain axis idx:', self.main_axis_index)
        self.mgw_axis_change_main()
        self.mgw_axis_change_filter()
        self.mgw_axis_change_rsamp()
        self.mgw_axis_change_tsamp()
        self.mgw_axis_change_detector()

        # self.motion_controllers.main_drive_axis = self.mtn_ctrls[0]
        self.motion_controllers.main_drive_axis = self.mtn_ctrls[0]

        self.homing_started = False
        if not dummy:
            self.homing_started = True
            # self.disable_movement_sensitive_buttons(True)
            self.scan_status_update("HOMING")
            self.motion_controllers.main_drive_axis.home()
        self.current_position = -1900

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
        self.UIE_mgw_save_config_qpb.clicked.connect(self.show_window_machine_config)
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
        # self.UIE_mgw_preferences_qa.triggered.connect(self.preferences_triggered)
        self.UIE_mgw_pop_out_table_qa.toggled.connect(self.pop_out_table_toggled)
        self.UIE_mgw_pop_out_plot_qa.toggled.connect(self.pop_out_plot_toggled)
        self.UIE_mgw_about_licensing_qa.triggered.connect(self.open_licensing_hyperlink)
        self.UIE_mgw_about_manual_qa.triggered.connect(self.open_manual_hyperlink)
        self.UIE_mgw_about_source_qa.triggered.connect(self.open_source_hyperlink)

        self.UIE_mgw_home_qpb.clicked.connect(self.manual_home)

        # Other stuff.
        self.scan = scan.Scan(weakref.proxy(self))
        self.sm_scan = scan.ScanSM(weakref.proxy(self))
        self.dm_scan = scan.ScanDM(weakref.proxy(self))

        # self.timer = QTimer()
        # self.timer.timeout.connect(self.update_position_displays_thread.start())
        # self.timer.start(1000)
        self.update_position_displays_thread.start()

        # Set up the status bar.
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.UIE_mgw_copyright_ql: QLabel = QLabel()
        self.UIE_mgw_copyright_ql.setText('Copyright (c) Mit Bailey 2023')
        # self.sb_grating_density: QLabel = QLabel()
        # self.sb_zero_offset: QLabel = QLabel()
        # self.sb_inc_ang: QLabel = QLabel()
        # self.sb_tan_ang: QLabel = QLabel()
        # self.sb_arm_len: QLabel = QLabel()
        # self.sb_diff_order: QLabel = QLabel()
        # self.sb_conv_slope: QLabel = QLabel()
        # self.statusBar.addPermanentWidget(self.sb_grating_density)
        # self.statusBar.addPermanentWidget(self.sb_zero_offset)
        # self.statusBar.addPermanentWidget(self.sb_inc_ang)
        # self.statusBar.addPermanentWidget(self.sb_tan_ang)
        # self.statusBar.addPermanentWidget(self.sb_arm_len)
        # self.statusBar.addPermanentWidget(self.sb_diff_order)
        # self.statusBar.addPermanentWidget(self.sb_conv_slope)
        self.statusBar.addPermanentWidget(self.UIE_mgw_copyright_ql)
        # self.update_status_bar_grating_equation_values()

        self.manual_position = (self.UIE_mgw_pos_qdsb.value() + self.zero_ofst)
        self.startpos = (self.UIE_mgw_start_qdsb.value() + self.zero_ofst)
        self.stoppos = (self.UIE_mgw_stop_qdsb.value() + self.zero_ofst)

        self.UIE_mgw_fw_mancon_position_set_qsb: QSpinBox = self.findChild(QSpinBox, 'filter_wheel_pos_set_spinbox')
        self.UIE_mgw_fw_mancon_move_pos_qpb: QPushButton = self.findChild(QPushButton, 'filter_wheel_move_pos_button')
        self.UIE_mgw_fw_mancon_home_qpb: QPushButton = self.findChild(QPushButton, 'filter_wheel_home_button')
        self.UIE_mgw_fw_add_rule_qpb: QPushButton = self.findChild(QPushButton, 'filter_wheel_add_rule_button')
        self.UIE_mgw_fw_add_rule_qpb.clicked.connect(self.new_filter_wheel_rule)
        
        self.cw_rules = [] # List to hold the actual rules.
        self.UIEL_mgw_fw_rules_qvbl = []
        self.UIEL_mgw_fw_rules_set_qdsb = []
        self.UIEL_mgw_fw_rules_step_qsb = []
        self.UIEL_mgw_fw_rules_remove_qpb = []
        self.UIEL_mgw_fw_rules_enact_qpb = []
        self.UIE_mgw_fw_rules_qsa: QVBoxLayout = self.findChild(QVBoxLayout, 'scroll_area_layout')
        self.UIEL_mgw_fw_misc_tuples_ql = []
        self.new_filter_wheel_rule()

        # Sample Movement UI
        self.UIE_mgw_sm_rpos_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'sample_rotate_spin')
        self.UIE_mgw_sm_tpos_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'sample_trans_spin')

        self.UIE_mgw_sm_rhome_qpb: QPushButton = self.findChild(QPushButton, 'sample_rotate_home_button')
        self.UIE_mgw_sm_rhome_qpb.clicked.connect(self.manual_home_smr)
        self.UIE_mgw_sm_thome_qpb: QPushButton = self.findChild(QPushButton, 'sample_trans_home_button')
        self.UIE_mgw_sm_thome_qpb.clicked.connect(self.manual_home_smt)

        self.UIE_mgw_sm_rmove_qpb: QPushButton = self.findChild(QPushButton, 'sample_rotate_move_button')
        self.UIE_mgw_sm_rmove_qpb.clicked.connect(self.move_to_position_button_pressed_sr)
        self.UIE_mgw_sm_tmove_qpb: QPushButton = self.findChild(QPushButton, 'sample_trans_move_button')
        self.UIE_mgw_sm_rmove_qpb.clicked.connect(self.move_to_position_button_pressed_st)

        # Detector Movement UI
        self.UIE_mgw_dm_rpos_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'detector_rotate_spin')

        self.UIE_mgw_dm_rhome_qpb: QPushButton = self.findChild(QPushButton, 'detector_rotate_home_button')
        self.UIE_mgw_dm_rhome_qpb.clicked.connect(self.manual_home_dmr)

        self.UIE_mgw_dm_rmove_qpb: QPushButton = self.findChild(QPushButton, 'detector_rotate_move_button')
        self.UIE_mgw_dm_rmove_qpb.clicked.connect(self.move_to_position_button_pressed_dr)

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

        self.UIE_mgw_mda_qw: QWidget = self.findChild(QWidget, 'main_drive_area')
        self.UIE_mgw_mda_collapse_qpb: QPushButton = self.findChild(QPushButton, 'main_drive_area_collap')
        self.mda_collapsed = False
        self.UIE_mgw_mda_collapse_qpb.clicked.connect(self.collapse_mda)
        
        self.UIE_mgw_fwa_qw: QWidget = self.findChild(QWidget, 'filter_wheel_area')
        self.UIE_mgw_fwa_collapse_qpb: QPushButton = self.findChild(QPushButton, 'filter_wheel_area_collap')
        self.fwa_collapsed = False
        self.UIE_mgw_fwa_collapse_qpb.clicked.connect(self.collapse_fwa)
        
        self.UIE_mgw_sa_qw: QWidget = self.findChild(QWidget, 'sample_area')
        self.UIE_mgw_sa_collapse_qpb: QPushButton = self.findChild(QPushButton, 'sample_area_collap')
        self.sa_collapsed = False
        self.UIE_mgw_sa_collapse_qpb.clicked.connect(self.collapse_sa)
        
        self.UIE_mgw_da_qw: QWidget = self.findChild(QWidget, 'detector_area')
        self.UIE_mgw_da_collapse_qpb: QPushButton = self.findChild(QPushButton, 'detector_area_collap')
        self.da_collapsed = False
        self.UIE_mgw_da_collapse_qpb.clicked.connect(self.collapse_da)
        
        self.UIE_mgw_sm_scan_type_qcb: QComboBox = self.findChild(QComboBox, 'scan_type_combo')
        self.UIE_mgw_sm_scan_type_qcb.addItem('Rotation')
        self.UIE_mgw_sm_scan_type_qcb.addItem('Translation')
        self.UIE_mgw_sm_scan_type_qcb.addItem('Theta2Theta')
        self.UIE_mgw_sm_start_set_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'start_set_spinbox_2')
        self.UIE_mgw_sm_end_set_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'end_set_spinbox_2')
        self.UIE_mgw_sm_step_set_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'step_set_spinbox_2')
        self.UIE_mgw_sm_scan_repeats_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'scan_repeats_3')
        self.UIE_mgw_sm_begin_scan_qpb: QPushButton = self.findChild(QPushButton, 'begin_scan_button_3')
        self.UIE_mgw_sm_begin_scan_qpb.clicked.connect(self.scan_sm_button_pressed)
        self.UIE_mgw_sm_end_scan_qpb: QPushButton = self.findChild(QPushButton, 'stop_scan_button_3')
        self.UIE_mgw_sm_end_scan_qpb.clicked.connect(self.stop_scan_button_pressed)

        self.UIE_mgw_dm_start_set_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'start_set_spinbox_3')
        self.UIE_mgw_dm_end_set_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'end_set_spinbox_3')
        self.UIE_mgw_dm_step_set_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'step_set_spinbox_3')
        self.UIE_mgw_dm_scan_repeats_qdsb: QDoubleSpinBox = self.findChild(QDoubleSpinBox, 'scan_repeats_4')
        self.UIE_mgw_dm_begin_scan_qpb: QPushButton = self.findChild(QPushButton, 'begin_scan_button_4')
        self.UIE_mgw_dm_begin_scan_qpb.clicked.connect(self.scan_dm_button_pressed)
        self.UIE_mgw_dm_end_scan_qpb: QPushButton = self.findChild(QPushButton, 'stop_scan_button_4')
        self.UIE_mgw_dm_end_scan_qpb.clicked.connect(self.stop_scan_button_pressed)

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
        movement_sensitive_list.append(self.UIE_mgw_sample_translation_axis_qcb)
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

        self.movement_sensitive_metalist = []
        self.movement_sensitive_metalist.append(movement_sensitive_list)
        self.movement_sensitive_metalist.append(self.UIEL_mgw_fw_rules_set_qdsb)
        self.movement_sensitive_metalist.append(self.UIEL_mgw_fw_rules_step_qsb)
        self.movement_sensitive_metalist.append(self.UIEL_mgw_fw_rules_remove_qpb)
        self.movement_sensitive_metalist.append(self.UIEL_mgw_fw_rules_enact_qpb)

        # This is where we disable the scroll function for all spin and combo boxes, because its dumb.
        uiel = self.findChildren(QDoubleSpinBox)
        uiel += self.findChildren(QSpinBox)
        uiel += self.findChildren(QComboBox)
        for uie in uiel:
            uie.installEventFilter(self)

        # Setup the steps_per_nm of the main axis.
        self.UIE_mcw_steps_per_nm_ql = None
        self.calculate_and_apply_steps_per_nm()

        self.main_gui_booted = True
        self.show()  
        self.dmw.close()

    def config_import(self):
        loadFileName, _ = QFileDialog.getOpenFileName(self, "Load CSV", directory=os.path.expanduser('~/Documents') + '/mcpherson_mmc/s_d.csv', filter='*.csv')
        fileInfo = QFileInfo(loadFileName)
        self.load_config(fileInfo.absoluteFilePath(), True)

    def config_export(self):
        savFileName, _ = QFileDialog.getSaveFileName(self, "Save CSV", directory=os.path.expanduser('~/Documents') + '/mcpherson_mmc/s_d.csv', filter='*.csv')
        fileInfo = QFileInfo(savFileName)
        self.save_config(fileInfo.absoluteFilePath(), True) 
        
    def save_config(self, path: str, is_export: bool):
        save_config(path, is_export, self.mes_sign, self.autosave_data_bool, self.data_save_directory, self.model_index, self.grating_density, self.zero_ofst, self.max_pos, self.min_pos, self.main_axis_index, self.filter_axis_index, self.rsamp_axis_index, self.tsamp_axis_index, self.detector_axis_index, self.main_axis_dev_name, self.filter_axis_dev_name, self.rsamp_axis_dev_name, self.tsamp_axis_dev_name, self.detector_axis_dev_name, len(self.mtn_ctrls), self.fw_max_pos, self.fw_min_pos, self.smr_max_pos, self.smr_min_pos, self.smt_max_pos, self.smt_min_pos, self.dr_max_pos, self.dr_min_pos)

    def load_config(self, path: str, is_import: bool):
        # Replaces default grating equation values with the values found in the config.ini file.
        try:
            load_dict = load_config(path, is_import)
        except Exception as e:
            print("The following exception occurred while attempting to load configuration file: %s"%(e))
            if not is_import:
                print("Attempting config file default reset.")
                try:
                    reset_config(path)
                    load_dict = load_config(path, is_import)
                except Exception as e2:
                    print("Configuration file recovery failed (exception: %s). Unable to load configuration file. Exiting."%(e2))
                    sys.exit(43)
            else:
                print("Config import failure.")
                
        self.mes_sign = load_dict['measurementSign']
        self.autosave_data_bool = load_dict['autosaveData']
        self.data_save_directory = load_dict['dataSaveDirectory']
        # self.grating_combo_lstr = load_dict["gratingDensities"]
        self.model_index = load_dict["modelIndex"]
        self.grating_density = load_dict["gratingDensity"]
        # self.diff_order = load_dict["diffractionOrder"]
        self.zero_ofst = load_dict["zeroOffset"]
        # self.incidence_ang = load_dict["incidenceAngle"]
        # self.tangent_ang = load_dict["tangentAngle"]
        # self.arm_length = load_dict["armLength"]
        self.max_pos = load_dict["maxPosition"]
        self.min_pos = load_dict["minPosition"]
        # self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx])

        self.main_axis_index = load_dict['mainAxisIndex']
        print('LOADED MAIN_AXIS_INDEX VALUE OF:', self.main_axis_index)
        self.filter_axis_index = load_dict['filterAxisIndex']
        self.rsamp_axis_index = load_dict['rsampAxisIndex']
        self.tsamp_axis_index = load_dict['tsampAxisIndex']
        self.detector_axis_index = load_dict['detectorAxisIndex']

        self.main_axis_dev_name = load_dict['mainAxisName']
        self.filter_axis_dev_name = load_dict['filterAxisName']
        self.rsamp_axis_dev_name = load_dict['rsampAxisName']
        self.tsamp_axis_dev_name = load_dict['tsampAxisName']
        self.detector_axis_dev_name = load_dict['detectorAxisName']
        self.num_axes_at_time_of_save = load_dict['numAxes']

        self.fw_max_pos = load_dict['fwMax']
        self.fw_min_pos = load_dict['fwMin']
        self.smr_max_pos = load_dict['smrMax']
        self.smr_min_pos = load_dict['smrMin']
        self.smt_max_pos = load_dict['smrMax']
        self.smt_min_pos = load_dict['smrMin']
        self.dr_max_pos = load_dict['drMax']
        self.dr_min_pos = load_dict['drMin']

    def collapse_mda(self):
        print('collapse_mda:', self.mda_collapsed)
        self.mda_collapsed = not self.mda_collapsed
        print('collapse_mda:', self.mda_collapsed)
        self.UIE_mgw_mda_qw.setVisible(not self.mda_collapsed)
        if self.mda_collapsed:
            self.UIE_mgw_mda_collapse_qpb.setText('<')
        else:
            self.UIE_mgw_mda_collapse_qpb.setText('v')

    def collapse_fwa(self):
        print('collapse_fwa:', self.fwa_collapsed)
        self.fwa_collapsed = not self.fwa_collapsed
        print('collapse_fwa:', self.fwa_collapsed)
        self.UIE_mgw_fwa_qw.setVisible(not self.fwa_collapsed)
        if self.fwa_collapsed:
            self.UIE_mgw_fwa_collapse_qpb.setText('<')
        else:
            self.UIE_mgw_fwa_collapse_qpb.setText('v')

    def collapse_sa(self):
        print('collapse_sa:', self.sa_collapsed)
        self.sa_collapsed = not self.sa_collapsed
        print('collapse_sa:', self.sa_collapsed)
        self.UIE_mgw_sa_qw.setVisible(not self.sa_collapsed)
        if self.sa_collapsed:
            self.UIE_mgw_sa_collapse_qpb.setText('<')
        else:
            self.UIE_mgw_sa_collapse_qpb.setText('v')

    def collapse_da(self):
        print('collapse_da:', self.da_collapsed)
        self.da_collapsed = not self.da_collapsed
        print('collapse_da:', self.da_collapsed)
        self.UIE_mgw_da_qw.setVisible(not self.da_collapsed)
        if self.da_collapsed:
            self.UIE_mgw_da_collapse_qpb.setText('<')
        else:
            self.UIE_mgw_da_collapse_qpb.setText('v')

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
        remove_button.clicked.connect(partial(self.del_filter_wheel_rule, self.UIEL_mgw_fw_rules_enact_qpb[-1]))
        print('RULE ADDED AT INDEX:', len(self.UIEL_mgw_fw_rules_remove_qpb) - 1)

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
            print('FAILED TO FIND SENDER INDEX!')
            return

        # sender.
        print('SENDER:')
        print(sender)

        dspin = self.UIEL_mgw_fw_rules_set_qdsb[sidx]
        spin = self.UIEL_mgw_fw_rules_step_qsb[sidx]

        print(dspin)
        print(spin)
        print('Values are %f and %d.'%(dspin.value(), spin.value()))

    def del_filter_wheel_rule(self, index_finder):
        index = self.UIEL_mgw_fw_rules_enact_qpb.index(index_finder)

        print('RULE REMOVAL AT INDEX:', index)

        self.UIEL_mgw_fw_rules_enact_qpb[index].setParent(None)
        del self.UIEL_mgw_fw_rules_enact_qpb[index]

        print('len', len(self.UIEL_mgw_fw_rules_remove_qpb))
        print('index', index)
        self.UIEL_mgw_fw_rules_remove_qpb[index].setParent(None)
        del self.UIEL_mgw_fw_rules_remove_qpb[index]

        self.UIEL_mgw_fw_rules_set_qdsb[index].setParent(None)
        del self.UIEL_mgw_fw_rules_set_qdsb[index]

        self.UIEL_mgw_fw_rules_step_qsb[index].setParent(None)
        del self.UIEL_mgw_fw_rules_step_qsb[index]

        self.UIEL_mgw_fw_misc_tuples_ql[index][0].setParent(None)
        self.UIEL_mgw_fw_misc_tuples_ql[index][1].setParent(None)
        del self.UIEL_mgw_fw_misc_tuples_ql[index]
        
        self.UIE_mgw_fw_rules_qsa.removeItem(self.UIEL_mgw_fw_rules_qvbl[index])
        del self.UIEL_mgw_fw_rules_qvbl[index]

    def devman_list_devices(self):
        self.dev_list = mw.find_all_ports()

        dev_list_str = ''
        for dev in self.dev_list:
            dev_list_str += '%s\n'%(dev)

        if (self.dmw_list != "~DEVICE LIST~\n" + dev_list_str):
            for i in range(self.num_detectors):
                self.UIEL_dmw_detector_qcb[i].clear()
                self.UIEL_dmw_detector_qcb[i].addItem('NO DEVICE SELECTED')
                self.UIEL_dmw_detector_qcb[i].setCurrentIndex(0)

                for dev in self.dev_list:
                    self.UIEL_dmw_detector_qcb[i].addItem('%s'%(dev))

            for i in range(self.num_motion_controllers):
                self.UIEL_dmw_mtn_ctrl_qcb[i].clear()
                self.UIEL_dmw_mtn_ctrl_qcb[i].addItem('NO DEVICE SELECTED')
                self.UIEL_dmw_mtn_ctrl_qcb[i].setCurrentIndex(0)

                for dev in self.dev_list:
                    self.UIEL_dmw_mtn_ctrl_qcb[i].addItem('%s'%(dev))

            self.dmw_list = "~DEVICE LIST~\n" + dev_list_str

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
            ofile.write('# Steps/mm: %f\n'%(metadata['steps_per_value']))
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

    def manual_home(self):
        self.scan_status_update("HOMING")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        self.motion_controllers.main_drive_axis.home()

    def manual_home_smr(self):
        self.scan_status_update("HOMING SR")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        self.motion_controllers.sample_rotation_axis.home()

    def manual_home_smt(self):
        self.scan_status_update("HOMING ST")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        self.motion_controllers.sample_translation_axis.home()

    def manual_home_dmr(self):
        self.scan_status_update("HOMING DR")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        self.motion_controllers.detector_rotation_axis.home()

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

    def scan_data_update(self, scan_idx: int, which_detector: int, xdata: float, ydata: float):
        if which_detector == 0:
            self.table.insertDataAt(scan_idx, xdata, ydata)

    def scan_data_complete(self, scan_idx: int, scan_class: str):
        self.table.markInsertFinished(scan_idx)
        self.table.updateTableDisplay()
        if self.scan_repeats.value() > 0:
            if scan_class == 'main':
                self.scan_repeats.setValue(self.scan_repeats.value() - 1)
                self.scan_button_pressed()
            elif scan_class == 'sample':
                self.UIE_mgw_sm_scan_repeats_qdsb.setValue(self.UIE_mgw_sm_scan_repeats_qdsb.value() - 1)
                self.scan_sm_button_pressed()
            elif scan_class == 'detector':
                self.UIE_mgw_dm_scan_repeats_qdsb.setValue(self.UIE_mgw_dm_scan_repeats_qdsb.value() - 1)
                self.scan_dm_button_pressed()
            else:
                print('ERROR: Unknown scan class %s.'%(scan_class))

    def update_position_displays(self):
        self.UIE_mgw_currpos_nm_disp_ql.setText('<b><i>%3.4f</i></b>'%(((self.current_position)) - self.zero_ofst))

    def scan_button_pressed(self):
        if not self.scanRunning:
            self.scanRunning = True
            self.disable_movement_sensitive_buttons(True)
            self.scan.start()

    def scan_sm_button_pressed(self):
        if not self.scanRunning:
            self.scanRunning = True
            self.disable_movement_sensitive_buttons(True)
            self.sm_scan.start()

    def scan_dm_button_pressed(self):
        if not self.scanRunning:
            self.scanRunning = True
            self.disable_movement_sensitive_buttons(True)
            self.dm_scan.start()

    def stop_scan_button_pressed(self):
        if self.scanRunning:
            self.scanRunning = False

    def move_to_position_button_pressed(self):
        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        print("Steps per nm: " + str(self.motion_controllers.main_drive_axis.get_steps_per_value()))
        print("Manual position: " + str(self.manual_position))
        print("Move to position button pressed, moving to %d nm"%(self.manual_position))
        pos = int((self.UIE_mgw_pos_qdsb.value() + self.zero_ofst))

        try:
            self.motion_controllers.main_drive_axis.move_to(pos, False)
        except Exception as e:
            QMessageBox.critical(self, 'Move Failure', 'Main drive axis failed to move: %s.'%(e))
            pass

    def move_to_position_button_pressed_sr(self):
        if (self.moving):
            print('ALREADY MOVING!')
            return
        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        pos = self.UIE_mgw_sm_rpos_qdsb.value()

        print("Move to position button (SR) pressed, moving to step %d"%(pos))
        try:
            self.motion_controllers.sample_rotation_axis.move_to(pos, False)
        except Exception as e:
            QMessageBox.critical(self, 'Move Failure', 'Sample rotation axis failed to move: %s'%(e))
            pass

    def move_to_position_button_pressed_st(self):
        if (self.moving):
            print('ALREADY MOVING!')
            return
        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        pos = self.UIE_mgw_sm_tpos_qdsb.value()

        print("Move to position button (ST) pressed, moving to step %d"%(pos))
        try:
            self.motion_controllers.sample_translation_axis.move_to(pos, False)
        except Exception as e:
            QMessageBox.critical(self, 'Move Failure', 'Sample translation axis failed to move: %s'%(e))
            pass

    def move_to_position_button_pressed_dr(self):
        if (self.moving):
            print('ALREADY MOVING!')
            return

        self.moving = True
        self.disable_movement_sensitive_buttons(True)

        pos = self.UIE_mgw_dm_rpos_qdsb.value()

        print("Move to position button (DR) pressed, moving to step %d"%(pos))
        try:
            self.motion_controllers.detector_rotation_axis.move_to(pos, False)
        except Exception as e:
            QMessageBox.critical(self, 'Move Failure', 'Detector rotation axis failed to move: %s'%(e))
            pass

    def start_changed(self):
        print("Start changed to: %s mm"%(self.UIE_mgw_start_qdsb.value()))
        self.startpos = (self.UIE_mgw_start_qdsb.value() + self.zero_ofst)
        print(self.startpos)

    def stop_changed(self):
        print("Stop changed to: %s mm"%(self.UIE_mgw_stop_qdsb.value()))
        self.stoppos = (self.UIE_mgw_stop_qdsb.value() + self.zero_ofst)
        print(self.stoppos)

    def step_changed(self):
        print("Step changed to: %s mm"%(self.UIE_mgw_step_qdsb.value()))
        self.steppos = (self.UIE_mgw_step_qdsb.value())
        print(self.steppos)

    def manual_pos_changed(self):
        print("Manual position changed to: %s mm"%(self.UIE_mgw_pos_qdsb.value()))
        self.manual_position = (self.UIE_mgw_pos_qdsb.value() + self.zero_ofst)

    def manual_pos_changed_sr(self):
        print('Manual position (SR) changed to: %d steps'%(self.UIE_mgw_sm_rpos))

    def update_model_index(self):
        self.model_index = self.UIE_mcw_model_qcb.currentIndex()

    def show_window_machine_config(self):
        if self.machine_conf_win is None:
            ui_file_name = exeDir + '/ui/machine_config.ui'
            ui_file = QFile(ui_file_name)
            if not ui_file.open(QIODevice.ReadOnly):
                print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
                raise RuntimeError('Could not load grating input UI file')
            
            self.machine_conf_win = QDialog(self) # pass parent window
            uic.loadUi(ui_file, self.machine_conf_win)

            self.machine_conf_win.setWindowTitle('Monochromator Configuration')

            self.UIE_mcw_model_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, 'models')
            self.UIE_mcw_model_qcb.addItems(McPherson.MONO_MODELS)
            self.UIE_mcw_model_qcb.setCurrentIndex(self.model_index)
            self.UIE_mcw_model_qcb.currentIndexChanged.connect(self.update_model_index)
            # print(self.current_grating_idx)
            # self.UIE_mcw_grating_qdsb.setCurrentIndex(self.current_grating_idx)

            self.UIE_mcw_grating_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'grating_density')
            self.UIE_mcw_grating_qdsb.setValue(self.grating_density)
            # self.UIE_mcw_grating_qdsb.addItems(self.grating_combo_lstr)
            # print(self.current_grating_idx)
            # self.UIE_mcw_grating_qdsb.setCurrentIndex(self.current_grating_idx)
            # self.UIE_mcw_grating_qdsb.activated.connect(self.new_grating_item)
            
            self.UIE_mcw_zero_ofst_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'zero_offset_in')
            self.UIE_mcw_zero_ofst_in_qdsb.setValue(self.zero_ofst)
            
            # self.UIE_mcw_incidence_ang_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'incidence_angle_in')
            # self.UIE_mcw_incidence_ang_in_qdsb.setValue(self.incidence_ang)
            
            # self.UIE_mcw_tangent_ang_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'tangent_angle_in')
            # self.UIE_mcw_tangent_ang_in_qdsb.setValue(self.tangent_ang)

            # self.UIE_mcw_arm_length_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'arm_length_in')
            # self.UIE_mcw_arm_length_in_qdsb.setValue(self.arm_length)

            # self.UIE_mcw_diff_order_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'diff_order_in')
            # self.UIE_mcw_diff_order_in_qdsb.setValue(self.diff_order)

            self.UIE_mcw_max_pos_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'max_pos_sbox')
            self.UIE_mcw_max_pos_in_qdsb.setValue(self.max_pos)

            self.UIE_mcw_min_pos_in_qdsb = self.machine_conf_win.findChild(QDoubleSpinBox, 'min_pos_sbox')
            self.UIE_mcw_min_pos_in_qdsb.setValue(self.min_pos)

            self.UIE_mcw_machine_conf_qpb = self.machine_conf_win.findChild(QPushButton, 'update_conf_btn')
            self.UIE_mcw_machine_conf_qpb.clicked.connect(self.apply_machine_conf)

            self.UIE_mcw_steps_per_nm_ql = self.machine_conf_win.findChild(QLabel, 'steps_per_nm')
            steps_per_nm = self.motion_controllers.main_drive_axis.get_steps_per_value()
            if steps_per_nm == 0.0:
                self.UIE_mcw_steps_per_nm_ql.setText('NOT CALCULATED')
            else:
                self.UIE_mcw_steps_per_nm_ql.setText(str(steps_per_nm))

            self.UIE_mcw_accept_qpb = self.machine_conf_win.findChild(QPushButton, 'mcw_accept')
            self.UIE_mcw_accept_qpb.clicked.connect(self.accept_mcw)

            # Get axes combos.
            self.UIE_mcw_main_drive_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "main_drive_axis_combo")
            self.UIE_mcw_filter_wheel_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "filter_wheel_axis_combo")
            self.UIE_mcw_sample_rotation_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "sample_rotation_axis_combo")
            self.UIE_mcw_sample_translation_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "sample_translation_axis_combo")
            self.UIE_mcw_detector_rotation_axis_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, "detector_rotation_axis_combo")

            # self.UIE_mcw_model_qcb: QComboBox = self.machine_conf_win.findChild(QComboBox, 'model_combo')

            none = 'No Device Selected'
            self.UIE_mcw_main_drive_axis_qcb.addItem('%s'%(none))
            self.UIE_mcw_filter_wheel_axis_qcb.addItem('%s'%(none))
            self.UIE_mcw_sample_rotation_axis_qcb.addItem('%s'%(none))
            self.UIE_mcw_sample_translation_axis_qcb.addItem('%s'%(none))
            self.UIE_mcw_detector_rotation_axis_qcb.addItem('%s'%(none))

            # Populate axes combos.
            print(self.mtn_ctrls)
            for dev in self.mtn_ctrls:
                print('Adding %s to config list.'%(dev))

                self.UIE_mcw_main_drive_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))
                self.UIE_mcw_filter_wheel_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))
                self.UIE_mcw_sample_rotation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))
                self.UIE_mcw_sample_translation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))
                self.UIE_mcw_detector_rotation_axis_qcb.addItem('%s: %s'%(dev.port_name(), dev.long_name()))

                self.UIE_mcw_main_drive_axis_qcb.setCurrentIndex(1)

            self.UIE_mcw_fw_steps_per_rot_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'fw_steps_per_deg')
            self.UIE_mcw_fw_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'fw_max')
            self.UIE_mcw_fw_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'fw_min')
            self.UIE_mcw_sm_steps_per_rot_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'smr_steps_per_deg')
            self.UIE_mcw_smr_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'smr_max')
            self.UIE_mcw_smr_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'smr_min')
            self.UIE_mcw_sm_steps_per_trans_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'smt_steps_per_deg')
            self.UIE_mcw_smt_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'smt_max')
            self.UIE_mcw_smt_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'smt_min')
            self.UIE_mcw_dr_steps_per_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'dr_steps_per_deg')
            self.UIE_mcw_dr_max_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'dr_max')
            self.UIE_mcw_dr_min_qdsb: QDoubleSpinBox = self.machine_conf_win.findChild(QDoubleSpinBox, 'dr_min')

        self.UIE_mcw_main_drive_axis_qcb.setCurrentIndex(self.main_axis_index)
        self.UIE_mcw_filter_wheel_axis_qcb.setCurrentIndex(self.filter_axis_index)
        self.UIE_mcw_sample_rotation_axis_qcb.setCurrentIndex(self.rsamp_axis_index)
        self.UIE_mcw_sample_translation_axis_qcb.setCurrentIndex(self.tsamp_axis_index)
        self.UIE_mcw_detector_rotation_axis_qcb.setCurrentIndex(self.detector_axis_index)

        self.UIE_mcw_min_pos_in_qdsb.setValue(self.max_pos)
        self.UIE_mcw_max_pos_in_qdsb.setValue(self.min_pos)
        self.UIE_mcw_fw_max_qdsb.setValue(self.fw_max_pos)
        self.UIE_mcw_fw_min_qdsb.setValue(self.fw_min_pos)
        self.UIE_mcw_smr_max_qdsb.setValue(self.smr_max_pos)
        self.UIE_mcw_smr_min_qdsb.setValue(self.smr_min_pos)
        self.UIE_mcw_smt_max_qdsb.setValue(self.smt_max_pos)
        self.UIE_mcw_smt_min_qdsb.setValue(self.smt_min_pos)
        self.UIE_mcw_dr_max_qdsb.setValue(self.dr_max_pos)
        self.UIE_mcw_dr_min_qdsb.setValue(self.dr_min_pos)

        self.machine_conf_win.exec() # synchronously run this window so parent window is disabled
        print('Exec done')

    def update_movement_limits(self):
        self.motion_controllers.main_drive_axis.set_limits(self.max_pos, self.min_pos)

        self.UIE_mgw_pos_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_pos_qdsb.setMinimum(self.min_pos)

        self.UIE_mgw_start_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_start_qdsb.setMinimum(self.min_pos)

        self.UIE_mgw_stop_qdsb.setMaximum(self.max_pos)
        self.UIE_mgw_stop_qdsb.setMinimum(self.min_pos)

    def apply_machine_conf(self):
        # idx = self.UIE_mcw_grating_qdsb.currentIndex()
        # if idx < len(self.grating_combo_lstr) - 1:
            # self.current_grating_idx = idx
        self.grating_density = self.UIE_mcw_grating_qdsb.value()
        print(self.grating_density)
        # self.diff_order = int(self.UIE_mcw_diff_order_in_qdsb.value())
        # self.max_pos = self.UIE_mcw_max_pos_in_qdsb.value()
        # self.min_pos = self.UIE_mcw_min_pos_in_qdsb.value()

        self.update_movement_limits()

        self.zero_ofst = self.UIE_mcw_zero_ofst_in_qdsb.value()

        self.calculate_and_apply_steps_per_nm()

    def calculate_and_apply_steps_per_nm(self):
        steps_per_rev = McPherson.MONO_STEPS_PER_REV[McPherson.MONO_MODELS[self.model_index]]

        try:
            steps_per_value = McPherson.get_steps_per_nm(steps_per_rev, McPherson.MONO_MODELS[self.model_index], self.grating_density)
        except Exception as e:
            print(e)
            print('Failed to update values. Please keep in mind that Models 272 and Model 608 Pre-Disperser only accepts specific grating densities.')
            pass

        print('Settings steps_per_value:', self.motion_controllers.main_drive_axis.set_steps_per_value(steps_per_value))
        if self.UIE_mcw_steps_per_nm_ql is not None:
            self.UIE_mcw_steps_per_nm_ql.setText(str(steps_per_value))

    def mgw_axis_change_main(self):
        self.main_axis_index = self.UIE_mgw_main_drive_axis_qcb.currentIndex()
        self.motion_controllers.main_drive_axis = self.mtn_ctrls[self.main_axis_index - 1]
        self.main_axis_dev_name = self.motion_controllers.main_drive_axis.short_name()

    def mgw_axis_change_filter(self):
        self.filter_axis_index = self.UIE_mgw_filter_wheel_axis_qcb.currentIndex()
        self.motion_controllers.filter_wheel_axis = self.mtn_ctrls[self.filter_axis_index - 1]
        self.filter_axis_dev_name = self.motion_controllers.filter_wheel_axis.short_name()

    def mgw_axis_change_rsamp(self):
        self.rsamp_axis_index = self.UIE_mgw_sample_rotation_axis_qcb.currentIndex()
        self.motion_controllers.sample_rotation_axis = self.mtn_ctrls[self.rsamp_axis_index - 1]
        self.rsamp_axis_dev_name = self.motion_controllers.sample_rotation_axis.short_name()

    def mgw_axis_change_tsamp(self):
        self.tsamp_axis_index = self.UIE_mgw_sample_translation_axis_qcb.currentIndex()
        self.motion_controllers.sample_translation_axis = self.mtn_ctrls[self.tsamp_axis_index - 1]
        self.tsamp_axis_dev_name = self.motion_controllers.sample_translation_axis.short_name()

    def mgw_axis_change_detector(self):
        self.detector_axis_index = self.UIE_mgw_detector_rotation_axis_qcb.currentIndex()
        self.motion_controllers.detector_rotation_axis = self.mtn_ctrls[self.detector_axis_index - 1]
        self.detector_axis_dev_name = self.motion_controllers.detector_rotation_axis.short_name()

    def accept_mcw(self):
        print('~~MACHINE CONFIGURATION ACCEPT CALLED:')
        print('~Main Drive')
        print(self.UIE_mcw_main_drive_axis_qcb.currentText())
        print('~Color Wheel Axis')
        print(self.UIE_mcw_filter_wheel_axis_qcb.currentText())
        print('~Sample Axes')
        print(self.UIE_mcw_sample_rotation_axis_qcb.currentText())
        print(self.UIE_mcw_sample_translation_axis_qcb.currentText())
        print('~Detector Rotation Axis')
        print(self.UIE_mcw_detector_rotation_axis_qcb.currentText())
        print('~~')

        self.main_axis_index = self.UIE_mcw_main_drive_axis_qcb.currentIndex()
        self.filter_axis_index = self.UIE_mcw_filter_wheel_axis_qcb.currentIndex()
        self.rsamp_axis_index = self.UIE_mcw_sample_rotation_axis_qcb.currentIndex()
        self.tsamp_axis_index = self.UIE_mcw_sample_translation_axis_qcb.currentIndex()
        self.detector_axis_index = self.UIE_mcw_detector_rotation_axis_qcb.currentIndex()

        self.UIE_mgw_main_drive_axis_qcb.setCurrentIndex(self.main_axis_index)
        self.UIE_mgw_filter_wheel_axis_qcb.setCurrentIndex(self.filter_axis_index)
        self.UIE_mgw_sample_rotation_axis_qcb.setCurrentIndex(self.rsamp_axis_index)
        self.UIE_mgw_sample_translation_axis_qcb.setCurrentIndex(self.tsamp_axis_index)
        self.UIE_mgw_detector_rotation_axis_qcb.setCurrentIndex(self.detector_axis_index)

        self.motion_controllers.main_drive_axis = self.mtn_ctrls[self.main_axis_index - 1]
        self.motion_controllers.filter_wheel_axis = self.mtn_ctrls[self.filter_axis_index - 1]
        self.motion_controllers.sample_rotation_axis = self.mtn_ctrls[self.rsamp_axis_index - 1]
        self.motion_controllers.sample_translation_axis = self.mtn_ctrls[self.tsamp_axis_index - 1]
        self.motion_controllers.detector_rotation_axis = self.mtn_ctrls[self.detector_axis_index - 1]

        # Set limits.
        self.max_pos = self.UIE_mcw_min_pos_in_qdsb.value()
        self.min_pos = self.UIE_mcw_max_pos_in_qdsb.value()
        self.fw_max_pos = self.UIE_mcw_fw_max_qdsb.value()
        self.fw_min_pos = self.UIE_mcw_fw_min_qdsb.value()
        self.smr_max_pos = self.UIE_mcw_smr_max_qdsb.value()
        self.smr_min_pos = self.UIE_mcw_smr_min_qdsb.value()
        self.smt_max_pos = self.UIE_mcw_smt_max_qdsb.value()
        self.smt_min_pos = self.UIE_mcw_smt_min_qdsb.value()
        self.dr_max_pos = self.UIE_mcw_dr_max_qdsb.value()
        self.dr_min_pos = self.UIE_mcw_dr_min_qdsb.value()
        self.motion_controllers.main_drive_axis.set_limits(self.max_pos, self.min_pos)
        self.motion_controllers.filter_wheel_axis.set_limits(self.fw_max_pos, self.fw_min_pos)
        self.motion_controllers.sample_rotation_axis.set_limits(self.smr_max_pos, self.smr_min_pos)
        self.motion_controllers.sample_translation_axis.set_limits(self.smt_max_pos, self.smt_min_pos)
        self.motion_controllers.detector_rotation_axis.set_limits(self.dr_max_pos, self.dr_min_pos)

        # Set conversion factors.
        self.calculate_and_apply_steps_per_nm()

        # self.motion_controllers.main_drive_axis.set_steps_per_value(self.UIE_mcw_steps_per_nm_qdsb.value())
        self.motion_controllers.filter_wheel_axis.set_steps_per_value(self.UIE_mcw_fw_steps_per_rot_qdsb.value())
        self.motion_controllers.sample_rotation_axis.set_steps_per_value(self.UIE_mcw_sm_steps_per_rot_qdsb.value())
        self.motion_controllers.sample_translation_axis.set_steps_per_value(self.UIE_mcw_sm_steps_per_trans_qdsb.value())
        self.motion_controllers.detector_rotation_axis.set_steps_per_value(self.UIE_mcw_dr_steps_per_qdsb.value())

        print('APPLIED GRAT DENSITY:', self.grating_density)
        print('APPLIED STEPS PER NM:', self.motion_controllers.main_drive_axis.get_steps_per_value())

        self.machine_conf_win.close()
    
    def QMessageBoxQuestion(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        print('QMessageBoxInformation:', title, msg)
        retval = QMessageBox.question(self, title, msg,
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        application.setQuitOnLastWindowClosed(True)
        return retval

    def QMessageBoxInformation(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        print('QMessageBoxInformation:', title, msg)
        retval = QMessageBox.information(self, title, msg)
        application.setQuitOnLastWindowClosed(True)
        return retval

    def QMessageBoxWarning(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        print('QMessageBoxWarning:', title, msg)
        retval = QMessageBox.warning(self, title, msg)
        application.setQuitOnLastWindowClosed(True)
        return retval

    def QMessageBoxCritical(self, title: str, msg: str):
        application.setQuitOnLastWindowClosed(False)
        print('QMessageBoxCritical:', title, msg)
        retval = QMessageBox.critical(self, title, msg)
        application.setQuitOnLastWindowClosed(True)
        return retval

# Main function.
if __name__ == '__main__':
    # There will be three separate GUIs:
    # 1. Initialization loading screen, where devices are being searched for and the current status and tasks are displayed. If none are found, display an error and an exit button.
    # 2. The device selection display, where devices can be selected and their settings can be changed prior to entering the control program.
    # 3. The control GUI (mainwindow.ui), where the user has control over what the device(s) do.

    sys._excepthook = sys.excepthook 
    def exception_hook(exctype, value, traceback):
        print('\n\n\nEXCEPTION HOOK')
        print(exctype, value, traceback)
        print('EXCEPTION HOOK\n\n')
        sys._excepthook(exctype, value, traceback) 
        sys.exit(1) 
    sys.excepthook = exception_hook 
    
    application = QApplication(sys.argv)
    # application.setQuitOnLastWindowClosed(False)

    # Finding and setting of fonts.
    try:
        fid = QFontDatabase.addApplicationFont(exeDir + '/fonts/digital-7 (mono italic).ttf')
    except Exception as e:
        print(e.what())

    try:
        fid = QFontDatabase.addApplicationFont(exeDir + '/fonts/digital-7 (mono).ttf')
    except Exception as e:
        print(e.what())

    # Main GUI and child-window setup.
    ui_file_name = exeDir + '/ui/machine_config.ui'
    ui_file = QFile(ui_file_name)
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)

    ui_file_name = exeDir + '/ui/device_manager.ui'
    ui_file = QFile(ui_file_name) # workaround to load UI file with pyinstaller
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)

    ui_file_name = exeDir + '/ui/main_window.ui'
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
        exit_code = application.exec() # block until

        # Save the current configuration when exiting. If the program crashes, it doesn't save your config.
        if mainWindow.main_gui_booted:
            mainWindow.save_config(appDir, False) 

        # Cleanup.
        del mainWindow

    print('Exiting program...')

    os._exit(exit_code)

# %%
