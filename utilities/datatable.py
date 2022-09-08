from __future__ import annotations
from PyQt5.QtWidgets import QTableWidget, QStyledItemDelegate, QHeaderView, QAbstractItemView, QCheckBox, QPushButton, QLineEdit, QTableWidgetItem, QDialog, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
import numpy as np
from typing import TypedDict
import weakref
import datetime as dt

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
        self.parent = weakref.proxy(parent)
        self.insertColumn(0)
        self.insertColumn(1)
        self.insertColumn(2)
        self.insertColumn(3)
        self.insertColumn(4)
        self.insertRow(0)
        self.recordedData = dict()
        self.recordedMetaData = dict()
        self.selectedItem = None
        self.newItem = False
        self._scanId = 0
        self.rowMap = None
        self._internal_insert_exec = False
        self.num_rows = 1
        self.del_confirm_win: QDialog = None
        self.setHorizontalHeaderLabels(['Name', 'Start', 'Stop', 'Step', 'Plot'])
        # self.resizeColumnsToContents()
        # self.resizeRowsToContents()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(False)
        # self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.clicked.connect(self.tableSelectAction)

        # self.insertData(np.random.random(10), np.random.random(10), dict(), btn_disabled=False)
        # self.insertData(np.random.random(10), np.random.random(10), dict(),btn_disabled=False)
        # self.insertData(np.random.random(10), np.random.random(10), dict(),btn_disabled=False)
        # self.insertData(np.random.random(10), np.random.random(10), dict(),btn_disabled=False)

    def insertData(self, xdata: np.ndarray | None, ydata: np.ndarray | None, metadata: dict,  btn_disabled: bool = True, name_editable: bool = True) -> int: # returns the scan ID
        scanId = self._scanId
        self._scanId += 1
        if not self._internal_insert_exec:
            self.recordedMetaData[scanId] = metadata
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
            self._internal_insert_exec = True
            ret = self.insertData(xdata, ydata, dict())
            self._internal_insert_exec = False
            return ret
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
        self.recordedData[scanId]['plot_cb'].setChecked(True) # it is checked at this point
        self.recordedData[scanId]['plot_cb'].setDisabled(False)
        # update just this row in the table
        if self.rowMap is None or scanId not in self.rowMap:
            self.updateTableDisplay(scanId)
        if scanId in self.rowMap:
            del self.rowMap[self.rowMap.index(scanId)]
            self.updateTableDisplay(scanId)


    
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

            if len(self.rowMap) > self.num_rows:
                print('Allocating rows:', len(self.rowMap), self.num_rows)
                for ii in range(self.num_rows, len(self.rowMap)):
                    self.insertRow(ii)
                    print("Adding new row for row_idx %d."%(ii))
                    self.num_rows += 1
                print('After allocation:', self.num_rows, len(self.rowMap))
            
            for row_idx, scan_idx in enumerate(self.rowMap):
                # print("In the loop:", row_idx, scan_idx)

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
                except Exception as e:
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
        text = text.split('#')[0].rstrip()
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

    def saveDataCb(self) -> tuple: # just return the data and the metadata, let main handle the saving
        if self.selectedItem is None:
            return (None, None)
        row = self.selectedItem.row()
        if row >= len(self.rowMap):
            return (None, None)
        scanIdx = self.rowMap[row]
        if scanIdx in self.recordedData:
            data = self.recordedData[scanIdx]
        else:
            data = None
        if scanIdx in self.recordedMetaData:
            metadata = self.recordedMetaData[scanIdx]
        else:
            metadata = None
        if data is None:
            return (None, None)
        else:
            return (data, metadata)

    def delDataCb(self):
        print('Delete called')
        if self.selectedItem is None:
            return
        row = self.selectedItem.row()
        if row >= len(self.rowMap):
            print('Trying to delete row %d, rowMap length %d!'%(row, len(self.rowMap)), self.rowMap)
            return
        try:
            scanIdx = self.rowMap[row]
        except Exception:
            print('No scanIdx corresponding to rowMap :O ...', row, self.rowMap)
            return
        if scanIdx not in self.recordedData.keys():
            print('%d is not in recorded data! :O ... '%(scanIdx), self.recordedData.keys())
            self._deleteRow(row)
            return
        self.__delete_item_confirm = False
        # spawn confirmation window here
        self.showDelConfirmWin(row, scanIdx)
        if self.__delete_item_confirm: # actually delete?
            print('\n\nGOING TO DELETE %d... '%(scanIdx), end = '')
            try:
                del self.recordedData[scanIdx]
            except Exception:
                pass
            try:
                del self.recordedMetaData[scanIdx]
            except Exception:
                pass
            self._deleteRow(row)
            print('DONE\n')
        self.__delete_item_confirm = False

    def _deleteRow(self, row: int):
        self.selectedItem = None
        self.num_rows -= 1
        self.removeRow(row)
        del self.rowMap[row]
        if self.num_rows == 0:
            self.num_rows = 1
            self.insertRow(0)

    def showDelConfirmWin(self, row: int, scan_id: int):
        if self.del_confirm_win is None:
            self.del_confirm_win = QDialog(self)

            self.del_confirm_win.setWindowTitle('Delete Row %d?'%(row))
            self.del_confirm_win.setMinimumSize(320, 160)

            self._del_prompt_label = QLabel('')
            ok_button = QPushButton('Agree')
            ok_button.clicked.connect(self.__signalAgree)
            cancel_button = QPushButton('Cancel')
            cancel_button.clicked.connect(self.__signalCancel)

            layout = QVBoxLayout()
            hlayout = QHBoxLayout()
            hlayout.addStretch(1)
            hlayout.addWidget(self._del_prompt_label)
            hlayout.addStretch(1)
            layout.addLayout(hlayout)
            hlayout = QHBoxLayout()
            hlayout.addWidget(ok_button)
            hlayout.addStretch(1)
            hlayout.addWidget(cancel_button)
            layout.addLayout(hlayout)
            self.del_confirm_win.setLayout(layout)

        try:
            scan_start = self.recordedData[scan_id]['x'].min()
        except Exception:
            scan_start = 0
        
        try:
            scan_end = self.recordedData[scan_id]['x'].max()
        except Exception:
            scan_end = 0

        try:
            num_pts = len(self.recordedData[scan_id]['x'] )
        except Exception:
            num_pts = 0
        text = 'Scan #%d: %.4f nm to %.4f nm (%d points)'%(scan_id, scan_start, scan_end, num_pts)
        self._del_prompt_label.setText(text)
        self.del_confirm_win.exec() # blocks

    def __signalAgree(self):
        self.__delete_item_confirm = True
        if self.del_confirm_win is not None:
            self.del_confirm_win.close()
    
    def __signalCancel(self):
        self.__delete_item_confirm = False
        if self.del_confirm_win is not None:
            self.del_confirm_win.close()

    def deleteItem(self, row: int):
        if row < 0:
            return
        try:
            scanId = self.rowMap.index(row)
        except ValueError:
            print('Row %d invalid, len(rows) = %d?'%(row, len(self.rowMap)))
        if scanId in self.recordedData.keys():
            del self.recordedData[scanId]
            if scanId in self.recordedMetaData:
                del self.recordedMetaData[scanId]
            del self.rowMap[row]
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
        