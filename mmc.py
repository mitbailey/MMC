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
                             QTableWidget, QTableWidgetItem, QSplitter, QAbstractItemView, QStyledItemDelegate, QHeaderView, QFrame, QProgressBar, QCheckBox, QToolTip, QGridLayout,
                             QLCDNumber, QAbstractSpinBox)
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

# TODO: Change this to a per-device variable.
MM_TO_IDX = 2184560.64
# NM_TO_MM = 0

# def dcos(deg):
#     return m.degrees((m.cos(m.radians(deg))))

# def nm_to_idx(pos_nm):
#     order = 1
#     zero_order_offset = 1
#     L = 550
#     grating_density = 0.0012
#     dX = pos_nm
#     a = ((2) * (1 / grating_density) * dcos(32) * ((dX + zero_order_offset)/(L)) * (10e6)) / (order)
#     return a * MM_TO_IDX

# Imports .ui file.
class Scan(QThread):
    pass

class Ui(QMainWindow):
    manual_prefix = 'manual'
    auto_prefix = 'automatic'
    manual_dir = './data'
    auto_dir = './data'
    startpos = 0
    stoppos = 0
    steppos = 0
    save_data = False

    manual_position = 0

    current_position = -1

    def __del__(self):
        # del self.scan # workaround for cross referencing: delete scan externally
        del self.motor_ctrl
        del self.pa

    def __init__(self, application, uiresource = None):

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

        self.arm_length = 56.53654 # mm
        self.diff_order = 1
        self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx]) # grooves/mm
        self.tangent_ang = 0 # deg
        self.incidence_ang = 32 # deg
        self.zero_ofst = 37.8461 # nm

        while os.path.exists(exeDir + '/config.ini'):
            config = confp.ConfigParser()
            config.read(exeDir + '/config.ini')
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
                self.grating_combo_lstr = gratingDensityList + ['* New Entry']
                try:
                    idx = int(config['INSTRUMENT']['gratingDensityIndex'])
                except Exception as e:
                    print('Error getting grating index, %s'%(e.what()))
                    idx = 0
                if idx >= len(self.grating_combo_lstr) - 1:
                    print('Invalid initial grating index')
                    idx = 0
                self.current_grating_idx = idx
                self.grating_density = float(self.grating_combo_lstr[self.current_grating_idx])
                try:
                    self.diff_order = int(config['INSTRUMENT']['diffractionOrder'])
                except Exception as e:
                    print('Invalid diffraction order, %s'%(e.what()))
                if self.diff_order < 1:
                    print('Diffraction order can not be zero or negative')
                    self.diff_order = 1
                try:
                    self.incidence_ang = float(config['INSTRUMENT']['incidenceAngle'])
                except Exception as e:
                    print('Invalid incidence angle, %s'%(e.what()))
                if not -90 < self.incidence_ang < 90:
                    print('Invalid incidence angle %f'%(self.incidence_ang))
                    self.incidence_ang = 0
                
                try:
                    self.tangent_ang = float(config['INSTRUMENT']['tangentAngle'])
                except Exception as e:
                    print('Invalid tangent angle, %s'%(e.what()))
                if not -90 < self.tangent_ang < 90:
                    print('Invalid tangent angle %f'%(self.tangent_ang))
                    self.tangent_ang = 0

                try:
                    self.arm_length = float(config['INSTRUMENT']['armLength'])
                except Exception as e:
                    print('Invalid arm length, %s'%(e.what()))
                if not 0 < self.arm_length < 1e6: # 1 km
                    print('Invalid arm length %f'%(self.arm_length))
                    self.arm_length = 100

                break
                    
        

        self.calculateConversionSlope()

        # pos_mm = ((arm_length_mm * order * grating_density_grv_mm)/(2 * (m.cos(m.radians(tan_ang_deg))) * (m.cos(m.radians(inc_ang_deg))) * 1e6)) * (INPUT_POSITION_NM - zero_offset_nm)

        print('\n\nConversion constant: %f\n'%(self.conversion_slope))

        self.manual_position = 0 # 0 nm
        self.startpos = 0
        self.stoppos = 0
        self.steppos = 0

        self.application: QApplication = application
        args = self.application.arguments()

        super(Ui, self).__init__()
        uic.loadUi(uiresource, self)
        if len(args) != 1:
            self.setWindowTitle("McPherson Monochromator Control (Debug Mode)")
        else:
            self.setWindowTitle("McPherson Monochromator Control (Hardware Mode)")

        self.is_conv_set = False # Use this flag to set conversion

        #  Picoammeter init.
        if len(args) != 1:
            self.pa = pico.Picodummy(3)
        else:
            self.pa = pico.Picoammeter(3)

        #  KST101 init.
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

        # Move to 1mm (0nm)
        # self.motor_ctrl.move_to(1 * MM_TO_IDX, True)

        # GUI init.
        self.scan_button = self.findChild(QPushButton, "begin_scan_button")
        self.save_data_checkbox = self.findChild(QCheckBox, "save_data_checkbox")
        self.auto_prefix_box = self.findChild(QLineEdit, "scancon_prefix_lineedit")
        self.manual_prefix_box = self.findChild(QLineEdit, "mancon_prefix_lineedit")
        self.dir_box = self.findChild(QLineEdit, "save_dir_lineedit")
        # self.auto_dir_box = self.findChild(QLineEdit, "lineEdit_7")
        # self.manual_dir_box = self.findChild(QLineEdit, "lineEdit_9")
        self.start_spin = self.findChild(QDoubleSpinBox, "start_set_spinbox")
        self.stop_spin = self.findChild(QDoubleSpinBox, "end_set_spinbox")
        self.step_spin = self.findChild(QDoubleSpinBox, "step_set_spinbox")

        # These UI elements moved to begin programmatically created within the status bar.
        self.currpos_mm_disp = self.findChild(QLabel, "currpos_nm")
        # self.currpos_lcd_disp: QLCDNumber = self.findChild(QLCDNumber, 'currpos_lcd')
        # get the palette
        palette = self.currpos_mm_disp.palette()

        # foreground color
        palette.setColor(palette.WindowText, QColor(255, 0, 0))
        # background color
        palette.setColor(palette.Background, QColor(0, 170, 255))
        # "light" border
        palette.setColor(palette.Light, QColor(80, 80, 255))
        # "dark" border
        palette.setColor(palette.Dark, QColor(0, 255, 0))

        # set the palette
        self.currpos_mm_disp.setPalette(palette)
        # if digital_7_italic_22 is not None:
        #     self.currpos_mm_disp.setFont(digital_7_italic_22)
        # self.currpos_steps_disp = self.findChild(QLabel, "currpos_steps")
        self.scan_status = self.findChild(QLabel, "status_label")
        # if digital_7_16 is not None:
        #     self.scan_status.setFont(digital_7_16)
        self.scan_progress = self.findChild(QProgressBar, "progressbar")
        

        save_config_btn: QPushButton = self.findChild(QPushButton, 'save_config_button')
        save_config_btn.clicked.connect(self.showConfigWindow)


        self.pos_spin: QDoubleSpinBox = self.findChild(QDoubleSpinBox, "pos_set_spinbox")
        self.move_to_position_button: QPushButton = self.findChild(QPushButton, "move_pos_button")
        self.collect_data: QPushButton = self.findChild(QPushButton, "collect_data_button")
        self.plotFrame: QWidget = self.findChild(QWidget, "data_graph")
        # self.mainPlotFrame: QWidget = self.findChild(QWidget, "mainGraph")
        # self.plotBtnFrame: QWidget = self.findChild(QWidget, 'frame')
        self.xmin_in: QLineEdit = self.findChild(QLineEdit, "xmin_in")
        self.ymin_in: QLineEdit = self.findChild(QLineEdit, "ymin_in")
        self.xmax_in: QLineEdit = self.findChild(QLineEdit, "xmax_in")
        self.ymax_in: QLineEdit = self.findChild(QLineEdit, "ymax_in")
        self.plot_autorange: QCheckBox = self.findChild(QCheckBox, "autorange_checkbox")
        self.plot_clear_plots: QPushButton = self.findChild(QPushButton, "clear_plots_button")

        self.xdata: list = [] # collection of xdata
        self.ydata: list = [] # collection of ydata

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

        self.manual_prefix_box.setText(self.manual_prefix)
        self.auto_prefix_box.setText(self.auto_prefix)
        self.dir_box.setText(self.manual_dir)

        self.scan_button.clicked.connect(self.scan_button_pressed)
        self.collect_data.clicked.connect(self.manual_collect_button_pressed)
        self.move_to_position_button.clicked.connect(self.move_to_position_button_pressed)
        self.save_data_checkbox.stateChanged.connect(self.save_checkbox_toggled)
        self.auto_prefix_box.editingFinished.connect(self.auto_prefix_changed)
        self.manual_prefix_box.editingFinished.connect(self.manual_prefix_changed)
        self.dir_box.editingFinished.connect(self.manual_dir_changed)
        self.start_spin.valueChanged.connect(self.start_changed)
        self.stop_spin.valueChanged.connect(self.stop_changed)
        self.step_spin.valueChanged.connect(self.step_changed)
        self.pos_spin.setValue(self.conversion_slope * (self.manual_position + self.zero_ofst))
        
        # self.pos_spin.setValue(0)
        self.pos_spin.valueChanged.connect(self.manual_pos_changed)

        self.scan = Scan(weakref.proxy(self))

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_position_displays)
        self.timer.start(100)

        self.show()

    def clearPlotFcn(self):
        print('clear called')
        if not self.scanRunning:
            self.plotCanvas.axes.cla()
            self.plotCanvas.axes.set_xlabel('Location (nm)')
            self.plotCanvas.axes.set_ylabel('Photo Current (pA)')
            self.plotCanvas.axes.grid()
            self.plotCanvas.draw()
            self.xdata = []
            self.ydata = []
        return

    def updatePlot(self):
        print('Update called')
        self.plotCanvas.axes.cla()
        self.plotCanvas.axes.set_xlabel('Location (nm)')
        self.plotCanvas.axes.set_ylabel('Photo Current (pA)')
        for idx in range(len(self.xdata)):
            if len(self.xdata[idx]) == len(self.ydata[idx]):
                self.plotCanvas.axes.plot(self.xdata[idx], self.ydata[idx], label = 'Scan %d'%(idx + 1))
        self.plotCanvas.axes.legend()
        self.plotCanvas.axes.grid()
        self.plotCanvas.draw()
        return

    def scan_statusUpdate_slot(self, status):
        self.scan_status.setText('"<html><head/><body><p><span style=" font-weight:600;">%s</span></p></body></html>"'%(status))

    def scan_progress_slot(self, curr_percent):
        self.scan_progress.setValue(curr_percent)

    def scan_complete_slot(self):
        self.scan_button.setText('Begin Scan')
        self.scan_status.setText('"<html><head/><body><p><span style=" font-weight:600;">IDLE</span></p></body></html>"')
        self.scan_progress.reset()

    def update_position_displays(self):
        self.current_position = self.motor_ctrl.get_position()
        self.moving = self.motor_ctrl.is_moving()
        # print(self.current_position)
        self.currpos_mm_disp.setText('<b><i>%3.4f</i></b>'%(((self.current_position / MM_TO_IDX) / self.conversion_slope) - self.zero_ofst))
        # self.currpos_lcd_disp.display(((self.current_position / MM_TO_IDX) / self.conversion_slope) - self.zero_ofst)
        # self.currpos_steps_disp.setText('%d steps'%(self.current_position))

    def scan_button_pressed(self):
        print("Scan button pressed!")
        if not self.scanRunning:
            self.scan.start()
            self.scan_button.setText('Stop Scan')
        else:
            self.scanRunning = False
            self.scan_button.setText('Begin Scan')

    def manual_collect_button_pressed(self):
        print("Manual collect button pressed!")
        self.take_data()

    def move_to_position_button_pressed(self):
        self.moving = True
        print("Conversion slope: " + str(self.conversion_slope))
        print("Manual position: " + str(self.manual_position))
        print("Move to position button pressed, moving to %d mm"%(self.manual_position))
        self.motor_ctrl.move_to(self.manual_position * MM_TO_IDX, False)

    def save_checkbox_toggled(self):
        print("Save checkbox toggled.")
        self.save_data = not self.save_data

    # def prefix_changed(self):
    #     print("Prefix changed to: %s"%(self.prefix_box.text()))
    #     self.prefix = self.prefix_box.text()

    def manual_prefix_changed(self):
        print("Prefix changed to: %s"%(self.manual_prefix_box.text()))
        self.manual_prefix = self.manual_prefix_box.text()

    def auto_prefix_changed(self):
        print("Prefix changed to: %s"%(self.auto_prefix_box.text()))
        self.auto_prefix = self.auto_prefix_box.text()

    def manual_dir_changed(self):
        print("Prefix changed to: %s"%(self.manual_dir_box.text()))
        self.manual_dir = self.manual_dir_box.text()

    def auto_dir_changed(self):
        print("Prefix changed to: %s"%(self.auto_dir_box.text()))
        self.auto_dir = self.auto_dir_box.text()

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

        tnow = dt.datetime.now()

        filename = self.manual_dir + '/' + self.manual_prefix + '_' + tnow.strftime('%Y%m%d%H%M%S') + "_data.csv"
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        self.sav_file = open(filename, 'w')
        
        self.sav_file.write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
        self.sav_file.write('# Steps/mm: %f\n'%(MM_TO_IDX))
        self.sav_file.write('# Position (step),Current(A),Timestamp,Error Code\n')
        pos = self.motor_ctrl.get_position()
        self.current_position = pos
        self.sav_file.write(self.pa.sample_data())

        self.sav_file.close()

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
        # if idx != len(self.grating_combo_lstr) - 1:
        #     self.grating_density = float(self.grating_combo_lstr[idx])
        #     self.current_grating_idx = idx
        # else:
        #     self.showGratingWindow()
        # if idx == len(self.grating_combo_lstr) - 1:
        #     self.grating_combo.setCurrentIndex(self.current_grating_idx)
        # else:
        #     self.current_grating_idx = self.grating_combo.currentIndex()
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
            # self.machine_conf_win.setWindowFlags(self.machine_conf_win.windowFlags().setFlag(WindowContextHelpButtonHint, False))

            self.grating_combo: QComboBox = self.machine_conf_win.findChild(QComboBox, 'grating_combo_2')
            self.grating_combo.addItems(self.grating_combo_lstr)
            print(self.current_grating_idx)
            self.grating_combo.setCurrentIndex(self.current_grating_idx)
            self.grating_combo.activated.connect(self.newGratingItem)
            # self.grating_density_in = self.machine_conf_win.findChild(QDoubleSpinBox, 'grating_density_in')
            # self.grating_density_in.setValue(self.grating_density)
            
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

        # self.conversion_slope = 2 / self.grating_density * 1e3 * np.cos(np.pi * self.incidence_ang / 180) * np.cos(np.pi * self.tangent_ang / 180) / self.arm_length * MM_TO_IDX / self.diff_order

        self.calculateConversionSlope()

        self.machine_conf_win.close()
    
    def calculateConversionSlope(self):
        self.conversion_slope = ((self.arm_length * self.diff_order * self.grating_density)/(2 * (m.cos(m.radians(self.tangent_ang))) * (m.cos(m.radians(self.incidence_ang))) * 1e6))

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
        print("Save to file? " + str(self.other.save_data))

        self.statusUpdate.emit("PREPARING")
        sav_file = None
        if (self.other.save_data):
            tnow = dt.datetime.now()
            
            filename = self.other.auto_dir + '/' + self.other.auto_prefix + '_' + tnow.strftime('%Y%m%d%H%M%S') + "_data.csv"
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            sav_file = open(filename, 'w')

        # self.statusUpdate.emit("MOVING")
        
        # self.motor_ctrl.move_to(self.startpos, True)
        
        # self.statusUpdate.emit("SAMPLING")
        print("SCAN QTHREAD")
        print("Start | Stop | Step")
        print(self.other.startpos, self.other.stoppos, self.other.steppos)
        if self.other.steppos == 0 or self.other.startpos == self.other.stoppos:
            self.complete.emit()
            return
        scanrange = np.arange(self.other.startpos, self.other.stoppos + self.other.steppos, self.other.steppos)
        # self.other.pa.set_samples(3)
        nidx = len(scanrange)
        if len(self.other.xdata) != len(self.other.ydata):
            self.other.xdata = []
            self.other.ydata = []
        pidx = len(self.other.xdata)
        self.other.xdata.append([])
        self.other.ydata.append([])
        self.other.scanRunning = True
        for idx, dpos in enumerate(scanrange):
            if not self.other.scanRunning:
                break
            self.statusUpdate.emit("MOVING")
            self.other.motor_ctrl.move_to(dpos * MM_TO_IDX, True)
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
            self.other.xdata[pidx].append((((pos / MM_TO_IDX) / self.other.conversion_slope)) - self.other.zero_ofst)
            self.other.ydata[pidx].append(-mes * 1e12)
            # print(self.other.xdata[pidx], self.other.ydata[pidx])
            self.other.updatePlot()
            if sav_file is not None:
                if idx == 0:
                    sav_file.write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
                    sav_file.write('# Steps/mm: %f\n'%(MM_TO_IDX))
                    sav_file.write('# Position (step),Mean Current(A),Status/Error Code\n')
                # process buf
                # 1. split by \n
                buf = '%d,%e,%d\n'%(pos, -mes, err)
                sav_file.write(buf)

        if (sav_file is not None):
            sav_file.close()
        self.other.scanRunning = False
        self.complete.emit()
        print('mainWindow reference in scan end: %d'%(sys.getrefcount(self.other) - 1))

