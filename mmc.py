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

# %% Set up paths
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

# %% More Imports
import configparser as confp
from email.charset import QP
from time import sleep
import weakref
from PyQt5 import uic
from PyQt5.Qt import QTextOption
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ARG, QAbstractItemModel,
                          QFileInfo, qFuzzyCompare, QMetaObject, QModelIndex, QObject, Qt,
                          QThread, QTime, QUrl, QSize, QEvent, QCoreApplication, QFile, QIODevice)
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
from io import TextIOWrapper

# import _thorlabs_kst_advanced as tlkt
from drivers import _thorlabs_kst_advanced as tlkt
import picoammeter as pico
import math as m
import os
import numpy as np
import datetime as dt

import matplotlib
matplotlib.use('Qt5Agg')

from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from utilities.config import load_config, save_config

# %% Fonts
digital_7_italic_22 = None
digital_7_16 = None

# %% Classes

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout = True)
        self.axes = fig.add_subplot(111)
        self.axes.set_xlabel('Position (nm)')
        self.axes.set_ylabel('Current (pA)')
        super(MplCanvas, self).__init__(fig)

# Imports .ui file.
class Scan(QThread):
    pass

# TODO: Figure out a loading screen.
# class LoadUi(QWidget):
#     def __init__(self, application, uiresource = None):
#         self.application: QApplication = application
#         args = self.application.arguments()

#         super(LoadUi, self).__init__()
#         uic.loadUi(uiresource, self)

#         self.show()

