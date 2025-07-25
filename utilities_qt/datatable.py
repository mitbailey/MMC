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
        self.__del_confirm_win: QDialog = None
        self.setHorizontalHeaderLabels(['Name', 'Start', 'Stop', 'Step', 'Plot'])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.horizontalHeader().setStretchLastSection(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selectionModel().selectionChanged.connect(self.__tableSelectAction)
        # self.currentRefId = -1
        # self.ref_data = None
        self.is_result = False
        # self.reference_operation = 0
        # self.advanced_ref = False
        self.row_to_id_det_map = dict()

    def insertData(self, det_idx: int, global_scan_id: int, xdata: np.ndarray | None, ydata: np.ndarray | None, metadata: dict,  btn_disabled: bool = True, name_editable: bool = True) -> int: # returns the scan ID
        
        if not self._internal_insert_exec:
            self.recordedMetaData[(global_scan_id, det_idx)] = metadata
        if xdata is None:
            xdata = np.array([], dtype = float)
        if ydata is None:
            ydata = np.array([], dtype = float)
        self.recordedData[(global_scan_id, det_idx)] = {'id': global_scan_id, 'name': '', 'x': xdata, 'y': ydata, 'plotted': True, 'plot_cb': CustomQCheckBox(global_scan_id)}
        
        self.recordedData[(global_scan_id, det_idx)]['plot_cb'].setChecked(True)
        self.recordedData[(global_scan_id, det_idx)]['plot_cb'].setDisabled(btn_disabled)
        self.recordedData[(global_scan_id, det_idx)]['plot_cb'].stateChanged.connect(lambda: self.__plotCheckboxCb(det_idx)) # connect callback

        log.debug('Plot Checkbox:', self.recordedData[(global_scan_id, det_idx)]['plot_cb'])

        self.updateTableDisplay(det_idx, global_scan_id, name_editable)

    # This is called from mmc.py which is called from scan.py. The data is stored here in recordedData.
    def insertDataAt(self, det_idx: int, global_scan_id: int, xdata: np.ndarray | float, ydata: np.ndarray | float) -> int:
        log.debug(f'global_scan_id: {global_scan_id}')
        log.debug(f'self.recordedData.keys(): {self.recordedData.keys()}')

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

    def plotsClearedCb(self):
        for key in self.recordedData.keys():
            self.recordedData[key]['plotted'] = False
            if self.recordedData[key]['plot_cb'] is not None:
                try:
                    self.recordedData[key]['plot_cb'].setChecked(False)
                except Exception as e:
                    log.warn('Could not set plot checkbox for scan ID %d, as its probably been deleted: %s'%(key[0], e))

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

            if len(self.rowMap) > self.num_rows:
                    
                log.debug('Allocating rows:', len(self.rowMap), self.num_rows)
                for ii in range(self.num_rows, len(self.rowMap)):
                    
                    self.insertRow(ii)
                    log.debug("Adding new row for row_idx %d."%(ii))
                    self.num_rows += 1
                log.debug('After allocation:', self.num_rows, len(self.rowMap))
            
            for row_idx, (scan_idx, key_det_idx) in enumerate(self.rowMap):
                
                text = 'Scan #%d'%(scan_idx + 1) if len(self.recordedData[(scan_idx, key_det_idx)]['name']) == 0 else '%s #%d'%(self.recordedData[(scan_idx, key_det_idx)]['name'], scan_idx)


                if name_editable:
                    textEditor = CustomQLineEdit(scan_idx, text)
                    textEditor.editingFinished.connect(self.__nameUpdated)
                    self.setCellWidget(row_idx, 0, textEditor)
                else:
                    self.setItem(row_idx, 0, QTableWidgetItem(text))

                xmin = 0
                try:
                    xmin = round(self.recordedData[(scan_idx, key_det_idx)]['x'].min(), 4)
                except Exception as e:
                    pass
                
                xmax = 0
                try:
                    xmax = round(self.recordedData[(scan_idx, key_det_idx)]['x'].max(), 4)
                except Exception:
                    pass
                
                # Here we create a mapping between rows and scan IDs/detectors.
                self.row_to_id_det_map[row_idx] = (scan_idx, key_det_idx)

                self.setItem(row_idx, 1, QTableWidgetItem(str(xmin)))

                self.setItem(row_idx, 2, QTableWidgetItem(str(xmax)))
                try:
                    self.setItem(row_idx, 3, QTableWidgetItem(str(round(np.diff(self.recordedData[(scan_idx, key_det_idx)]['x'])[0], 4))))

                except Exception:
                    self.setItem(row_idx, 3, QTableWidgetItem(str(0)))
                if name_editable:
                    try:
                        self.setCellWidget(row_idx, 4, self.recordedData[(scan_idx, key_det_idx)]['plot_cb'])
                    except Exception as e:
                        log.error('Exception:', e)
                        log.error('Tried to find "plot_cb" in ', self.recordedData[(scan_idx, key_det_idx)])
                        raise e

            self.newItem = False

        self.updatePlots(det_idx)

    def updatePlots(self, det_idx: int):
        log.debug('Update plots called...')
        # log.debug('Current reference ID is %d'%(self.currentRefId))
        data = []
        for scan_idx in self.recordedData.keys():
            log.debug(f'Checkpoint A: {scan_idx}')
            if self.recordedData[scan_idx]['plotted']:
                text = 'Scan #%d'%(scan_idx[0] + 1) if len(self.recordedData[scan_idx]['name']) == 0 else '%s #%d'%(self.recordedData[scan_idx]['name'], scan_idx[0] + 1)
                
                data.append([self.recordedData[scan_idx]['x'], self.recordedData[scan_idx]['y'], text, scan_idx[0]])

        # This updates the main plot in MainGUIWindow with the data we are passing to it.
        self.parent.update_plots(det_idx, data, self.is_result) # updatePlots in Ui(QMainWindow)

    def __nameUpdated(self):
        src: CustomQLineEdit = self.sender()
        text = src.text()
        text = text.lstrip().rstrip()
        text = text.split('#')[0].rstrip()
        which_detector = self.parent.UIE_mgw_table_qtw.currentIndex() - 1
        self.recordedData[(src.id, which_detector)]['name'] = text
        self.updatePlots(which_detector)

    def __plotCheckboxCb(self, det_idx: int):
        src: CustomQCheckBox = self.sender()
        state = src.checkState()
        global_scan_id = src.id
        log.debug(state, global_scan_id)
        self.recordedData[(global_scan_id, det_idx)]['plotted'] = state == Qt.Checked
        log.debug(self.recordedData[(global_scan_id, det_idx)]['plotted'])
        self.updatePlots(det_idx)

    # def getRefData(self) -> tuple: # Return the data and the metadata
    #     if self.currentRefId in self.recordedData:
    #         data = self.recordedData[self.currentRefId]
    #     else:
    #         return (None, None)

    #     if self.currentRefId in self.recordedMetaData:
    #         metadata = self.recordedMetaData[self.currentRefId]
    #     else:
    #         metadata = None
        
    #     return (data, metadata)

    def saveDataCb(self) -> tuple: # just return the data and the metadata, let main handle the saving
        return self.save_data_auto()

    # TODO: Since we take into account any references prior to returning the data, we need a way to bypass this, since we use this function to obtain the pre-reference-operated data for any new referencing.
    def save_data_auto(self, scanIdx=None, which_detector=None) -> tuple:

        # Reference Data Note - With the addition of reference data and operations, this becomes slightly more complex. 

        log.debug(f'scanIdx: {scanIdx}, which_detector: {which_detector}')

        if scanIdx is None:
            if self.selectedItem is None or len(self.selectedItem) == 0:
                log.error('self.selectedItem is None!')
                return (None, None)
            
            row = self.selectedItem[0]

            if row >= len(self.rowMap):
                log.error(f'Trying to save row {row}, rowMap length {len(self.rowMap)}!', self.rowMap)
                return (None, None)
            scanIdx = self.rowMap[row][0]

            which_detector = self.parent.UIE_mgw_table_qtw.currentIndex() - 1

        log.debug(f'scanIdx: {scanIdx}, which_detector: {which_detector}')
        log.debug('self.recordedData keys:', self.recordedData.keys())

        if (scanIdx, which_detector) in self.recordedData:
            data = self.recordedData[(scanIdx, which_detector)]

        else:
            data = None
            log.error(f'No data found for scan ID {scanIdx} from detector {which_detector}.')

        if (scanIdx, which_detector) in self.recordedMetaData:
            metadata = self.recordedMetaData[(scanIdx, which_detector)]
        else:
            log.error(f'No metadata found for scan ID {scanIdx} from detector {which_detector}.')
            metadata = None

        if data is None:
            log.error('No data found for scan ID %d!'%(scanIdx))
            return (None, None)
        elif not data['plot_cb'].isEnabled():
            log.error('Plot button is disabled for scan ID %d!'%(scanIdx))
            return (None, None)
        else:
            log.info('Normal return from saveDataCb()')
            return (data, metadata)
        
    def delDataCb(self):
        log.debug('Delete called for:', self.selectedItem)

        if self.selectedItem is None:
            log.debug('self.selectedItem is None, returning.')
            return
        
        if type(self.selectedItem) is int:
            log.error('Selected item is an int instead of a list. This is unexpected.')
            return
        elif type(self.selectedItem) is not list:
            log.error('Selected item is not an int or list, but is type: ', type(self.selectedItem))
            self.parent.QMessageBoxCritical(
                'Error', 'Selection is not of type int (single) nor list (multiple). Please select a scan to delete data from.')
            return

        which_detector = self.parent.UIE_mgw_table_qtw.currentIndex() - 1

        # Handle the case where we have selected items in the results tab, where which_detector will be -1.
        if which_detector == -1:
            # We are deleting from the results tab.
            for which_detector_pseudo in range(self.parent.num_detectors):
                for selectedItem in self.selectedItem:
                    if selectedItem is None:
                        continue
                    
                    row = selectedItem
                    if row >= len(self.rowMap):
                        log.debug('Trying to delete row %d, rowMap length %d!'%(row, len(self.rowMap)), self.rowMap)
                        continue
                    try:
                        scanIdx = self.rowMap[row]
                    except Exception:
                        log.error('No scanIdx corresponding to rowMap :O ...', row, self.rowMap)
                        continue
                    
                    log.debug(f'scanIdx: {scanIdx}, which_detector: {which_detector_pseudo}')

                    key = (scanIdx[0], which_detector_pseudo)
                    log.debug(f'scanIdx: {scanIdx}, which_detector: {which_detector_pseudo}; key: {key}')
                    log.debug(f'rowMap: {self.rowMap}')

                    if key not in self.recordedData.keys():
                        log.error(f'{key} is not in recorded data: {self.recordedData.keys()}')
                        self.__deleteRow(row)
                        continue
                    try:
                        plotCb: CustomQCheckBox = self.recordedData[key]['plot_cb']
                        if not plotCb.isEnabled():
                            continue
                    except Exception as e:
                        log.error(f'Exception at {key}: {e}')
                    self.__delete_item_confirm = False
                    # spawn confirmation window here
                    self.__showDelConfirmWin(row, key[0], key[1])
                    if self.__delete_item_confirm: # actually delete?
                        log.info(f'Going to delete {key}... ', end = '')
                        try:
                            del self.recordedData[key]
                        except Exception:
                            pass
                        try:
                            del self.recordedMetaData[key]
                        except Exception:
                            pass
                        self.__deleteRow(row)
                        log.debug('DONE\n')
                    self.__delete_item_confirm = False

                    self.updatePlots(which_detector_pseudo)

        for selectedItem in self.selectedItem:
            if selectedItem is None:
                return
            row = selectedItem
            if row >= len(self.rowMap):
                log.debug('Trying to delete row %d, rowMap length %d!'%(row, len(self.rowMap)), self.rowMap)
                return
            try:
                scanIdx = self.rowMap[row]
            except Exception:
                log.error('No scanIdx corresponding to rowMap :O ...', row, self.rowMap)
                return
            
            # (scan_id, det_id) = self.row_to_id_det_map[scanIdx[0]]
            log.debug(f'scanIdx: {scanIdx}, which_detector: {which_detector}')

            key = (scanIdx[0], which_detector)
            log.debug(f'scanIdx: {scanIdx}, which_detector: {which_detector}; key: {key}')
            log.debug(f'rowMap: {self.rowMap}')

            # key = (scan_id, det_id)
            # log.debug(f'new key: {key}')

            if key not in self.recordedData.keys():
                log.error(f'{key} is not in recorded data: {self.recordedData.keys()}')
                self.__deleteRow(row)
                return
            try:
                plotCb: CustomQCheckBox = self.recordedData[key]['plot_cb']
                if not plotCb.isEnabled():
                    return
            except Exception as e:
                log.error(f'Exception at {key}: {e}')
            self.__delete_item_confirm = False
            # spawn confirmation window here
            self.__showDelConfirmWin(row, key[0], key[1])
            if self.__delete_item_confirm: # actually delete?
                log.info(f'Going to delete {key}... ', end = '')
                try:
                    del self.recordedData[key]
                except Exception:
                    pass
                try:
                    del self.recordedMetaData[key]
                except Exception:
                    pass
                self.__deleteRow(row)
                log.debug('DONE\n')
            self.__delete_item_confirm = False

            # Now we need to update the mapping.
            # self.row_to_id_det_map[row_idx] = (scan_idx, key_det_idx)


            self.updatePlots(which_detector)
        
        self.updateTableDisplay(which_detector)

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
        
        which_detector = self.parent.UIE_mgw_table_qtw.currentIndex() - 1

        if row < 0:
            return
        try:
            scanId = self.rowMap.index(row)
        except ValueError:
            log.error('Row %d invalid, len(rows) = %d?'%(row, len(self.rowMap)))
        if (scanId, which_detector) in self.recordedData.keys():
            del self.recordedData[(scanId, which_detector)]
            if (scanId, which_detector) in self.recordedMetaData:
                del self.recordedMetaData[(scanId, which_detector)]
            del self.rowMap[row]
        self.updateTableDisplay()
        self.updatePlots(which_detector)
        pass

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_Delete and self.selectedItem is not None:
            # delete data
            row = self.selectedItem[0]
            log.info('Delete:', row)
            self.__deleteItem(row)
        else:
            super(DataTableWidget, self).keyPressEvent(event) # propagate elsewhere

    def __tableSelectAction(self, selected: QItemSelection, deselected: QItemSelection):
        just_selected = []
        just_deselected = []

        # Gather the location which have been deselected.
        log.debug('Deselected cell location(s):', end='')
        for ix in deselected.indexes():
            log.debug('({0}, {1}) '.format(ix.row(), ix.column()), end='')
            just_deselected.append(ix.row())
        log.debug('')

        # Gather the location which have been selected.
        log.debug('Selected cell location(s):', end='')
        for ix in selected.indexes():
            log.debug('({0}, {1}) '.format(ix.row(), ix.column()), end='')
            just_selected.append(ix.row())
        log.debug('')
        
        # Make each list unique by turning it into a set and then back into a list.
        just_selected = list(set(just_selected))
        just_deselected = list(set(just_deselected))

        log.debug('just_selected:', just_selected)
        log.debug('just_deselected:', just_deselected)

        if self.selectedItem is None:
            # We just havent selected anything yet - first selection.
            currently_selected = just_selected
        else:
            currently_selected = set(self.selectedItem) - set(just_deselected)
            currently_selected = currently_selected.union(set(just_selected))
            currently_selected = list(currently_selected)
        
        log.debug('currently_selected:', currently_selected)

        log.debug(just_selected)

        self.selectedItem = currently_selected

        log.debug('self.selectedItem:', self.selectedItem)
        log.debug('type(self.selectedItem):', type(self.selectedItem))
        if len(self.selectedItem) > 0:
            log.debug('type(self.selectedItem[0]:', type(self.selectedItem[0]))


        # if len(selset) == 1:
        #     self.selectedItem = selset[0]
        # else:
        #     # self.selectedItem = None
        #     self.selectedItem = selset
        