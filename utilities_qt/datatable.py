#
# @file datatable.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief 
# @version See Git tags for version information.
# @date 2022.09.07
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

from __future__ import annotations
from PyQt5.QtWidgets import QTableWidget, QStyledItemDelegate, QHeaderView, QAbstractItemView, QCheckBox, QPushButton, QLineEdit, QTableWidgetItem, QDialog, QHBoxLayout, QVBoxLayout, QLabel, QStyle
from PyQt5.QtCore import Qt, QItemSelection
from PyQt5.QtGui import QFont
import numpy as np
from typing import TypedDict
import weakref
import datetime as dt
from utilities import log

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
    ref_cb: CustomQCheckBox


class DataTableWidget(QTableWidget):
    def __init__(self, parent):
        super(DataTableWidget, self).__init__(parent)
        self.parent = weakref.proxy(parent)
        self.insertColumn(0)
        self.insertColumn(1)
        self.insertColumn(2)
        self.insertColumn(3)
        self.insertColumn(4)
        self.insertColumn(5)
        self.insertRow(0)
        self.recordedData = dict()
        self.recordedMetaData = dict()
        self.selectedItem = None
        self.newItem = False
        self._scanId = 0
        self.rowMap = None
        self._internal_insert_exec = False
        self.num_rows = 1
        self.__del_confirm_win: QDialog = None
        self.setHorizontalHeaderLabels(['Name', 'Start', 'Stop', 'Step', 'Plot', 'Ref'])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setStretchLastSection(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selectionModel().selectionChanged.connect(self.__tableSelectAction)
        self.currentRefId = -1
        # self.scan_idx = 0
        self.ref_data = None
        self.is_result = False

    def insertData(self, det_idx: int, global_scan_id: int, xdata: np.ndarray | None, ydata: np.ndarray | None, metadata: dict,  btn_disabled: bool = True, name_editable: bool = True) -> int: # returns the scan ID
        
        # scanId = self._scanId
        # self._scanId += 1


        if not self._internal_insert_exec:
            self.recordedMetaData[(global_scan_id, det_idx)] = metadata
        if xdata is None:
            xdata = np.array([], dtype = float)
        if ydata is None:
            ydata = np.array([], dtype = float)
        self.recordedData[(global_scan_id, det_idx)] = {'id': global_scan_id, 'name': '', 'x': xdata, 'y': ydata, 'plotted': True, 'plot_cb': CustomQCheckBox(global_scan_id), 'ref_cb': CustomQCheckBox(global_scan_id)}
        
        self.recordedData[(global_scan_id, det_idx)]['plot_cb'].setChecked(True)
        self.recordedData[(global_scan_id, det_idx)]['plot_cb'].setDisabled(btn_disabled)
        self.recordedData[(global_scan_id, det_idx)]['plot_cb'].stateChanged.connect(lambda: self.__plotCheckboxCb(det_idx)) # connect callback

        self.recordedData[(global_scan_id, det_idx)]['ref_cb'].setChecked(False)
        self.recordedData[(global_scan_id, det_idx)]['ref_cb'].setDisabled(False)
        self.recordedData[(global_scan_id, det_idx)]['ref_cb'].stateChanged.connect(lambda: self.__refCheckboxCb(det_idx)) # connect callback
        log.debug('Ref Checkbox ID:', global_scan_id)
        log.debug('Plot Checkbox:', self.recordedData[(global_scan_id, det_idx)]['plot_cb'])
        log.debug('Ref Checkbox:', self.recordedData[(global_scan_id, det_idx)]['ref_cb'])

        self.updateTableDisplay(det_idx, global_scan_id, name_editable)

        # self.scan_idx += 1
        # return (scanId)
    
    # @property
    # def scanId(self):
    #     return self._scanId

    # This is called from mmc.py which is called from scan.py. The data is stored here in recordedData.
    def insertDataAt(self, det_idx: int, global_scan_id: int, xdata: np.ndarray | float, ydata: np.ndarray | float) -> int:
        log.debug(f'global_scan_id: {global_scan_id}')
        log.debug(f'self.recordedData.keys(): {self.recordedData.keys()}')
        # self._scanId = scanId
        if (global_scan_id, det_idx) not in self.recordedData.keys():
            self._scanId = global_scan_id
            self._internal_insert_exec = True
            if isinstance(xdata, float):
                xdata = np.array([xdata], dtype=float)
            if isinstance(ydata, float):
                ydata = np.array([ydata], dtype=float)
            ret = self.insertData(det_idx, global_scan_id, xdata, ydata, dict())
            self._internal_insert_exec = False
            return ret
        else:
            if isinstance(xdata, float):
                xdata = np.array([xdata], dtype=float)
            if isinstance(ydata, float):
                ydata = np.array([ydata], dtype=float)
            log.debug(f"Appending {xdata} to the end of {self.recordedData[(global_scan_id, det_idx)]['x']} for global_scan_id {global_scan_id}")
            self.recordedData[(global_scan_id, det_idx)]['x'] = np.concatenate((self.recordedData[(global_scan_id, det_idx)]['x'], xdata))
            log.debug(f"Appending {ydata} to the end of {self.recordedData[(global_scan_id, det_idx)]['y']} for global_scan_id {global_scan_id}")
            self.recordedData[(global_scan_id, det_idx)]['y'] = np.concatenate((self.recordedData[(global_scan_id, det_idx)]['y'], ydata))
            self.updateTableDisplay(det_idx, global_scan_id, name_editable=False)
        return global_scan_id

    def markInsertFinished(self, det_idx: int, global_scan_id: int):
        log.debug('Marking insert finished for scan ID %d'%(global_scan_id))
        self.__enablePlotBtn(det_idx, global_scan_id)

    def __enablePlotBtn(self, det_idx: int, global_scan_id: int):
        if (global_scan_id, det_idx) not in self.recordedData.keys():
            log.error('Scan ID (%d, %d) not found in recorded data!'%(global_scan_id, det_idx))
            log.error('Recorded data keys: ', self.recordedData.keys())
            return
        self.recordedData[(global_scan_id, det_idx)]['plotted'] = True # plot by default if plot button is disabled
        self.recordedData[(global_scan_id, det_idx)]['plot_cb'].setChecked(True) # it is checked at this point

        log.debug('Enabling plot button for scan ID %d'%(global_scan_id))

        self.recordedData[(global_scan_id, det_idx)]['plot_cb'].setDisabled(False)
        # update just this row in the table
        if self.rowMap is None or global_scan_id not in self.rowMap:
            self.updateTableDisplay(det_idx, global_scan_id)
        if global_scan_id in self.rowMap:
            del self.rowMap[self.rowMap.index(global_scan_id)]
            self.updateTableDisplay(det_idx, global_scan_id)

    def plotsClearedCb(self, det_idx: int):
        for global_scan_id in self.recordedData.keys():
            self.recordedData[(global_scan_id, det_idx)]['plotted'] = False
            self.recordedData[(global_scan_id, det_idx)]['plot_cb'].setChecked(False)

    def updateTableDisplay(self, det_idx: int, global_scan_id: int = None, name_editable: bool = True):
        if global_scan_id is not None and isinstance(global_scan_id, int):
            if self.rowMap is None or global_scan_id not in self.rowMap:
                self.newItem = True
            else:
                # update this row only
                pass

        if self.newItem or self.rowMap is None:
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
            log.debug("Row Map:", self.rowMap)
            checkpoint = 0

            # log.debug('Checkpoint A: %d'%(checkpoint))
            checkpoint+=1

            if len(self.rowMap) > self.num_rows:
                    
                # log.debug('Checkpoint B: %d'%(checkpoint))
                checkpoint+=1

                log.debug('Allocating rows:', len(self.rowMap), self.num_rows)
                for ii in range(self.num_rows, len(self.rowMap)):
                    
                    # log.debug('Checkpoint C: %d'%(checkpoint))
                    checkpoint+=1

                    self.insertRow(ii)
                    log.debug("Adding new row for row_idx %d."%(ii))
                    self.num_rows += 1
                log.debug('After allocation:', self.num_rows, len(self.rowMap))
            
            for row_idx, (scan_idx, key_det_idx) in enumerate(self.rowMap):
                
                # log.debug('Checkpoint D: %d'%(checkpoint))
                checkpoint+=1

                text = 'Scan #%d'%(scan_idx + 1) if len(self.recordedData[(scan_idx, key_det_idx)]['name']) == 0 else '%s #%d'%(self.recordedData[(scan_idx, key_det_idx)]['name'], scan_idx)
                # text = 'Scan #%d'%(scanId) if len(self.recordedData[scan_idx]['name']) == 0 else '%s #%d'%(self.recordedData[scan_idx]['name'], scan_idx)

                # log.debug('Checkpoint E: %d'%(checkpoint))
                checkpoint+=1

                if name_editable:

                    # log.debug('Checkpoint F: %d'%(checkpoint))
                    checkpoint+=1

                    textEditor = CustomQLineEdit(scan_idx, text)

                    # log.debug('Checkpoint G: %d'%(checkpoint))
                    checkpoint+=1

                    textEditor.editingFinished.connect(self.__nameUpdated)

                    # log.debug('Checkpoint H: %d'%(checkpoint))
                    checkpoint+=1

                    self.setCellWidget(row_idx, 0, textEditor)

                    # log.debug('Checkpoint I: %d'%(checkpoint))
                    checkpoint+=1
                else:
                    # log.debug('Checkpoint J: %d'%(checkpoint))
                    checkpoint+=1

                    self.setItem(row_idx, 0, QTableWidgetItem(text))

                    # log.debug('Checkpoint K: %d'%(checkpoint))
                    checkpoint+=1
                xmin = 0
                try:
                    # log.debug('Checkpoint L: %d'%(checkpoint))
                    checkpoint+=1

                    xmin = round(self.recordedData[(scan_idx, key_det_idx)]['x'].min(), 4)

                    # log.debug('Checkpoint M: %d'%(checkpoint))
                    checkpoint+=1
                except Exception as e:
                    pass
                
                xmax = 0
                try:
                    # log.debug('Checkpoint N: %d'%(checkpoint))
                    checkpoint+=1
                    
                    xmax = round(self.recordedData[(scan_idx, key_det_idx)]['x'].max(), 4)
                    
                    # log.debug('Checkpoint O: %d'%(checkpoint))
                    checkpoint+=1
                except Exception:
                    pass

                # log.debug('Checkpoint P: %d'%(checkpoint))
                checkpoint+=1

                self.setItem(row_idx, 1, QTableWidgetItem(str(xmin)))

                # log.debug('Checkpoint Q: %d'%(checkpoint))
                checkpoint+=1

                self.setItem(row_idx, 2, QTableWidgetItem(str(xmax)))
                try:

                    # log.debug('Checkpoint R: %d'%(checkpoint))
                    checkpoint+=1

                    self.setItem(row_idx, 3, QTableWidgetItem(str(round(np.diff(self.recordedData[(scan_idx, key_det_idx)]['x'])[0], 4))))

                    # log.debug('Checkpoint S: %d'%(checkpoint))
                    checkpoint+=1

                except Exception:
                    self.setItem(row_idx, 3, QTableWidgetItem(str(0)))
                if name_editable:

                    # log.debug('Checkpoint T: %d'%(checkpoint))
                    checkpoint+=1

                    self.setCellWidget(row_idx, 4, self.recordedData[(scan_idx, key_det_idx)]['plot_cb'])

                try:
                    self.setCellWidget(row_idx, 5, self.recordedData[(scan_idx, key_det_idx)]['ref_cb'])
                except Exception:
                    self.setItem(row_idx, 5, QTableWidgetItem(str(0)))

                # log.debug('Checkpoint U: %d'%(checkpoint))
                checkpoint+=1

            self.newItem = False

        self.updatePlots(det_idx)

    def updatePlots(self, det_idx: int):
        log.debug('Update plots called...')
        log.debug('Current reference ID is %d'%(self.currentRefId))
        data = []
        for scan_idx in self.recordedData.keys():
            log.debug(f'Checkpoint A: {scan_idx}')
            if self.recordedData[scan_idx]['plotted']:
                text = 'Scan #%d'%(scan_idx[0] + 1) if len(self.recordedData[scan_idx]['name']) == 0 else '%s #%d'%(self.recordedData[scan_idx]['name'], scan_idx[0] + 1)
                
                # This next line is how we used to prepare and send the data before references and operations existed...
                # data.append([self.recordedData[scan_idx]['x'], self.recordedData[scan_idx]['y'], text, scan_idx])
                
                # This is the new way we send the data - by applying the reference operation first. This is also done in saveDataCb(...)
                # self.recordedData[self.currentRefId]
                if (self.ref_data is not None) and np.array_equal(self.recordedData[scan_idx]['x'], self.ref_data[0][0]):
                    log.debug('Current reference ID is set (%d), so performing operation...'%(self.currentRefId))
                    # First we set which operands we want in which order based on the QRadioButtons.
                    opx = np.copy(self.recordedData[scan_idx]['x'])
                    if self.parent.reference_operation:
                        # op1x = np.copy(self.recordedData[scan_idx]['x'])
                        op1y = np.copy(self.recordedData[scan_idx]['y'])
                        # op2x = np.copy(self.recordedData[self.currentRefId]['x'])
                        op2y = np.copy(self.ref_data[0][1])
                    else:
                        # op1x = np.copy(self.recordedData[self.currentRefId]['x'])
                        op1y = np.copy(self.ref_data[0][1])
                        # op2x = np.copy(self.recordedData[scan_idx]['x'])
                        op2y = np.copy(self.recordedData[scan_idx]['y'])

                    # Then we operate based on the operation selected in the QComboBox and append.
                    if self.parent.reference_operation == 0: # Multiply
                        # Multiply
                        data.append([opx, np.multiply(op1y, op2y), text + ' (RefID#%d)'%(self.currentRefId), scan_idx[0]])
                    elif self.parent.reference_operation == 1: # Divide
                        # Divide
                        data.append([opx, np.divide(op1y, op2y), text + ' (RefID#%d)'%(self.currentRefId), scan_idx[0]])
                    elif self.parent.reference_operation == 2: # Add
                        data.append([opx, np.add(op1y, op2y), text + ' (RefID#%d)'%(self.currentRefId), scan_idx[0]])
                    elif self.parent.reference_operation == 3: # Subtract
                        data.append([opx, np.subtract(op1y, op2y), text + ' (RefID#%d)'%(self.currentRefId), scan_idx[0]])
                    else:
                        # Unknown
                        log.error('Unknown operation index:', self.parent.reference_operation)
                else:
                    log.debug('No reference ID set (%d), so no operation necessary...'%(self.currentRefId))
                    # No operation necessary.
                    data.append([self.recordedData[scan_idx]['x'], self.recordedData[scan_idx]['y'], text, scan_idx[0]])

        # This updates the main plot in MainGUIWindow with the data we are passing to it.
        self.parent.update_plots(det_idx, data, self.is_result) # updatePlots in Ui(QMainWindow)

    def __nameUpdated(self):
        src: CustomQLineEdit = self.sender()
        text = src.text()
        text = text.lstrip().rstrip()
        text = text.split('#')[0].rstrip()
        self.recordedData[src.id]['name'] = text
        self.updatePlots()

    def __plotCheckboxCb(self, det_idx: int):
        src: CustomQCheckBox = self.sender()
        state = src.checkState()
        global_scan_id = src.id
        log.debug(state, global_scan_id)
        self.recordedData[(global_scan_id, det_idx)]['plotted'] = state == Qt.Checked
        log.debug(self.recordedData[(global_scan_id, det_idx)]['plotted'])
        self.updatePlots(det_idx)

    def __refCheckboxCb(self, det_idx: int):
        src: CustomQCheckBox = self.sender()
        state = src.checkState()
        global_scan_id = src.id

        log.debug(f'BEFORE currentRefId: {self.currentRefId}, global_scan_id: {global_scan_id}')

        if self.currentRefId > -1:
            self.recordedData[(self.currentRefId, det_idx)]['ref_cb'].setChecked(False)

        if global_scan_id == self.currentRefId:
            # self.recordedData[self.currentRefId]['ref_cb'].setChecked(False)
            self.currentRefId = -1
        else:
            self.currentRefId = global_scan_id

        log.debug(f'AFTER currentRefId: {self.currentRefId}, global_scan_id: {global_scan_id}')

        # To retrieve the data from a row:
        # self.recordedData[scanId]

        # log.debug(state, scanId)
        # self.recordedData[scanId]['plotted'] = state == Qt.Checked
        # log.debug(self.recordedData[scanId]['plotted'])

        # TODO: This will need to update only the Results tabs, not the raw tabs.
        log.error('Reference checkbox callback not implemented for multiple tabs yet.')
        # self.updatePlots(det_idx)

        if state == Qt.Checked:
            ref_data = []
            
            # [[array([0. , 0.1, 0.2, 0.3]), array([7.673988e+11, 6.499859e+11, 1.845185e+11, 8.461278e+11]), 'Scan #1', 0]]
            # [{'id': 0, 'name': '', 'x': array([0. , 0.1, 0.2, 0.3]), 'y': array([9.275461e+11, 9.555003e+11, 9.593626e+11, 8.850503e+11]), 'plotted': True, 'plot_cb': <utilities_qt.datatable.CustomQCheckBox object at 0x00000264D08083A0>, 'ref_cb': <utilities_qt.datatable.CustomQCheckBox object at 0x00000264D0808310>}]
            
            _data = [
                self.recordedData[(self.currentRefId, det_idx)]['x'],
                self.recordedData[(self.currentRefId, det_idx)]['y'],
                f'Scan #{self.currentRefId + 1}',
                self.currentRefId
            ]

            ref_data.append(_data)
            self.parent.register_ref_data(ref_data)
        
        else:
            self.parent.unregister_ref_data()

    def getRefData(self) -> tuple: # Return the data and the metadata
        if self.currentRefId in self.recordedData:
            data = self.recordedData[self.currentRefId]
        else:
            return (None, None)

        if self.currentRefId in self.recordedMetaData:
            metadata = self.recordedMetaData[self.currentRefId]
        else:
            metadata = None
        
        return (data, metadata)

    def saveDataCb(self) -> tuple: # just return the data and the metadata, let main handle the saving

        # Reference Data Note - With the addition of reference data and operations, this becomes slightly more complex. 

        if self.selectedItem is None:
            return (None, None)
        row = self.selectedItem

        if row >= len(self.rowMap):
            return (None, None)
        scanIdx = self.rowMap[row]

        if scanIdx in self.recordedData:
            data = self.recordedData[scanIdx]
            if (self.currentRefId > -1) and np.array_equal(data['x'], self.recordedData[self.currentRefId]['x']):
                # opx = np.copy(data['x'])
                # First we set which operands we want in which order based on the QRadioButtons.
                if self.parent.reference_order_meas_ref:
                    # op1x = np.copy(data['x'])
                    op1y = np.copy(data['y'])
                    # op2x = np.copy(self.recordedData[self.currentRefId]['x'])
                    op2y = np.copy(self.recordedData[self.currentRefId]['y'])
                else:
                    # op1x = np.copy(self.recordedData[self.currentRefId]['x'])
                    op1y = np.copy(self.recordedData[self.currentRefId]['y'])
                    # op2x = np.copy(data['x'])
                    op2y = np.copy(data['y'])

                # Then we operate based on the operation selected in the QComboBox and append.
                # TODONOW CHANGE FROM UIE_ CHECK DIRECTLY TO SELF.REFERENCE_OPERATION CHECK
                if self.parent.reference_operation == 0:
                    # Multiply
                    # data['x'] = np.multiply(op1x, op2x)
                    data['y'] = np.multiply(op1y, op2y)
                elif self.parent.reference_operation == 1:
                    # Divide
                    # data['x'] = np.divide(op1x, op2x)
                    data['y'] = np.divide(op1y, op2y)
                else:
                    # Unknown
                    log.error('Unknown operation index:', self.parent.reference_operation)
            else:
                # No operation necessary.
                pass
        else:
            data = None

        if scanIdx in self.recordedMetaData:
            metadata = self.recordedMetaData[scanIdx]
        else:
            metadata = None

        if data is None:
            return (None, None)
        elif not data['plot_cb'].isEnabled():
            return (None, None)
        else:
            return (data, metadata)


    def delDataCb(self):
        log.debug('Delete called')
        if self.selectedItem is None:
            return
        row = self.selectedItem
        if row >= len(self.rowMap):
            log.debug('Trying to delete row %d, rowMap length %d!'%(row, len(self.rowMap)), self.rowMap)
            return
        try:
            scanIdx = self.rowMap[row]
        except Exception:
            log.error('No scanIdx corresponding to rowMap :O ...', row, self.rowMap)
            return
        if scanIdx not in self.recordedData.keys():
            log.error('%d is not in recorded data! :O ... '%(scanIdx), self.recordedData.keys())
            self.__deleteRow(row)
            return
        try:
            plotCb: CustomQCheckBox = self.recordedData[scanIdx]['plot_cb']
            if not plotCb.isEnabled():
                return
        except Exception:
            log.error('Could not recover plotCb for %d! :O ... '%(scanIdx, self.recordedData.keys()))
        self.__delete_item_confirm = False
        # spawn confirmation window here
        self.__showDelConfirmWin(row, scanIdx)
        if self.__delete_item_confirm: # actually delete?
            log.info('\n\nGOING TO DELETE %d... '%(scanIdx), end = '')
            try:
                del self.recordedData[scanIdx]
            except Exception:
                pass
            try:
                del self.recordedMetaData[scanIdx]
            except Exception:
                pass
            self.__deleteRow(row)
            log.debug('DONE\n')
        self.__delete_item_confirm = False
        self.updatePlots()

    def __deleteRow(self, row: int):
        self.selectedItem = None
        self.num_rows -= 1
        self.removeRow(row)
        del self.rowMap[row]
        if self.num_rows == 0:
            self.num_rows = 1
            self.insertRow(0)

    def __showDelConfirmWin(self, row: int, global_scan_id: int, det_idx: int):
        if self.__del_confirm_win is None:
            self.__del_confirm_win = QDialog(self, Qt.WindowSystemMenuHint | Qt.WindowTitleHint)

            self.__del_confirm_win.setWindowTitle('Confirm Deletion of row %d'%(row))
            self.__del_confirm_win.setMinimumSize(320, 160)

            pixmapi = getattr(QStyle, 'SP_MessageBoxWarning')
            icon = self.style().standardIcon(pixmapi)
            self.__del_confirm_win.setWindowIcon(icon)

            self._del_prompt_label = QLabel('')
            ok_button = QPushButton('Agree')
            ok_button.clicked.connect(self.__signalAgree)
            ok_button.setFont(QFont('Segoe UI', 14))
            cancel_button = QPushButton('Cancel')
            cancel_button.clicked.connect(self.__signalCancel)
            cancel_button.setFont(QFont('Segoe UI', 14))

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
            self.__del_confirm_win.setLayout(layout)

        name = ''
        try:
            name = self.recordedData[(global_scan_id, det_idx)]['name']
        except Exception:
            name = ''

        if name == '':
            name = 'Scan'

        try:
            scan_start = self.recordedData[(global_scan_id, det_idx)]['x'].min()
        except Exception:
            scan_start = 0
        
        try:
            scan_end = self.recordedData[(global_scan_id, det_idx)]['x'].max()
        except Exception:
            scan_end = 0

        try:
            num_pts = len(self.recordedData[(global_scan_id, det_idx)]['x'] )
        except Exception:
            num_pts = 0
        text = 'Confirm for deletion:\n%s #%d: %.4f nm to %.4f nm (%d points)'%(name, global_scan_id + 1, scan_start, scan_end, num_pts)
        self._del_prompt_label.setText(text)
        self._del_prompt_label.setFont(QFont('Segoe UI', 12))
        self.__del_confirm_win.exec() # blocks

    def __signalAgree(self):
        self.__delete_item_confirm = True
        if self.__del_confirm_win is not None:
            self.__del_confirm_win.close()
    
    def __signalCancel(self):
        self.__delete_item_confirm = False
        if self.__del_confirm_win is not None:
            self.__del_confirm_win.close()

    def __deleteItem(self, row: int):
        # TODO: This assume that the row# == global_scan_id. This is not always the case.
        
        if row < 0:
            return
        try:
            scanId = self.rowMap.index(row)
        except ValueError:
            log.error('Row %d invalid, len(rows) = %d?'%(row, len(self.rowMap)))
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
            row = self.selectedItem
            log.info('Delete:', row)
            self.__deleteItem(row)
        else:
            super(DataTableWidget, self).keyPressEvent(event) # propagate elsewhere

    def __tableSelectAction(self, selected: QItemSelection, deselected: QItemSelection):
        selset = []
        deselset = []

        log.debug('Deselected Cell Location(s):', end='')
        for ix in deselected.indexes():
            log.debug('({0}, {1}) '.format(ix.row(), ix.column()), end='')
            deselset.append(ix.row())
        log.debug('')

        log.debug('Deselected Cell Location(s):', end='')
        for ix in selected.indexes():
            log.debug('({0}, {1}) '.format(ix.row(), ix.column()), end='')
            selset.append(ix.row())
        log.debug('')
        
        selset = list(set(selset))
        deselset = list(set(deselset))

        if len(selset) == 1:
            self.selectedItem = selset[0]
        else:
            self.selectedItem = None
        