class Ui(QMainWindow):
    # manual_prefix = 'manual'
    # auto_prefix = 'automatic'
    # manual_dir = './data'
    # auto_dir = './data'
    # Destructor
    def __del__(self):
        # del self.scan # workaround for cross referencing: delete scan externally
        del self.motor_ctrl
        del self.pa

    # Constructor
    def __init__(self, application, uiresource = None):
        # Set this via the QMenu QAction Edit->Change Auto-log Directory
        self.data_save_directory = os.path.expanduser('~/Documents')
        self.data_save_directory += '/mcpherson_mmc/%s/'%(dt.datetime.now().strftime('%Y%m%d'))
        if not os.path.exists(self.data_save_directory):
            os.makedirs(self.data_save_directory)

        self.num_scans = 0

        self.mes_sign = 1
        self.autosave_data_bool = False
        self.pop_out_table = False
        self.pop_out_plot = False

        self.machine_conf_win: QDialog = None
        self.grating_conf_win: QDialog = None
        self.grating_density_in: QDoubleSpinBox = None
        self.diff_order_in: QDoubleSpinBox = None
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
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx]) # grooves/mm
        self.tangent_ang = 0 # deg
        self.incidence_ang = 32 # deg
        self.zero_ofst = 37.8461 # nm

        # Replaces default grating equation values with the values found in the config.ini file.
        load_dict = load_config(appDir)
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
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx])

        # Sets the conversion slope based on the found (or default) values.
        self.calculateConversionSlope()

        print('\n\nConversion constant: %f\n'%(self.conversion_slope))

        self.manual_position = 0 # 0 nm
        self.startpos = 0
        self.stoppos = 0
        self.steppos = 0.1

        self.application: QApplication = application
        args = self.application.arguments()

        super(Ui, self).__init__()
        uic.loadUi(uiresource, self)

        if len(args) != 1:
            self.setWindowTitle("McPherson Monochromator Control (Debug Mode)")
        else:
            self.setWindowTitle("McPherson Monochromator Control (Hardware Mode)")

        self.is_conv_set = False # Use this flag to set conversion

        # Picoammeter initialization.
        if len(args) != 1:
            self.pa = pico.Picodummy(3)
        else:
            self.pa = pico.Picoammeter(3)

        # KST101 initialization.
        print("KST101 init begin.")
        if len(args) == 1:
            print("Trying...")
            serials = tlkt.Thorlabs.ListDevicesAny()
            print(serials)
            if len(serials) == 0:
                print("No KST101 controller found.")
                raise RuntimeError('No KST101 controller found')
            self.motor_ctrl = tlkt.Thorlabs.KST101(serials[0])
            if (self.motor_ctrl._CheckConnection() == False):
                print("Connection with motor controller failed.")
                raise RuntimeError('Connection with motor controller failed.')
            self.motor_ctrl.set_stage('ZST25')
        else:
            serials = tlkt.Thorlabs.KSTDummy._ListDevices()
            self.motor_ctrl = tlkt.Thorlabs.KSTDummy(serials[0])
            self.motor_ctrl.set_stage('ZST25')

        # TODO: Move to zero-order?
        # Move to 1mm (0nm)
        # self.motor_ctrl.move_to(1 * self.motor_ctrl.mm_to_idx, True)

        # GUI initialization, gets the UI elements from the .ui file.
        self.scan_button = self.findChild(QPushButton, "begin_scan_button") # Scanning Control 'Begin Scan' Button
        self.stop_scan_button = self.findChild(QPushButton, "stop_scan_button")
        self.save_data_checkbox = self.findChild(QCheckBox, "save_data_checkbox") # Scanning Control 'Save Data' Checkbox
        # self.auto_prefix_box = self.findChild(QLineEdit, "scancon_prefix_lineedit") # Scanning Control 'Data file prefix:' Line Edit
        # self.manual_prefix_box = self.findChild(QLineEdit, "mancon_prefix_lineedit")
        self.dir_box = self.findChild(QLineEdit, "save_dir_lineedit")
        self.start_spin = self.findChild(QDoubleSpinBox, "start_set_spinbox")
        self.stop_spin = self.findChild(QDoubleSpinBox, "end_set_spinbox")
        self.step_spin = self.findChild(QDoubleSpinBox, "step_set_spinbox")
        self.currpos_nm_disp = self.findChild(QLabel, "currpos_nm")
        self.scan_status = self.findChild(QLabel, "status_label")
        self.scan_progress = self.findChild(QProgressBar, "progressbar")
        save_config_btn: QPushButton = self.findChild(QPushButton, 'save_config_button')
        self.pos_spin: QDoubleSpinBox = self.findChild(QDoubleSpinBox, "pos_set_spinbox") # Manual Control 'Position:' Spin Box
        self.move_to_position_button: QPushButton = self.findChild(QPushButton, "move_pos_button")
        self.collect_data: QPushButton = self.findChild(QPushButton, "collect_data_button")
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
        self.oneshot_samples_spinbox: QSpinBox = self.findChild(QSpinBox, "samples_set_spinbox")
        self.table: QTableWidget = self.findChild(QTableWidget, "table")
        
        # Get the palette.
        palette = self.currpos_nm_disp.palette()

        # Foreground color.
        palette.setColor(palette.WindowText, QColor(255, 0, 0))
        # Background color.
        palette.setColor(palette.Background, QColor(0, 170, 255))
        # "light" border.
        palette.setColor(palette.Light, QColor(80, 80, 255))
        # "dark" border.
        palette.setColor(palette.Dark, QColor(0, 255, 0))

        # Set the palette.
        self.currpos_nm_disp.setPalette(palette)

        # Plot setup.
        self.xdata: dict = {} # collection of xdata
        self.ydata: dict = {} # collection of ydata

        self.manual_xdata: list = []
        self.manual_ydata: list = []

        self.plotCanvas = MplCanvas(self, width=5, height=4, dpi=100)
        # self.plotCanvas.axes.plot([], [])
        self.scanRunning = False
        self.clearPlotFcn()
        toolbar = NavigationToolbar(self.plotCanvas, self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(toolbar)
        layout.addWidget(self.plotCanvas)
        self.plotFrame.setLayout(layout)

        self.plot_clear_plots.clicked.connect(self.clearPlotFcn)

        # Setting states of UI elements.
        # self.manual_prefix_box.setText(self.manual_prefix)
        # self.auto_prefix_box.setText(self.auto_prefix)
        # self.dir_box.setText(self.save_dir)

        # Set the initial value of the Manual Control 'Position:' spin box.
        self.pos_spin.setValue(0)

        # Signal-to-slot connections.
        save_config_btn.clicked.connect(self.showConfigWindow)
        self.scan_button.clicked.connect(self.scan_button_pressed)
        self.stop_scan_button.clicked.connect(self.stop_scan_button_pressed)
        self.collect_data.clicked.connect(self.manual_collect_button_pressed)
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

        # Other stuff.
        self.scan = Scan(weakref.proxy(self))
        self.one_shot = OneShot(weakref.proxy(self))

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

        # Set up the data table.
        self.auto_data_dict = {} # {Scan ID, CSV Data String} dictionary for automatic scan data.
        self.man_data_str = '' # CSV String to append manual data to.
        self.table.setColumnCount(6)
        self.scan_number = 0
        self.table_has_manual_entry = False
        self.table_manual_row = 0
        self.table_manual_points = 0
        # Scan Number, Scan Type (Auto, Manual), Number of Data Points (e.g., pressed scan 50x), Starting wavelength, Stop wavelength (auto-only), step wavelength (auto-only)
        self.table.setHorizontalHeaderLabels(['#', 'Scan Type', 'Data Points', 'Start', 'Stop', 'Step'])

        # Make sure the menu bar QAction states agree with reality.
        print('mes_sign: ', self.mes_sign)
        print('autosave_data: ', self.autosave_data_bool)

        if self.mes_sign == -1:
            self.invert_mes_act.setChecked(True)
        else:
            self.invert_mes_act.setChecked(False)

        if self.autosave_data_bool:
            self.autosave_data_act.setChecked(True)
        else:
            self.autosave_data_act.setChecked(False)

        # Display the GUI.
        self.show()

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

    def clearPlotFcn(self):
        print('clear called')
        if not self.scanRunning:
            self.plotCanvas.axes.cla()
            self.plotCanvas.axes.set_xlabel('Location (nm)')
            self.plotCanvas.axes.set_ylabel('Photo Current (pA)')
            self.plotCanvas.axes.grid()
            self.plotCanvas.draw()
            self.xdata = {}
            self.ydata = {}
        return

    def updatePlot(self):
        print('Update called')
        self.plotCanvas.axes.cla()
        self.plotCanvas.axes.set_xlabel('Location (nm)')
        self.plotCanvas.axes.set_ylabel('Photo Current (pA)')
        keys = list(self.xdata.keys())
        keys.sort()
        for idx in keys:
            if len(self.xdata[idx]) == len(self.ydata[idx]):
                self.plotCanvas.axes.plot(self.xdata[idx], self.ydata[idx], label = 'Scan %d'%(idx + 1))
        self.plotCanvas.axes.legend()
        self.plotCanvas.axes.grid()
        self.plotCanvas.draw()
        return

    def scan_statusUpdate_slot(self, status):
        self.scan_status.setText('<html><head/><body><p><span style=" font-weight:600;">%s</span></p></body></html>'%(status))

    def scan_progress_slot(self, curr_percent):
        self.scan_progress.setValue(curr_percent)

    def scan_complete_slot(self):
        self.scan_button.setText('Begin Scan')
        self.scan_status.setText('<html><head/><body><p><span style=" font-weight:600;">IDLE</span></p></body></html>')
        self.scan_progress.reset()

    def update_position_displays(self):
        self.current_position = self.motor_ctrl.get_position()
        self.moving = self.motor_ctrl.is_moving()
        # print(self.current_position)
        self.currpos_nm_disp.setText('<b><i>%3.4f</i></b>'%(((self.current_position / self.motor_ctrl.mm_to_idx) / self.conversion_slope) - self.zero_ofst))

    def scan_button_pressed(self):
        print("Scan button pressed!")
        if not self.scanRunning:
            self.scan.start()
            self.scan_button.setDisabled(True)
            self.stop_scan_button.setDisabled(False)

    def stop_scan_button_pressed(self):
        print("Stop scan button pressed!")
        if self.scanRunning:
            self.scanRunning = False

    def manual_collect_button_pressed(self):
        print("Manual collect button pressed!")
        self.collect_data.setDisabled(True)
        self.one_shot.start()

    def move_to_position_button_pressed(self):
        self.moving = True
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

    def take_data(self):
        # TODO: Garbo function, edit for proper functionality
        # TODO: otherwise, good. <pat in the back>

        pass



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

            self.machine_conf_btn = self.machine_conf_win.findChild(QPushButton, 'update_conf_btn')
            self.machine_conf_btn.clicked.connect(self.applyMachineConf)
        
        self.machine_conf_win.exec() # synchronously run this window so parent window is disabled
        print('Exec done', self.current_grating_idx, self.grating_combo.currentIndex())
        if self.current_grating_idx != self.grating_combo.currentIndex():
            self.grating_combo.setCurrentIndex(self.current_grating_idx)

    def applyMachineConf(self):
        print('Apply config called')
        idx = self.grating_combo.currentIndex()
        if idx < len(self.grating_combo_lstr) - 1:
            self.current_grating_idx = idx
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx])
        print(self.grating_density)
        self.diff_order = int(self.diff_order_in.value())
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
# TODO: Complete.
class Boot(QThread):
    pass

