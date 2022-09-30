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

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# %% Custom Imports
from utilities.config import load_config, save_config, reset_config
import webbrowser
from utilities.datatable import DataTableWidget

from middleware import MotionController
from middleware import DataSampler
from middleware import ColorWheel

# %% Fonts
digital_7_italic_22 = None
digital_7_16 = None

# %% Classes
class NavigationToolbar(NavigationToolbar2QT):
    def edit_parameters(self):
        print("before")
        super(NavigationToolbar, self).edit_parameters()
        print("after")

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

    def getToolbar(self, parent) -> NavigationToolbar:
        self.toolbar = NavigationToolbar(self, parent)
        return self.toolbar

    def setTableClearCb(self, fcn):
        self._tableClearCb = fcn

    def clearPlotFcn(self):
        print('clear called')
        if not self.parent.scanRunning:
            self.axes.cla()
            self.axes.set_xlabel('Location (nm)')
            self.axes.set_ylabel('Photo Current (pA)')
            self.axes.grid()
            self.draw()
            if self._tableClearCb is not None:
                self._tableClearCb()
        return

    def updatePlots(self, data):
        print('Update called')
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

    def appendPlot(self, idx, xdata, ydata):
        if idx not in self.lines.keys():
            c = self.colors[idx % len(self.colors)]
            self.lines[idx], = self.axes.plot(xdata, ydata, label = 'Scan #%d'%(idx), color = c)
        else:
            self.lines[idx].set_data(xdata, ydata)
        self.draw()

class Scan(QThread):
    pass

