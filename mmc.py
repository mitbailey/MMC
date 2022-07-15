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
from PyQt5.QtCore import (pyqtSignal, pyqtSlot, Q_ARG, QAbstractItemModel, QFileInfo, qFuzzyCompare, QMetaObject, 
        QModelIndex, QObject, Qt, QThread, QTime, QUrl)
from PyQt5.QtGui import QColor, qGray, QImage, QPainter, QPalette
from PyQt5.QtMultimedia import (QAbstractVideoBuffer, QMediaContent, QMediaMetaData, QMediaPlayer, QMediaPlaylist, 
        QVideoFrame, QVideoProbe)
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QListView,
        QMessageBox, QPushButton, QSizePolicy, QSlider, QStyle, QToolButton, QVBoxLayout, QWidget, QMainWindow)

# Imports .ui file.
class Ui(QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi("mainwindow.ui", self)
        self.show()

# Main function.
if __name__ == '__main__':
    import sys
    application = QApplication(sys.argv)

    # Create the main window.
    mainWindow = Ui()
    # mainWindow = QWidget()
    # mainWindow.setGeometry(100, 100, 350, 400)
    # mainWindow.setWindowTitle("This is the Title")
    # mainWindow.show()
    
    # Wait for the Qt loop to exit before exiting.
    sys.exit(application.exec_())