class OneShot(QThread):
    statusUpdate = pyqtSignal(str)
    complete = pyqtSignal()

    def __init__(self, parent: QMainWindow):
        super(OneShot, self).__init__()
        self.parent: Ui = parent
        # TODO: disable begin scan button on run
        self.statusUpdate.connect(self.parent.scan_statusUpdate_slot)

    def run(self):
        self.parent.scan_button.setDisabled(True)
        # collect data
        for _ in range(self.parent.oneshot_samples_spinbox.value()):
            pos = ((self.parent.motor_ctrl.get_position() / self.parent.motor_ctrl.mm_to_idx) / self.parent.conversion_slope) - self.parent.zero_ofst
            buf = self.parent.pa.sample_data()
            words = buf.split(',') # split at comma
            if len(words) != 3:
                continue
            try:
                mes = float(words[0][:-1]) # skip the A (unit suffix)
                err = int(float(words[2])) # skip timestamp
            except Exception:
                continue
            self.parent.manual_xdata.append(pos)
            self.parent.manual_ydata.append(self.parent.mes_sign * mes * 1e12)
            print(pos, self.parent.mes_sign * mes * 1e12)

            # Add to data table.
            self.parent.table_log(buf, 'Manual', pos)

        self.complete.emit()
        self.parent.collect_data.setDisabled(False)
        self.parent.scan_button.setDisabled(False)