class Ui(QMainWindow):
    # Destructor
    def __del__(self):
        # del self.scan # workaround for cross referencing: delete scan externally
        del self.motor_ctrl
        del self.pa

    # Constructor
    def __init__(self, application, uiresource = None):
        # Handles the initial showing of the UI.
        self.application: QApplication = application
        args = self.application.arguments()
        super(Ui, self).__init__()
        uic.loadUi(uiresource, self)

        self.loading_win = None
        self.showLoadingWindow()

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
        self.calculateConversionSlope()

        print('\n\nConversion constant: %f\n'%(self.conversion_slope))

        self.manual_position = 0 # 0 nm
        self.startpos = 0
        self.stoppos = 0
        self.steppos = 0.1

        # self.application: QApplication = application
        # args = self.application.arguments()

        # super(Ui, self).__init__()
        # uic.loadUi(uiresource, self)

        # # Display the GUI.
        # self.show()

        if len(args) != 1:
            self.setWindowTitle("McPherson Monochromator Control (Debug Mode) v0.3")
        else:
            self.setWindowTitle("McPherson Monochromator Control (Hardware Mode) v0.3")

        self.is_conv_set = False # Use this flag to set conversion

        # Picoammeter initialization.
        self.pa = DataSampler(len(args))

        # Generalized to any compatible machines.
        # Motion controller initialization.
        print("Motion controller init begin.")
        self.motor_ctrl = MotionController(len(args))

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

        if self.pa.is_dummy():
            self.stop_spin.setValue(0.2)

        self.step_spin = self.findChild(QDoubleSpinBox, "step_set_spinbox")
        self.currpos_nm_disp = self.findChild(QLabel, "currpos_nm")
        self.scan_status = self.findChild(QLabel, "status_label")
        self.scan_progress = self.findChild(QProgressBar, "progressbar")
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
        if not self.motor_ctrl.is_dummy():
            self.homing_started = True
            self.disable_movement_sensitive_buttons(True)
            self.scan_statusUpdate_slot("HOMING")
            self.motor_ctrl.home()

        # Get and set the palette.
        palette = self.currpos_nm_disp.palette()
        palette.setColor(palette.WindowText, QColor(255, 0, 0))
        palette.setColor(palette.Background, QColor(0, 170, 255))
        palette.setColor(palette.Light, QColor(80, 80, 255))
        palette.setColor(palette.Dark, QColor(0, 255, 0))
        self.currpos_nm_disp.setPalette(palette)

        self.plotCanvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.plotCanvas.clearPlotFcn()
        self.plotCanvas.setTableClearCb(self.table.plotsClearedCb)
        toolbar = self.plotCanvas.getToolbar(self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self.plotCanvas)
        self.plotFrame.setLayout(layout)

        self.plot_clear_plots.clicked.connect(self.plotCanvas.clearPlotFcn)

        # Set the initial value of the Manual Control 'Position:' spin box.
        self.pos_spin.setValue(0)

        # Signal-to-slot connections.
        save_config_btn.clicked.connect(self.showConfigWindow)
        self.scan_button.clicked.connect(self.scan_button_pressed)
        self.stop_scan_button.clicked.connect(self.stop_scan_button_pressed)
        # self.collect_data.clicked.connect(self.manual_collect_button_pressed)
        self.move_to_position_button.clicked.connect(self.move_to_position_button_pressed)
        self.start_spin.valueChanged.connect(self.start_changed)
        self.stop_spin.valueChanged.connect(self.stop_changed)
        self.step_spin.valueChanged.connect(self.step_changed)
        self.pos_spin.valueChanged.connect(self.manual_pos_changed)

        self.machine_conf_act.triggered.connect(self.showConfigWindow)
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
        self.updateStatusBarGratingEquationValues()

        self.manual_position = (self.pos_spin.value() + self.zero_ofst) * self.conversion_slope
        self.startpos = (self.start_spin.value() + self.zero_ofst) * self.conversion_slope
        self.stoppos = (self.stop_spin.value() + self.zero_ofst) * self.conversion_slope

        # Make sure the menu bar QAction states agree with reality.
        # print('mes_sign: ', self.mes_sign)
        # print('autosave_data: ', self.autosave_data_bool)

        if self.mes_sign == -1:
            self.invert_mes_act.setChecked(True)
        else:
            self.invert_mes_act.setChecked(False)

        if self.autosave_data_bool:
            self.autosave_data_act.setChecked(True)
        else:
            self.autosave_data_act.setChecked(False)

        self.updateMovementLimits()

        self.table.updatePlots()

        # TODO: Only close if we successfully detected devices. Otherwise, open a device management prompt.
        self.loading_win.close()
        self.show()

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
        self.scan_statusUpdate_slot("HOMING")
        self.homing_started = True
        self.disable_movement_sensitive_buttons(True)
        self.motor_ctrl.home()

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


    def updateStatusBarGratingEquationValues(self):
        self.sb_grating_density.setText("  <i>G</i> " + str(self.grating_density) + " grooves/mm    ")
        self.sb_zero_offset.setText("  <i>&lambda;</i><sub>0</sub> " + str(self.zero_ofst) + " nm    ")
        self.sb_inc_ang.setText("  <i>&theta;</i><sub>inc</sub> " + str(self.incidence_ang) + " deg    ")
        self.sb_tan_ang.setText("  <i>&theta;</i><sub>tan</sub> " + str(self.tangent_ang) + " deg    ")
        self.sb_arm_len.setText("  <i>L</i> " + str(self.arm_length) + " mm    ")
        self.sb_diff_order.setText("  <i>m</i> " + str(self.diff_order) + "    ")
        self.sb_conv_slope.setText("   %.06f slope    "%(self.conversion_slope))

    def updatePlots(self, data: list):
        if self.plotCanvas is None:
            return
        self.plotCanvas.updatePlots(data)

    def scan_statusUpdate_slot(self, status):
        self.scan_status.setText('<html><head/><body><p><span style=" font-weight:600;">%s</span></p></body></html>'%(status))

    def scan_progress_slot(self, curr_percent):
        self.scan_progress.setValue(curr_percent)

    def scan_complete_slot(self):
        self.scanRunning = False
        self.disable_movement_sensitive_buttons(False)
        self.scan_button.setText('Begin Scan')
        self.scan_status.setText('<html><head/><body><p><span style=" font-weight:600;">IDLE</span></p></body></html>')
        self.scan_progress.reset()

    def scan_data_begin_slot(self, scan_idx: int, metadata: dict):
        n_scan_idx = self.table.insertData(None, None, metadata)
        if n_scan_idx != scan_idx:
            print('\n\n CHECK INSERTION ID MISMATCH %d != %d\n\n'%(scan_idx, n_scan_idx))

    def scan_data_update_slot(self, scan_idx: int, xdata: float, ydata: float):
        self.table.insertDataAt(scan_idx, xdata, ydata)

    def scan_data_complete_slot(self, scan_idx: int):
        self.table.markInsertFinished(scan_idx)
        self.table.updateTableDisplay()

    def update_position_displays(self):
        self.current_position = self.motor_ctrl.get_position()
        
        if self.homing_started: # set this to True at __init__ because we are homing, and disable everything. same goes for 'Home' button
            home_status = self.motor_ctrl.is_homing() # explore possibility of replacing this with is_homed()
            # print("home_status", home_status)

            if home_status:
                # Detect if the device is saying its homing, but its not actually moving.
                if self.current_position == self.previous_position:
                    self.immobile_count += 1
                if self.immobile_count >= 3:
                    self.motor_ctrl.home()
                    self.immobile_count = 0

            if not home_status:
                # enable stuff here
                print(home_status)
                self.immobile_count = 0
                self.scan_statusUpdate_slot("IDLE")
                self.disable_movement_sensitive_buttons(False)
                self.homing_started = False
                pass
        move_status = self.motor_ctrl.is_moving()
        
        if not move_status and self.moving and not self.scanRunning:
            print("setDisabled 1")
            self.disable_movement_sensitive_buttons(False)

        self.moving = move_status
        self.previous_position = self.current_position

        self.currpos_nm_disp.setText('<b><i>%3.4f</i></b>'%(((self.current_position / self.motor_ctrl.mm_to_idx) / self.conversion_slope) - self.zero_ofst))

    def scan_button_pressed(self):
        # self.moving = True
        print("Scan button pressed!")
        if not self.scanRunning:
            self.scanRunning = True
            self.disable_movement_sensitive_buttons(True)
            self.scan.start()
            print("setDisabled 2")

    def stop_scan_button_pressed(self):
        print("Stop scan button pressed!")
        if self.scanRunning:
            self.scanRunning = False

    def move_to_position_button_pressed(self):
        self.moving = True

        self.disable_movement_sensitive_buttons(True)

        print("Conversion slope: " + str(self.conversion_slope))
        print("Manual position: " + str(self.manual_position))
        print("Move to position button pressed, moving to %d nm"%(self.manual_position))
        pos = int((self.pos_spin.value() + self.zero_ofst) * self.conversion_slope * self.motor_ctrl.mm_to_idx)
        self.motor_ctrl.move_to(pos, False)

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

    def showGratingWindow(self):
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
            apply_button.clicked.connect(self.applyGratingInput)

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

    def applyGratingInput(self):
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

    def newGratingItem(self, idx: int):
        slen = len(self.grating_combo_lstr) # old length
        if idx == slen - 1:
            self.showGratingWindow()
            if len(self.grating_combo_lstr) != slen: # new length is different, new entry has been added
                self.current_grating_idx = self.grating_combo.setCurrentIndex(idx)
            else: # new entry has not been added
                self.grating_combo.setCurrentIndex(self.current_grating_idx)

    # Screen shown during startup to disable premature user interaction as well as handle device-not-found issues.
    def showLoadingWindow(self):
        if self.loading_win is None:
            self.loading_win = QDialog(self)
            self.loading_win.setWindowTitle('Device Manager')
            self.loading_win.setMinimumSize(520, 360)

            self.prompt_label = QLabel('Detecting devices, please be patient...')
            self.prompt_label.setFont(QFont('Segoe UI', 12))

            layout = QVBoxLayout()
            hlayout = QHBoxLayout()
            hlayout.addWidget(self.prompt_label)
            layout.addLayout(hlayout)
            self.loading_win.setLayout(layout)

            self.loading_win.show()

    def showConfigWindow(self):
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
            self.grating_combo.activated.connect(self.newGratingItem)
            
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
            self.machine_conf_btn.clicked.connect(self.applyMachineConf)
        
        self.machine_conf_win.exec() # synchronously run this window so parent window is disabled
        print('Exec done', self.current_grating_idx, self.grating_combo.currentIndex())
        if self.current_grating_idx != self.grating_combo.currentIndex():
            self.grating_combo.setCurrentIndex(self.current_grating_idx)

    def updateMovementLimits(self):
        self.pos_spin.setMaximum(self.max_pos)
        self.pos_spin.setMinimum(self.min_pos)

        self.start_spin.setMaximum(self.max_pos)
        self.start_spin.setMinimum(self.min_pos)

        self.stop_spin.setMaximum(self.max_pos)
        self.stop_spin.setMinimum(self.min_pos)

    def applyMachineConf(self):
        print('Apply config called')
        idx = self.grating_combo.currentIndex()
        if idx < len(self.grating_combo_lstr) - 1:
            self.current_grating_idx = idx
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx])
        print(self.grating_density)
        self.diff_order = int(self.diff_order_in.value())
        self.max_pos = self.max_pos_in.value()
        self.min_pos = self.min_pos_in.value()

        self.updateMovementLimits()

        self.zero_ofst = self.zero_ofst_in.value()
        self.incidence_ang = self.incidence_ang_in.value()
        self.tangent_ang = self.tangent_ang_in.value()
        self.arm_length = self.arm_length_in.value()

        self.calculateConversionSlope()

        self.updateStatusBarGratingEquationValues()

        self.machine_conf_win.close()
    
    def calculateConversionSlope(self):
        self.conversion_slope = ((self.arm_length * self.diff_order * self.grating_density)/(2 * (m.cos(m.radians(self.tangent_ang))) * (m.cos(m.radians(self.incidence_ang))) * 1e6))

