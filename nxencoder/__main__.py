#!/usr/bin/env python

'''
nxEncoder GUI

Copyright (c) 2021 Simon Davie <nexx@nexxdesign.co.uk>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

from PyQt5.QtCore import Qt, QState, QStateMachine, QThread, pyqtSignal, QCoreApplication
from PyQt5.QtGui import QPainter
from PyQt5.QtSerialPort import QSerialPortInfo
from PyQt5.QtWidgets import QApplication, QFileDialog, QLineEdit, QMainWindow, QMessageBox

from helpers.printer_reprapfirmware import RepRapFirmware3
from helpers.serial_encoder import SerialEncoder
from helpers.worker_consistency import WorkerConsistency
from helpers.worker_esteps import WorkerEsteps
from resources.ui_mainwindow import Ui_MainWindow

import time


class MainWindow(QMainWindow, Ui_MainWindow):
    sig_serial_disable = pyqtSignal()
    sig_serial_enable = pyqtSignal()
    sig_encoder_connect = pyqtSignal()
    sig_encoder_disconnect = pyqtSignal()
    sig_printer_connect = pyqtSignal()
    sig_printer_disconnect = pyqtSignal()
    sig_chart_const_finished = pyqtSignal()

    working = False

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.current_tool = 0
        self.thread_printer = QThread()
        self.thread_worker = QThread()

        self.actn_save.triggered.connect(self.log_save)
        self.btn_encoder_connect.clicked.connect(self.encoder_connect)
        self.btn_encoder_disconnect.clicked.connect(self.encoder_disconnect)
        self.btn_encoder_refresh.clicked.connect(self.populate_serial_ports)
        self.btn_printer_connect.clicked.connect(self.printer_connect)
        self.btn_printer_disconnect.clicked.connect(self.printer_disconnect)
        self.btn_tool_home.clicked.connect(self.printer_move_home)
        self.btn_tool_center.clicked.connect(self.printer_move_center)
        self.btn_tool_heat.clicked.connect(self.printer_set_temperature)
        self.btn_tool_run.clicked.connect(self.printer_run)
        self.btn_estop.clicked.connect(self.printer_estop)
        self.cbx_printer_fwtype.currentIndexChanged.connect(self.fwtype_update)
        self.cbx_tool.currentIndexChanged.connect(self.gui_tool_update)
        self.tabMain.currentChanged.connect(self.gui_tab_update)

        self.init_gui()
        self.show()
        self.log_event('Logging started')

    def init_gui(self):
        ''' Set the start-up state for GUI elements, initialise the state
        machines, and finally populate the serial combobox and event log. '''
        self.state_serial = QStateMachine()
        self.state_serial_disconnected = QState(self.state_serial)
        self.state_serial_disconnected.assignProperty(self.lbl_encoder_status, 'text', 'Disonnected')
        self.state_serial_disconnected.assignProperty(self.lbl_encoder_status, 'styleSheet', 'color: rgb(170, 0, 0)')
        self.state_serial_disconnected.assignProperty(self.lbl_encoder_fw, 'text', 'N/A')
        self.state_serial_disconnected.assignProperty(self.cbx_encoder_port, 'enabled', True)
        self.state_serial_disconnected.assignProperty(self.btn_encoder_connect, 'enabled', True)
        self.state_serial_disconnected.assignProperty(self.btn_encoder_disconnect, 'enabled', False)
        self.state_serial_disconnected.assignProperty(self.btn_encoder_refresh, 'enabled', True)

        self.state_serial_connecting = QState(self.state_serial)
        self.state_serial_connecting.assignProperty(self.lbl_encoder_status, 'text', 'Connecting')
        self.state_serial_connecting.assignProperty(self.lbl_encoder_status, 'styleSheet', 'color: rgb(170, 170, 0)')
        self.state_serial_connecting.assignProperty(self.lbl_encoder_fw, 'text', 'N/A')
        self.state_serial_connecting.assignProperty(self.cbx_encoder_port, 'enabled', False)
        self.state_serial_connecting.assignProperty(self.btn_encoder_connect, 'enabled', False)
        self.state_serial_connecting.assignProperty(self.btn_encoder_disconnect, 'enabled', False)
        self.state_serial_connecting.assignProperty(self.btn_encoder_refresh, 'enabled', False)

        self.state_serial_connected = QState(self.state_serial)
        self.state_serial_connected.assignProperty(self.lbl_encoder_status, 'text', 'Connected')
        self.state_serial_connected.assignProperty(self.lbl_encoder_status, 'styleSheet', 'color: rgb(0, 170, 0)')
        self.state_serial_connected.assignProperty(self.cbx_encoder_port, 'enabled', False)
        self.state_serial_connected.assignProperty(self.btn_encoder_connect, 'enabled', False)
        self.state_serial_connected.assignProperty(self.btn_encoder_disconnect, 'enabled', True)
        self.state_serial_connected.assignProperty(self.btn_encoder_refresh, 'enabled', False)

        self.state_serial_disabled = QState(self.state_serial)
        self.state_serial_disabled.assignProperty(self.lbl_encoder_status, 'text', 'No serial ports detected')
        self.state_serial_disabled.assignProperty(self.btn_encoder_connect, 'enabled', False)
        self.state_serial_disabled.assignProperty(self.cbx_encoder_port, 'enabled', False)
        self.state_serial.setInitialState(self.state_serial_disconnected)

        self.state_serial_disconnected.addTransition(self.sig_encoder_connect, self.state_serial_connecting)
        self.state_serial_connecting.addTransition(self.sig_encoder_connect, self.state_serial_connected)
        self.state_serial_connecting.addTransition(self.sig_encoder_disconnect, self.state_serial_disconnected)
        self.state_serial_disconnected.addTransition(self.sig_serial_disable, self.state_serial_disabled)
        self.state_serial_disabled.addTransition(self.sig_serial_enable, self.state_serial_disconnected)
        self.state_serial_connected.addTransition(self.sig_encoder_disconnect, self.state_serial_disconnected)
        self.state_serial.start()

        self.state_printer = QStateMachine()
        self.state_printer_disconnected = QState(self.state_printer)
        self.state_printer_disconnected.assignProperty(self.lbl_printer_status, 'text', 'Disconnected')
        self.state_printer_disconnected.assignProperty(self.lbl_printer_status, 'styleSheet', 'color: rgb(170, 0, 0)')
        self.state_printer_disconnected.assignProperty(self.lbl_printer_fw, 'text', 'N/A')
        self.state_printer_disconnected.assignProperty(self.txt_printer_hostname, 'enabled', True)
        self.state_printer_disconnected.assignProperty(self.btn_printer_connect, 'enabled', True)
        self.state_printer_disconnected.assignProperty(self.btn_printer_disconnect, 'enabled', False)
        self.state_printer_disconnected.assignProperty(self.tabMain, 'enabled', False)
        self.state_printer_disconnected.assignProperty(self.cbx_tool, 'enabled', False)

        self.state_printer_connecting = QState(self.state_printer)
        self.state_printer_connecting.assignProperty(self.lbl_printer_status, 'text', 'Connecting')
        self.state_printer_connecting.assignProperty(self.lbl_printer_status, 'styleSheet', 'color: rgb(170, 170, 0)')
        self.state_printer_connecting.assignProperty(self.lbl_printer_fw, 'text', 'N/A')
        self.state_printer_connecting.assignProperty(self.txt_printer_hostname, 'enabled', False)
        self.state_printer_connecting.assignProperty(self.btn_printer_connect, 'enabled', False)
        self.state_printer_connecting.assignProperty(self.btn_printer_disconnect, 'enabled', False)

        self.state_printer_connected = QState(self.state_printer)
        self.state_printer_connected.assignProperty(self.lbl_printer_status, 'text', 'Connected')
        self.state_printer_connected.assignProperty(self.lbl_printer_status, 'styleSheet', 'color: rgb(0, 170, 0)')
        self.state_printer_connected.assignProperty(self.txt_printer_hostname, 'enabled', False)
        self.state_printer_connected.assignProperty(self.btn_printer_connect, 'enabled', False)
        self.state_printer_connected.assignProperty(self.btn_printer_disconnect, 'enabled', True)
        self.state_printer_connected.assignProperty(self.tabMain, 'enabled', True)
        self.state_printer_connected.assignProperty(self.cbx_tool, 'enabled', True)
        self.state_printer.setInitialState(self.state_printer_disconnected)

        self.state_printer_disconnected.addTransition(self.sig_printer_connect, self.state_printer_connecting)
        self.state_printer_connecting.addTransition(self.sig_printer_connect, self.state_printer_connected)
        self.state_printer_connecting.addTransition(self.sig_printer_disconnect, self.state_printer_disconnected)
        self.state_printer_connected.addTransition(self.sig_printer_disconnect, self.state_printer_disconnected)
        self.state_printer.start()

        self.worker_consistency = WorkerConsistency()
        self.chart_const_widget.setChart(self.worker_consistency.chart)
        self.chart_const_widget.setRenderHint(QPainter.Antialiasing)

        self.populate_serial_ports()
        self.cbx_printer_port.setHidden(True)

    def log_event(self, event):
        ''' Log text to the GUI event log. '''
        self.pte_eventlog.appendPlainText('[{}] {}'.format(time.strftime('%H:%M:%S', time.localtime()), event))

    def log_debug(self, event):
        ''' Log debug event to the GUI event log if the verbose option is
        enabled. '''
        if self.actn_verboselog.isChecked():
            self.log_event(event)

    def log_save(self):
        ''' Save the contents of the event log to a file chosen by QFileDialog. '''
        log_filename, _ = QFileDialog.getSaveFileName(self, 'Save the Event Log as...', 'eventlog.txt', 'Text files (*.txt)')
        f = open(log_filename, 'w')
        f.write(self.pte_eventlog.toPlainText())
        f.close()
        self.log_event('Log saved to {}'.format(log_filename))

    def error_critical(self, error):
        ''' Handle a critical error. Show the user a QMessageBox and also log
        the error to the event log. Optionally handle a detailed error to log
        to the verbose log. '''
        self.log_event(error)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText('A critical error has occured:')
        msg.setInformativeText(error)
        msg.setWindowTitle('Error')
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def results_popup(self, result):
        ''' Show the user a messagebox with the results of the test which has
        been run. '''
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle('Success!')
        msg.setStandardButtons(QMessageBox.Ok)

        if self.tabMain.currentIndex() == 0:
            msg.setText('The extruder calibration completed successfully.')
            msg.setInformativeText('The new extruder steps/mm value for tool {} has been calculated to be {}.\n\n'
                                   'You will need to update your printers configuration to use this new value.'.format(self.current_tool, result))
        if self.tabMain.currentIndex() == 1:
            grade = 'an average result.'
            if result >= -1.25 and result <= 1.25:
                grade = 'a good result.'
            if result >= -0.75 and result <= 0.75:
                grade = 'a great result!'
            if result >= -0.25 and result <= 0.25:
                grade = 'an excellent result!'
            msg.setText('The extruder consistency check has completed successfully.')
            msg.setInformativeText('The extruder for tool {} has an average deviation of {}%.\n\n'
                                   'This is {} '.format(self.current_tool, result, grade))
        if self.tabMain.currentIndex() == 2:
            msg.setText('NYI')
            msg.setInformativeText('NYI')

        msg.exec_()

    def populate_serial_ports(self):
        ''' Populate the encoder combobox with available system serial ports.
        Also called when the user hits the refresh button. '''
        self.cbx_encoder_port.clear()

        # FIXME: This fixes a bug where no serial ports are available on launch
        # but self.sig_serial_disable.emit() never fires.
        QCoreApplication.processEvents()
        self.serial_ports = QSerialPortInfo.availablePorts()
        if not self.serial_ports:
            self.log_debug('[SERIAL] No serial ports detected')
            self.sig_serial_disable.emit()
            return
        self.sig_serial_enable.emit()
        for port in self.serial_ports:
            self.log_debug('[SERIAL] Found port: {} - {}'.format(port.portName(), port.description()))
            self.cbx_encoder_port.addItem('{}: {}'.format(port.portName(), port.description()))

    def populate_printer_ports(self):
        ''' Populate the printer combobox with available system serial ports.
        Automatically omit the port used by the serial encoder if connected. '''
        self.cbx_printer_port.clear()
        for port in self.serial_ports:
            self.cbx_printer_port.addItem('{}: {}'.format(port.portName(), port.description()))

    def fwtype_update(self, index):
        ''' Signalled when the firmware type combobox is altered. This allows
        aspects of the GUI to be changed depending on the desired firmware. '''
        if index in [3, 5]:
            self.txt_printer_hostname.setHidden(True)
            self.cbx_printer_port.setHidden(False)
            self.lbl_printer_hostname_static.setText('Port')
            self.populate_printer_ports()
            return
        self.txt_printer_hostname.setHidden(False)
        self.cbx_printer_port.setHidden(True)
        self.lbl_printer_hostname_static.setText('Host or IP')

    def encoder_connect(self):
        ''' Connect to the serial encoder via the SerialEncoder class. '''
        port = self.serial_ports[self.cbx_encoder_port.currentIndex()].portName()
        self.log_event('Attempting connection to encoder on {}'.format(port))
        self.encoder = SerialEncoder()
        self.encoder.sig_log_event.connect(self.log_event)
        self.encoder.sig_log_debug.connect(self.log_debug)
        self.encoder.sig_handshake.connect(self.encoder_handshake)
        self.encoder.sig_error.connect(self.error_critical)
        self.encoder.sig_force_close.connect(self.encoder_disconnect)
        self.sig_encoder_connect.emit()
        self.encoder.connect(port)

    def encoder_disconnect(self):
        ''' Disconnect from the serial encoder. '''
        self.encoder.disconnect()
        self.encoder = None
        self.log_event('Closed connection to encoder')
        self.sig_encoder_disconnect.emit()

    def encoder_handshake(self):
        ''' The encoder returned a handshake, process and update the GUI with
        the details '''
        self.sig_encoder_connect.emit()
        self.log_event('Connected to encoder')
        self.log_debug('[SERIAL] Encoder Firmware: v{} - Built: {}'.format(self.encoder.firmware_version, self.encoder.firmware_date))
        self.lbl_encoder_fw.setText('v{} ({})'.format(self.encoder.firmware_version, self.encoder.firmware_date))

    def printer_connect(self):
        ''' Connect to the specified firmware '''
        self.log_event('Attempting connection to {} at {}'.format(self.cbx_printer_fwtype.currentText(), self.txt_printer_hostname.text()))
        if self.cbx_printer_fwtype.currentIndex() == 0:
            self.printer = RepRapFirmware3(self.txt_printer_hostname.text())

        self.printer.moveToThread(self.thread_printer)
        self.thread_printer.started.connect(self.printer.run)
        self.printer.sig_log_event.connect(self.log_event)
        self.printer.sig_log_debug.connect(self.log_debug)
        self.printer.sig_finished.connect(self.thread_printer.quit)
        self.printer.sig_connected.connect(self.printer_connected)
        self.printer.sig_error.connect(self.error_critical)
        self.printer.sig_force_close.connect(self.printer_force_close)
        self.printer.sig_data_update.connect(self.printer_update)
        self.printer.sig_temp_reached.connect(self.printer_temp_reached)
        self.thread_printer.start()
        self.sig_printer_connect.emit()

    def printer_connected(self):
        ''' The printer connection established sucessfully. '''
        self.sig_printer_connect.emit()
        self.lbl_printer_fw.setText(self.printer.fw_string)
        self.cbx_tool.clear()
        for tool, data in enumerate(self.printer.cfg_tools):
            self.cbx_tool.addItem('Tool {}'.format(tool))
        self.groupbox_settings.setEnabled(True)

    def printer_force_close(self):
        ''' A critical error occured in the printer class. Force
        close the connection and clean up. '''
        if self.printer is not None:
            self.printer.run_thread = False
        self.thread_printer.quit()
        self.thread_printer.started.disconnect()

        self.log_event('Error connecting to printer')
        self.printer = None
        self.sig_printer_disconnect.emit()
        self.groupbox_settings.setEnabled(False)

    def printer_update(self):
        ''' The printer has signalled that updated data is available. '''
        if self.printer is None:
            return
        tool_data = self.printer.cfg_tools[self.current_tool]
        self.txt_tool_curstep.setText('{}'.format(tool_data['stepsPerMm']))
        self.txt_tool_curtemp.setText('{} C'.format(tool_data['cur_temp']))

        if self.printer.homed and not self.working:
            self.btn_tool_center.setEnabled(True)

    def printer_disconnect(self):
        ''' Disconnect from the printer '''
        self.cbx_tool.clear()
        self.printer.disconnect()
        self.printer = None
        self.log_event('Closed connection to printer')
        self.sig_printer_disconnect.emit()
        self.groupbox_settings.setEnabled(False)

    def printer_temp_reached(self, tool):
        ''' The printer has signalled the tool has hit the
        requested temperature. '''
        if self.working:
            return
        if tool != self.current_tool:
            self.log_event('WARNING: Tool {} is at temperature, but it is not the active tool. Setting its temperature to 0C.'.format(tool))
            self.printer.set_tool_temperature(0, tool)
            return
        self.btn_tool_heat.setEnabled(True)
        self.btn_tool_run.setEnabled(True)

    def printer_move_home(self):
        ''' Attempt to home the printer '''
        self.printer.move_homeaxes()
        self.btn_tool_center.setEnabled(True)

    def printer_move_center(self):
        ''' Move current tool to middle of workspace. '''
        self.printer.move_tomiddle(self.current_tool)
        self.btn_tool_heat.setEnabled(True)

    def printer_set_temperature(self):
        ''' Set the current tool temperature. '''
        self.btn_tool_heat.setEnabled(False)
        self.btn_tool_run.setEnabled(False)
        self.log_event('Heating Tool {} to {} C'.format(self.current_tool, self.dsbx_tool_temp.text()))
        self.printer.set_tool_temperature(self.dsbx_tool_temp.text(), self.current_tool)

    def gui_tool_update(self, index):
        ''' Signalled when the tool combobox is altered. If we change tool, we
        must update aspects of the GUI and make sure the previous tool heater
        is disabled. '''
        if index != -1:
            self.log_event('Selecting tool {}'.format(index))
            if self.current_tool != index:
                self.printer.set_tool_temperature(0, self.current_tool)
            self.current_tool = index
            if self.printer.cfg_tools[index]['max_temp'] == 0:
                self.dsbx_tool_temp.setMaximum(250)
                return
            self.dsbx_tool_temp.setMaximum(self.printer.cfg_tools[index]['max_temp'])

    def gui_tab_update(self, index):
        ''' Signalled when the user changes tab on the bottom of the
        application. Use this to update the run button text to represent what
        it will do. '''
        if index == 0:
            self.btn_tool_run.setText('Run Extruder Calibration')
            return
        if index == 1:
            self.btn_tool_run.setText('Run Consistency Test')
            return
        if index == 2:
            self.btn_tool_run.setText('Run Volumetric Calculation')
            return

    def printer_estop(self):
        ''' Trigger an immediate emergency stop and then close all printer
        connections. '''
        self.log_event('**** EMERGENCY STOP TRIGGERED ****')
        self.printer.estop()
        self.printer_disconnect()

    def printer_run(self):
        ''' Triggered when the run button is pressed. We determine the correct
        test to run based upon tabMain.currentIndex(). '''
        self.working = True
        if self.tabMain.currentIndex() == 0:
            self.tabMain.setTabEnabled(1, False)
            self.tabMain.setTabEnabled(2, False)
            self.btn_tool_run.setEnabled(False)
            self.encoder.set_absolute()
            self.printer_calibrate_esteps()
            return
        if self.tabMain.currentIndex() == 1:
            self.tabMain.setTabEnabled(0, False)
            self.tabMain.setTabEnabled(2, False)
            self.btn_tool_run.setEnabled(False)
            self.printer_check_consistency()
            return
        if self.tabMain.currentIndex() == 2:
            self.tabMain.setTabEnabled(0, False)
            self.tabMain.setTabEnabled(1, False)
            return

    def printer_calibrate_esteps(self):
        ''' Run a calibration loop to calculate the extruder esteps. '''
        for i in self.tab_esteps.findChildren(QLineEdit):
            i.clear()

        self.txt_esteps_original.setText(str(self.printer.cfg_tools[self.current_tool]['stepsPerMm']))

        self.worker_esteps = WorkerEsteps()
        self.worker_esteps.moveToThread(self.thread_worker)
        self.worker_esteps.sig_encoder_measure.connect(self.encoder.measure)
        self.worker_esteps.sig_printer_send_gcode.connect(self.printer.send_gcode)
        self.worker_esteps.sig_log_debug.connect(self.log_debug)
        self.worker_esteps.sig_result_ready.connect(self.esteps_data_ready)
        self.worker_esteps.sig_finished.connect(self.esteps_finished)
        self.thread_worker.started.connect(self.worker_esteps.run)
        self.encoder.sig_measurement.connect(self.worker_esteps.handle_measurement)
        # FIXME: Perhaps alter the firmware to only report relative measurements
        self.encoder.set_relative()
        self.thread_worker.start()

    def esteps_data_ready(self):
        ''' Signalled when the esteps calibration worker has completed an
        iteration and the data is ready for the GUI. '''
        current_tool_esteps = self.printer.cfg_tools[self.current_tool]['stepsPerMm']

        results_num = len(self.worker_esteps.cal_results)
        results_pct = round((results_num / 20) * 100)
        self.progress_esteps.setValue(results_pct)

        # FIXME: Do sanity checking on the results. If they seem wildly inaccurate
        # warn the user and abort rather than set an esteps value which is obviously
        # wrong.
        if results_num <= 10:
            qle = self.tab_esteps.findChild(QLineEdit, 'txt_esteps_{}'.format(results_num - 1))
            qle.setText('{:.2f} mm'.format(self.worker_esteps.cal_results[results_num - 1]))
            qle = self.tab_esteps.findChild(QLineEdit, 'txt_esteps_pct_{}'.format(results_num - 1))
            qle.setText('{:.2f} %'.format((self.worker_esteps.cal_results[results_num - 1] / self.worker_esteps.distance_coarse) * 100))
            distance_avg = sum(self.worker_esteps.cal_results[0:10]) / len(self.worker_esteps.cal_results[0:10])
            distance_pct = distance_avg / self.worker_esteps.distance_coarse
            self.txt_esteps_coarse_avg.setText('{:.2f} mm'.format(distance_avg))
            self.txt_esteps_coarse_pct_avg.setText('{:.2f} %'.format(distance_pct * 100))
            self.txt_esteps_calculated.setText('{:.2f}'.format(current_tool_esteps / distance_pct))

        if results_num == 10:
            self.log_event('Calculated coarse eSteps: {:.2f}'.format(current_tool_esteps / distance_pct))
            current_tool_esteps = current_tool_esteps / distance_pct
            self.printer.set_tool_esteps('{:.2f}'.format(current_tool_esteps))

        if results_num >= 11:
            qle = self.tab_esteps.findChild(QLineEdit, 'txt_esteps_{}'.format(results_num - 1))
            qle.setText('{:.2f} mm'.format(self.worker_esteps.cal_results[results_num - 1]))
            qle = self.tab_esteps.findChild(QLineEdit, 'txt_esteps_pct_{}'.format(results_num - 1))
            qle.setText('{:.2f} %'.format((self.worker_esteps.cal_results[results_num - 1] / self.worker_esteps.distance_fine) * 100))
            distance_avg = sum(self.worker_esteps.cal_results[10:20]) / len((self.worker_esteps.cal_results[10:20]))
            distance_pct = distance_avg / self.worker_esteps.distance_fine
            self.txt_esteps_fine_avg.setText('{:.2f} mm'.format(distance_avg))
            self.txt_esteps_fine_pct_avg.setText('{:.2f} %'.format(distance_pct * 100))
            self.txt_esteps_calculated.setText('{:.2f}'.format(current_tool_esteps / distance_pct))

        if results_num == 20:
            self.log_event('Calculated final eSteps: {:.2f}'.format(current_tool_esteps / distance_pct))
            current_tool_esteps = current_tool_esteps / distance_pct
            self.printer.set_tool_esteps('{:.2f}'.format(current_tool_esteps))

    def printer_check_consistency(self):
        ''' Run a consistency loop to check the extruder. '''
        self.log_event('Beginning extruder consistency test. Please wait whilst this completes.')
        self.worker_consistency.moveToThread(self.thread_worker)
        self.worker_consistency.sig_encoder_measure.connect(self.encoder.measure)
        self.worker_consistency.sig_encoder_reset.connect(self.encoder.reset)
        self.worker_consistency.sig_printer_send_gcode.connect(self.printer.send_gcode)
        self.worker_consistency.sig_log_debug.connect(self.log_debug)
        self.worker_consistency.sig_finished.connect(self.const_finished)
        self.thread_worker.started.connect(self.worker_consistency.run)
        self.encoder.sig_measurement.connect(self.worker_consistency.handle_measurement)
        # FIXME: Perhaps alter the firmware to only report relative measurements
        self.encoder.set_relative()
        self.thread_worker.start()

    def esteps_finished(self):
        ''' Signalled when the esteps process has completed. We can now
        perform a report on the extruder steps. '''
        self.results_popup(self.printer.cfg_tools[self.current_tool]['stepsPerMm'])
        self.btn_tool_run.setEnabled(True)
        self.tabMain.setTabEnabled(1, True)
        self.tabMain.setTabEnabled(2, True)
        self.thread_worker.quit()
        self.thread_worker.started.disconnect()
        self.working = False

    def const_finished(self):
        ''' Signalled when the readings for the chart have completed. We can
        now perform a report on the extruder consistency. '''
        deviation_avg = round(sum(self.worker_consistency.cal_results) / len(self.worker_consistency.cal_results), 2)
        self.log_event('Extruder consistency test complete!')
        self.log_event('Average deviation: {}%'.format(deviation_avg))
        self.results_popup(deviation_avg)
        self.btn_tool_run.setEnabled(True)
        self.tabMain.setTabEnabled(0, True)
        self.tabMain.setTabEnabled(2, True)
        self.thread_worker.quit()
        self.thread_worker.started.disconnect()
        self.working = False

    def chart_vol_finished(self):
        ''' Signalled when the readings for the chart have completed. We can
        now perform a report on the maximum volumetric throughput. '''
        self.btn_tool_run.setEnabled(True)
        self.tabMain.setTabEnabled(0, True)
        self.tabMain.setTabEnabled(1, True)
        self.working = False


if __name__ == '__main__':
    app = QApplication([])
    window_main = MainWindow()
    app.exec_()