class Scan(QThread):
    statusUpdate = pyqtSignal(str)
    progress = pyqtSignal(int)
    complete = pyqtSignal()

    def __init__(self, parent: QMainWindow):
        super(Scan, self).__init__()
        self.other: Ui = parent
        self.statusUpdate.connect(self.other.scan_statusUpdate_slot)
        self.progress.connect(self.other.scan_progress_slot)
        self.complete.connect(self.other.scan_complete_slot)
        print('mainWindow reference in scan init: %d'%(sys.getrefcount(self.other) - 1))

    def __del__(self):
        self.wait()

    def run(self):
        print(self.other)
        print("Save to file? " + str(self.other.autosave_data_bool))

        self.statusUpdate.emit("PREPARING")
        sav_file = None
        if (self.other.autosave_data_bool):
            tnow = dt.datetime.now()
            
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
            self.complete.emit()
            return
        scanrange = np.arange(self.other.startpos, self.other.stoppos + self.other.steppos, self.other.steppos)
        # self.other.pa.set_samples(3)
        nidx = len(scanrange)
        if len(self.other.xdata) != len(self.other.ydata):
            self.other.xdata = {}
            self.other.ydata = {}
        pidx = self.other.num_scans
        self.other.xdata[pidx] = []
        self.other.ydata[pidx] = []
        self.other.scanRunning = True
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
            # print(words)
            if len(words) != 3:
                continue
            try:
                mes = float(words[0][:-1]) # skip the A (unit suffix)
                err = int(float(words[2])) # skip timestamp
            except Exception:
                continue
            # print(mes, err)
            self.other.xdata[pidx].append((((pos / self.other.motor_ctrl.mm_to_idx) / self.other.conversion_slope)) - self.other.zero_ofst)
            self.other.ydata[pidx].append(self.other.mes_sign * mes * 1e12)
            # print(self.other.xdata[pidx], self.other.ydata[pidx])
            self.other.updatePlot()
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
        self.other.scanRunning = False
        self.other.scan_button.setDisabled(False)
        self.other.stop_scan_button.setDisabled(True)
        self.other.table_log('Automatic', self.other.startpos, self.other.stoppos, self.other.steppos, nidx+1)
        self.complete.emit()
        print('mainWindow reference in scan end: %d'%(sys.getrefcount(self.other) - 1))

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

    # First, the loading screen.
    # TODO: Set up some kind of loading screen to display.
    # lui_file_name = exeDir + '/ui/' + "load.ui"
    # lui_file = QFile(lui_file_name) # workaround to load UI file with pyinstaller
    # if not lui_file.open(QIODevice.ReadOnly):
    #     print(f"Cannot open {lui_file_name}: {lui_file.errorString()}")
    #     sys.exit(-1)

    # loadWindow = LoadUi(application, lui_file)
    # ret = application.exec_()

    # Then, we load up the device selection UI.
    # TODO: Display a device selection UI / connected devices status UI prior to booting the main window.

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
    # TODO: Save the following:
    # mainWindow.mes_sign
    # .autosave_data
    # .data_save_directory
    save_config(appDir, mainWindow.mes_sign, mainWindow.autosave_data_bool, mainWindow.data_save_directory, mainWindow.grating_combo_lstr, mainWindow.current_grating_idx, mainWindow.diff_order, mainWindow.zero_ofst, mainWindow.incidence_ang, mainWindow.tangent_ang, mainWindow.arm_length)    

    # Cleanup and exit.
    del mainWindow
    sys.exit(ret)
# %%