# QThread which will be run by the loading UI to initialize communication with devices. Will need to save important data. This functionality currently handled by the MainWindow UI.
class Boot(QThread):
    pass

class Scan(QThread):
    statusUpdate = pyqtSignal(str)
    progress = pyqtSignal(int)
    complete = pyqtSignal()

    dataBegin = pyqtSignal(int, dict) # scan index, redundant
    dataUpdate = pyqtSignal(int, float, float) # scan index, xdata, ydata (to be appended into index)
    dataComplete = pyqtSignal(int) # scan index, redundant

    def __init__(self, parent: QMainWindow):
        super(Scan, self).__init__()
        self.other: Ui = parent
        self.statusUpdate.connect(self.other.scan_statusUpdate_slot)
        self.progress.connect(self.other.scan_progress_slot)
        self.complete.connect(self.other.scan_complete_slot)
        self.dataBegin.connect(self.other.scan_data_begin_slot)
        self.dataUpdate.connect(self.other.scan_data_update_slot)
        self.dataComplete.connect(self.other.scan_data_complete_slot)
        print('mainWindow reference in scan init: %d'%(sys.getrefcount(self.other) - 1))
        self._last_scan = -1

    def __del__(self):
        self.wait()

    def run(self):
        self.other.disable_movement_sensitive_buttons(True)

        print(self.other)
        print("Save to file? " + str(self.other.autosave_data_bool))

        self.statusUpdate.emit("PREPARING")
        sav_file = None
        tnow = dt.datetime.now()
        if (self.other.autosave_data_bool):
            
            filename = self.other.data_save_directory + tnow.strftime('%Y%m%d%H%M%S') + "_data.csv"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            sav_file = open(filename, 'w')

        print("SCAN QTHREAD")
        print("Start | Stop | Step")
        print(self.other.startpos, self.other.stoppos, self.other.steppos)
        self.other.startpos = (self.other.start_spin.value() + self.other.zero_ofst) * self.other.conversion_slope
        self.other.stoppos = (self.other.stop_spin.value() + self.other.zero_ofst) * self.other.conversion_slope
        self.other.steppos = (self.other.step_spin.value()) * self.other.conversion_slope
        if self.other.steppos == 0 or self.other.startpos == self.other.stoppos:
            if (sav_file is not None):
                sav_file.close()
            self.complete.emit()
            return
        scanrange = np.arange(self.other.startpos, self.other.stoppos + self.other.steppos, self.other.steppos)
        # self.other.pa.set_samples(3)
        nidx = len(scanrange)
        # if nidx > 0

        # MOVES TO ZERO PRIOR TO BEGINNING A SCAN
        self.statusUpdate.emit("ZEROING")
        prep_pos = int((0 + self.other.zero_ofst) * self.other.conversion_slope * self.other.motor_ctrl.mm_to_idx)
        self.other.motor_ctrl.move_to(prep_pos, True)
        self.statusUpdate.emit("HOLDING")
        sleep(1)

        self._xdata = []
        self._ydata = []
        self._scan_id = self.other.table.scanId
        metadata = {'tstamp': tnow, 'mm_to_idx': self.other.motor_ctrl.mm_to_idx, 'mm_per_nm': self.other.conversion_slope, 'lam_0': self.other.zero_ofst, 'scan_id': self.scanId}
        self.dataBegin.emit(self.scanId, metadata) # emit scan ID so that the empty data can be appended and table scan ID can be incremented
        while self.scanId == self.other.table.scanId: # spin until that happens
            continue
        for idx, dpos in enumerate(scanrange):
            if not self.other.scanRunning:
                break
            self.statusUpdate.emit("MOVING")
            self.other.motor_ctrl.move_to(dpos * self.other.motor_ctrl.mm_to_idx, True)
            pos = self.other.motor_ctrl.get_position()
            self.statusUpdate.emit("SAMPLING")
            buf = self.other.pa.sample_data()
            print(buf)
            self.progress.emit(round((idx + 1) * 100 / nidx))
            # process buf
            words = buf.split(',') # split at comma
            if len(words) != 3:
                continue
            try:
                mes = float(words[0][:-1]) # skip the A (unit suffix)
                err = int(float(words[2])) # skip timestamp
            except Exception:
                continue
            self._xdata.append((((pos / self.other.motor_ctrl.mm_to_idx) / self.other.conversion_slope)) - self.other.zero_ofst)
            self._ydata.append(self.other.mes_sign * mes * 1e12)
            self.dataUpdate.emit(self.scanId, self._xdata[-1], self._ydata[-1])

            if sav_file is not None:
                if idx == 0:
                    sav_file.write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
                    sav_file.write('# Steps/mm: %f\n'%(self.other.motor_ctrl.mm_to_idx))
                    sav_file.write('# mm/nm: %e; lambda_0 (nm): %e\n'%(self.other.conversion_slope, self.other.zero_ofst))
                    sav_file.write('# Position (step),Position (nm),Mean Current(A),Status/Error Code\n')
                # process buf
                # 1. split by \n
                buf = '%d,%e,%e,%d\n'%(pos, ((pos / self.other.motor_ctrl.mm_to_idx) / self.other.conversion_slope) - self.other.zero_ofst, self.other.mes_sign * mes, err)
                sav_file.write(buf)

        if (sav_file is not None):
            sav_file.close()
        self.other.num_scans += 1

        self.complete.emit()
        self.dataComplete.emit(self.scanId)
        print('mainWindow reference in scan end: %d'%(sys.getrefcount(self.other) - 1))
    
    @property
    def xdata(self):
        return np.array(self._xdata, dtype=float)
    
    @property
    def ydata(self):
        return np.array(self._ydata, dtype=float)

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

    ui_file_name = exeDir + '/ui/mainwindow_mk2.ui'
    ui_file = QFile(ui_file_name) # workaround to load UI file with pyinstaller
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)

    # Initializes the GUI / Main GUI bootup.
    mainWindow = Ui(application, ui_file)
    
    # Wait for the Qt loop to exit before exiting.
    ret = application.exec_() # block until

    # Save the current configuration when exiting. If the program crashes, it doesn't save your config.
    save_config(appDir, mainWindow.mes_sign, mainWindow.autosave_data_bool, mainWindow.data_save_directory, mainWindow.grating_combo_lstr, mainWindow.current_grating_idx, mainWindow.diff_order, mainWindow.zero_ofst, mainWindow.incidence_ang, mainWindow.tangent_ang, mainWindow.arm_length, mainWindow.max_pos, mainWindow.min_pos)    

    # Cleanup and exit.
    del mainWindow
    sys.exit(ret)
# %%
