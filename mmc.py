#
# @file mmc.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief 
# @version See Git tags for version information.
# @date 2022.07.14
# 
# @copyright Copyright (c) 2022
# 
#

from PyQt5 import uic
from PyQt5 import QtCore, QtGui, QtWidgets
# from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ARG, QAbstractItemModel, QFileInfo, qFuzzyCompare, QMetaObject, 
#         QModelIndex, QObject, Qt, QThread, QTime, QUrl)
# from PyQt5.QtGui import QColor, qGray, QImage, QPainter, QPalette
from PyQt5.QtMultimedia import (QAbstractVideoBuffer, QMediaContent, QMediaMetaData, QMediaPlayer, QMediaPlaylist, 
        QVideoFrame, QVideoProbe)
from PyQt5.QtMultimediaWidgets import QVideoWidget
# from PyQt5.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QListView,
        # QMessageBox, QPushButton, QSizePolicy, QSlider, QStyle, QToolButton, QVBoxLayout, QWidget, QMainWindow)

import instruments

# Imports .ui file.
class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi("mainwindow.ui", self)
        self.show()

# Main function.
if __name__ == '__main__':
    import sys
    application = QtWidgets.QApplication(sys.argv)

    # Initializes the GUI.
    mainWindow = Ui()

    # Example: Creating a new instrument. Should be done in a UI callback of some sort.
     # new_mono = instruments.Monochromator(241.0536, 32, 1)

    # Example: Getting a UI element from the .ui file, setting LCDNumber value.
     # lcd_milli = mainWindow.findChild(QtWidgets.QLCDNumber, "lcdNumber")
     # lcd_nano = mainWindow.findChild(QtWidgets.QLCDNumber, "lcdNumber_2")
     # lcd_milli.display(1)
     # lcd_nano.display(2)
    
    # Wait for the Qt loop to exit before exiting.
    sys.exit(application.exec_())