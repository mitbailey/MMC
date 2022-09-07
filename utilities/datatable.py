from __future__ import annotations
from PyQt5.QtWidgets import QTableWidget, QStyledItemDelegate, QHeaderView, QAbstractItemView, QCheckBox, QPushButton, QLineEdit, QTableWidgetItem
from PyQt5.QtCore import Qt
import numpy as np
from typing import TypedDict
import weakref

class CustomQLineEdit(QLineEdit):
    def __init__(self, id, contents, parent = None):
        super(CustomQLineEdit, self).__init__(contents, parent)
        self._id = id
    
    @property
    def id(self):
        return self._id

class CustomQCheckBox(QCheckBox):
    def __init__(self, id, parent = None):
        super(CustomQCheckBox, self).__init__(parent)
        self._id = id
    
    @property
    def id(self):
        return self._id

class TableRowRaw(TypedDict):
    id: int
    name: str
    x: np.ndarray
    y: np.ndarray
    plotted: bool
    plot_cb: CustomQCheckBox


class DataTableWidget(QTableWidget):
    def __init__(self, parent):
        super(DataTableWidget, self).__init__(parent)

        print("\n\nGIGANTO-PRINT\n\n")
        self.parent = weakref.proxy(parent)
        self.insertColumn(0)
        self.insertColumn(1)
        self.insertColumn(2)
        self.insertColumn(3)
        self.insertColumn(4)
        self.insertRow(0)
        self.recordedData = dict()#[int, TableRowRaw]
        # self.manualData: TableRowRaw = {'id': -1, 'name': 'Manual Scan', 'x': np.array([], dtype=float), 'y': np.array([], dtype=float), 'plotted': False, 'plot_cb': CustomQCheckBox(-1, self)}
        # self.manualData['plot_cb'].setDisabled(True)
        # self.manualData['plot_cb'].stateChanged.connect(self.plotCheckboxCb)
        # self.hasManualData = False
        # self.hadManualData = False
        self.selectedItem = None
        self.newItem = False
        self._scanId = 0
        self.rowMap = None
        self.existent_rows = []
        self.existent_rows.append(0)
        self.setHorizontalHeaderLabels(['Name', 'Start', 'Stop', 'Step', 'Plot'])
        # self.resizeColumnsToContents()
        # self.resizeRowsToContents()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(False)
        # self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.clicked.connect(self.tableSelectAction)

        self.insertData(np.random.random(10), np.random.random(10), False)
        self.insertData(np.random.random(10), np.random.random(10), False)
        self.insertData(np.random.random(10), np.random.random(10), False)
        self.insertData(np.random.random(10), np.random.random(10), False)

    def insertData(self, xdata: np.ndarray | None, ydata: np.ndarray | None, btn_disabled: bool = True, name_editable: bool = True) -> int: # returns the scan ID
        scanId = self._scanId
        self._scanId += 1
        if xdata is None:
            xdata = np.array([], dtype = float)
        if ydata is None:
            ydata = np.array([], dtype = float)
        self.recordedData[scanId] = {'id': scanId, 'name': '', 'x': xdata, 'y': ydata, 'plotted': True, 'plot_cb': CustomQCheckBox(scanId)}
        # [scanId, '', xdata, ydata, True, CustomQCheckBox(scanId, self)] # scanID, title, xdata, ydata, plotted, plot_checkbox
        self.recordedData[scanId]['plot_cb'].setChecked(True)
        self.recordedData[scanId]['plot_cb'].setDisabled(btn_disabled)
        self.recordedData[scanId]['plot_cb'].stateChanged.connect(self.plotCheckboxCb) # connect callback

        self.updateTableDisplay(scanId, name_editable)
        return (scanId)
    
    @property
    def scanId(self):
        return self._scanId

    def insertDataAt(self, scanId: int, xdata: np.ndarray | float, ydata: np.ndarray | float) -> int:
        if scanId not in self.recordedData.keys():
            return self.insertData(xdata, ydata)
        else:
            if isinstance(xdata, float):
                xdata = np.array([xdata], dtype=float)
            if isinstance(ydata, float):
                ydata = np.array([ydata], dtype=float)
            self.recordedData[scanId]['x'] = np.concatenate((self.recordedData[scanId]['x'], xdata))
            self.recordedData[scanId]['y'] = np.concatenate((self.recordedData[scanId]['y'], ydata))
            self.updateTableDisplay(scanId, name_editable=False)
        return scanId

    def enablePlotBtn(self, scanId: int):
        if scanId not in self.recordedData.keys():
            return
        self.recordedData[scanId]['plotted'] = True # plot by default if plot button is disabled
        self.recordedData[scanId]['plot_cb'].setDisabled(False)
    
    # def insertManualData(self, xdata: np.ndarray, ydata: np.ndarray):
    #     self.manualData[2] = np.concatenate((self.manualData[2], xdata))
    #     self.manualData[3] = np.concatenate((self.manualData[3], ydata))
    #     self.hasManualData = True
    #     self.updateTableDisplay(-1)
    #     pass

    def updateTableDisplay(self, scanId: int = None, name_editable: bool = True):
        if scanId is not None and isinstance(scanId, int):
            if self.rowMap is None or scanId not in self.rowMap:
                self.newItem = True
            else:
                # update this row only
                pass
        # if not self.hadManualData and self.hasManualData: # manual data has been added
        #     self.hadManualData = True
        #     if self.rowMap is None:
        #         self.rowMap = [-1]
        #     else:
        #         self.rowMap = [-1] + self.rowMap # append scanId -1 to the top
        if self.newItem or self.rowMap is None:
            # add it to the table or this is the first time things are happening
            # if self.hasManualData:
            #     self.hadManualData = True
            #     self.rowMap = [-1] # add that to the top
            # else:
            self.rowMap = []
            namedIds = []
            unnamedIds = []
            for idx in self.recordedData.keys():
                if len(self.recordedData[idx]['name']) == 0:
                    unnamedIds.append(idx)
                else:
                    namedIds.append(idx)
            self.rowMap += namedIds
            self.rowMap += unnamedIds
            print("Row Map:", self.rowMap)
            for row_idx, scan_idx in enumerate(self.rowMap):
                if row_idx not in self.existent_rows:
                    self.existent_rows.append(row_idx)
                    self.insertRow(row_idx)
                    print("Adding new row for row_idx %d."%(row_idx))

                print("In the loop:", row_idx, scan_idx)

                text = 'Scan #%d'%(scan_idx + 1) if len(self.recordedData[scan_idx]['name']) == 0 else '%s #%d'%(self.recordedData[scan_idx]['name'], scan_idx)
                if name_editable:
                    textEditor = CustomQLineEdit(scan_idx, text)
                    textEditor.editingFinished.connect(self.nameUpdated)
                    self.setCellWidget(row_idx, 0, textEditor)
                else:
                    self.setItem(row_idx, 0, QTableWidgetItem(text))
                xmin = 0
                try:
                    xmin = round(self.recordedData[scan_idx]['x'].min(), 4)
                except Exception:
                    pass
                
                xmax = 0
                try:
                    xmax = round(self.recordedData[scan_idx]['x'].max(), 4)
                except Exception:
                    pass

                self.setItem(row_idx, 1, QTableWidgetItem(str(xmin)))
                self.setItem(row_idx, 2, QTableWidgetItem(str(xmax)))
                # self.setItem(row_idx, 4, QTableWidgetItem(text))
                try:
                    self.setItem(row_idx, 3, QTableWidgetItem(str(round(np.diff(self.recordedData[scan_idx]['x'])[0], 4))))
                except Exception:
                    self.setItem(row_idx, 3, QTableWidgetItem(str(0)))
                if name_editable:
                    self.setCellWidget(row_idx, 4, self.recordedData[scan_idx]['plot_cb'])
            self.newItem = False

        self.updatePlots()

    def updatePlots(self):
        data = []
        # if self.hasManualData:
        #     data.append(self.manualData['x'], self.manualData['y'], self.manualData['name'])
        for scan_idx in self.recordedData.keys():
            if self.recordedData[scan_idx]['plotted']:
                text = 'Scan #%d'%(scan_idx + 1) if len(self.recordedData[scan_idx]['name']) == 0 else '%s #%d'%(self.recordedData[scan_idx]['name'], scan_idx + 1)
                data.append([self.recordedData[scan_idx]['x'], self.recordedData[scan_idx]['y'], text, scan_idx])
        self.parent.updatePlots(data) # updatePlots in Ui(QMainWindow)

    def nameUpdated(self):
        src: CustomQLineEdit = self.sender()
        text = src.text()
        text = text.lstrip().rstrip()
        self.recordedData[src.id]['name'] = text
        self.updatePlots()

    def plotCheckboxCb(self, state: Qt.CheckState):
        src: CustomQCheckBox = self.sender()
        state = src.checkState()
        # if src.id == -1: # manual data checkbox was changed
            # self.manualData['plotted'] = state == Qt.Checked
        # else:
        scanId = src.id
        print(state, scanId)
        self.recordedData[scanId]['plotted'] = state == Qt.Checked
        print(self.recordedData[scanId]['plotted'])
        self.updatePlots()

    def saveDataCb(self):
        pass

    def delDataCb(self):
        pass

    def deleteItem(self, row: int):
        if row < 0:
            return
        try:
            scanId = self.rowMap.index(row)
        except ValueError:
            print('Row %d invalid, len(rows) = %d?'%(row, len(self.rowMap)))
        if scanId in self.recordedData.keys():
            del self.recordedData[scanId]
            del self.rowMap[row]
        # elif scanId == -1: # for manual
        #     self.rowMap = None # just rebuild...
            # self.hasManualData = False
            # self.hadManualData = False
            # self.manualData['plotted'] = False
            # self.manualData['name'] = 'Manual Scan'
            # self.manualData['x'] = np.zeros([], dtype = float)     
            # self.manualData['y'] = np.zeros([], dtype = float)     
            # self.manualData['plot_cb'].setDisabled(True)
            # self.manualData['plot_cb'].setCheckState(Qt.Unchecked)
        self.updateTableDisplay()
        self.updatePlots()
        pass

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Delete and self.selectedItem is not None:
            # delete data
            row = self.selectedItem.row()
            print('Delete:', row)
            self.deleteItem(row)
        else:
            super(DataTableWidget, self).keyPressEvent(event) # propagate elsewhere

    def tableSelectAction(self, item: QTableWidgetItem):
        self.selectedItem = item
        print(item.row(), item.column())
        