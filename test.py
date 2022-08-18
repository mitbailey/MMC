# Test program.

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QPushButton, QHBoxLayout, QLineEdit, QVBoxLayout
from PyQt5.QtGui import QIcon

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, tight_layout = True)
        self.axes = fig.add_subplot(111)
        self.axes.set_xlabel('Nothing to show')
        self.axes.set_ylabel('Nothing to show')
        super(MplCanvas, self).__init__(fig)

class App(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 status bar example - pythonspot.com'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.initUI()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        plotWidget = QWidget()
        plotLayout = QVBoxLayout()
        plotCanvas = MplCanvas(self, width=5, height=4, dpi=100)
        plotLayout.addWidget(plotCanvas)
        toolbar = NavigationToolbar(plotCanvas, self)
        plotLayout.addWidget(toolbar)
        plotWidget.setLayout(plotLayout)
        self.setCentralWidget(plotWidget)
        # self.statusBar().showMessage('Message in statusbar.')
        self.statusBar().addPermanentWidget(QLineEdit())
        self.b = QPushButton("Click Me!")
        self.statusBar().addPermanentWidget(self.b)
 
        self.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())