# Main function.
if __name__ == '__main__':
    # There will be three separate GUIs:
    # 1. Initialization loading screen, where devices are being searched for and the current status and tasks are displayed. If none are found, display an error and an exit button.
    # 2. The device selection display, where devices can be selected and their settings can be changed prior to entering the control program.
    # 3. The control GUI (mainwindow.ui), where the user has control over what the device(s) do.
    
    application = QApplication(sys.argv)
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

    # Then, we load up the device selection UI.
    ui_file_name = exeDir + '/ui/grating_input.ui'
    ui_file = QFile(ui_file_name)
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)

    # Main GUI bootup.
    ui_file_name = exeDir + '/ui/' + "mainwindow_mk2.ui"
    ui_file = QFile(ui_file_name) # workaround to load UI file with pyinstaller
    if not ui_file.open(QIODevice.ReadOnly):
        print(f"Cannot open {ui_file_name}: {ui_file.errorString()}")
        sys.exit(-1)

    # Initializes the GUI.
    mainWindow = Ui(application, ui_file)
    
    # Example: Creating a new instrument. Should be done in a UI callback of some sort.
     # new_mono = instruments.Monochromator(241.0536, 32, 1)

    # Example: Getting a UI element from the .ui file, setting LCDNumber value.
     # lcd_milli = mainWindow.findChild(QtWidgets.QLCDNumber, "lcdNumber")
     # lcd_nano = mainWindow.findChild(QtWidgets.QLCDNumber, "lcdNumber_2")
     # lcd_milli.display(1)
     # lcd_nano.display(2)
    
    # Wait for the Qt loop to exit before exiting.
    ret = application.exec_() # block until
    print('mainwindow: %d'%(sys.getrefcount(mainWindow) - 1))
    print('motor: %d'%(sys.getrefcount(mainWindow.motor_ctrl) - 1))
    print('pa: %d'%(sys.getrefcount(mainWindow.pa) - 1))

    save_config = confp.ConfigParser()
    grating_lstr = mainWindow.grating_combo_lstr[:-1]
    gratingDensityStr = ''
    for obj in grating_lstr:
        gratingDensityStr += obj + ','
    gratingDensityStr = gratingDensityStr.rstrip(',')
    save_config['INSTRUMENT'] = {'gratingDensities': gratingDensityStr,
                                 'gratingDensityIndex': str(mainWindow.current_grating_idx),
                                 'diffractionOrder': str(mainWindow.diff_order),
                                 'zeroOffset': str(mainWindow.zero_ofst),
                                 'incidenceAngle': str(mainWindow.incidence_ang),
                                 'tangentAngle': str(mainWindow.tangent_ang),
                                 'armLength': str(mainWindow.arm_length)}
    
    with open(exeDir+'/config.ini', 'w') as confFile:
        save_config.write(confFile)

    del mainWindow
    sys.exit(ret)

# %%
