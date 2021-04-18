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
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow

from helpers.chart_consistency import ConsistencyChart
from helpers.printer_reprapfirmware import DuetRRF3
from helpers.serial_encoder import SerialEncoder
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

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.current_tool = 0
        self.log_debug = False
        self.thread_printer = QThread()

        self.actn_save.triggered.connect(self.log_save)

        self.btn_encoder_connect.clicked.connect(self.encoder_connect)
        self.btn_encoder_disconnect.clicked.connect(self.encoder_disconnect)
        self.btn_encoder_refresh.clicked.connect(self.populate_serial_ports)
        self.btn_printer_connect.clicked.connect(self.printer_connect)
        self.btn_printer_disconnect.clicked.connect(self.printer_disconnect)
        self.cbx_tool.currentIndexChanged.connect(self.gui_tool_update)
        self.btn_tool_home.clicked.connect(self.printer_move_home)
        self.btn_tool_center.clicked.connect(self.printer_move_center)
        self.btn_tool_heat.clicked.connect(self.printer_set_temperature)
        self.btn_tool_run.clicked.connect(self.printer_run)
        self.btn_estop.clicked.connect(self.printer_estop)
        self.sig_chart_const_finished.connect(self.chart_const_finished)

        self.init_gui()
        self.show()
        self.log_event('Program started')

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

        self.t_count = 1
        self.chart_const = ConsistencyChart()
        self.chart_const_widget.setChart(self.chart_const.chart)
        self.chart_const_widget.setRenderHint(QPainter.Antialiasing)

        self.populate_serial_ports()

    def log_event(self, text, debug=False):
        ''' Log text to the GUI event log. '''
        if debug and not self.actn_verboselog.isChecked(): return
        self.pte_eventlog.appendPlainText('[{}] {}'.format(time.strftime('%H:%M:%S', time.localtime()), text))

    def log_save(self):
        ''' Save the contents of the event log to a file chosen by QFileDialog. '''
        log_filename, _ = QFileDialog.getSaveFileName(self, 'Save the Event Log as...', 'eventlog.txt', 'Text files (*.txt)' )
        f = open(log_filename, 'w')
        f.write(self.pte_eventlog.toPlainText())
        f.close()
        self.log_event('Log saved to {}'.format(log_filename))

    def populate_serial_ports(self):
        ''' Populate the encoder combobox with available system serial
        ports. Also called when the user hits the refresh button. '''
        self.cbx_encoder_port.clear()

        # FIXME: This fixes a bug where no serial ports are available on launch
        # but self.sig_serial_disable.emit() never fires.
        QCoreApplication.processEvents()
        self.serial_ports = QSerialPortInfo.availablePorts()
        if not self.serial_ports:
            self.log_event('[SERIAL] No serial ports detected', True)
            self.sig_serial_disable.emit()
            return
        self.sig_serial_enable.emit()
        for port in self.serial_ports:
            self.log_event('[SERIAL] Found port: {} - {}'.format(port.portName(), port.description()), True)
            self.cbx_encoder_port.addItem('{}: {}'.format(port.portName(), port.description()))

    def encoder_connect(self):
        ''' Connect to the serial encoder via the serial_encoder class. '''
        port = self.serial_ports[self.cbx_encoder_port.currentIndex()].portName()
        self.log_event('Attempting connection to encoder on {}'.format(port))
        self.encoder = SerialEncoder()
        self.encoder.sig_handshake.connect(self.encoder_handshake)
        self.encoder.sig_measurement.connect(self.encoder_measurement)
        self.sig_encoder_connect.emit()
        if not self.encoder.connect(port):
            self.log_event('Error connecting to the encoder')
            self.log_event('[SERIAL] [ERROR] {}'.format(self.encoder.err), True)
            self.encoder = None
            self.sig_encoder_disconnect.emit()

    def encoder_disconnect(self):
        ''' Disconnect from the serial encoder. '''
        self.encoder.disconnect()
        self.encoder = None
        self.log_event('Closed connection to encoder')
        self.sig_encoder_disconnect.emit()

    def encoder_handshake(self):
        ''' The encoder returned a handshake, process and update the
        GUI with the details '''
        self.sig_encoder_connect.emit()
        self.log_event('Connected to encoder')
        self.log_event('[SERIAL] Encoder Firmware: v{} - Built: {}'.format(self.encoder.firmware_version, self.encoder.firmware_date), True)
        self.lbl_encoder_fw.setText('v{} ({})'.format(self.encoder.firmware_version, self.encoder.firmware_date))

    def encoder_measurement(self, measurement):
        ''' The encoder returned a measurement, process and update
        the GUI with the details '''
        self.log_event('[SERIAL] Measurement received: {}'.format(measurement), True)
        if self.tabMain.currentIndex() == 0:
            return
        if self.tabMain.currentIndex() == 1:
            if measurement == 0 and self.chart_const.count != 1:
                ''' Assume the measurement is complete. '''
                self.encoder.stop()
                self.sig_chart_const_finished.emit()
                return
            if measurement == 0 and self.chart_const.count == 1:
                ''' Zero reading, extruder has not moved yet. '''
                return

            self.chart_const.add(measurement, self.encoder.interval)
            return
        if self.tabMain.currentIndex() == 2:
            return

    def printer_connect(self):
        ''' Connect to the specified firmware '''
        self.log_event('Attempting connection to {} at {}'.format(self.cbx_printer_fwtype.currentText(), self.txt_printer_hostname.text()))
        if self.cbx_printer_fwtype.currentIndex() == 0:            
            self.printer = DuetRRF3(self.txt_printer_hostname.text())

        self.printer.moveToThread(self.thread_printer)
        self.thread_printer.started.connect(self.printer.run)
        self.printer.sig_finished.connect(self.thread_printer.quit)
        self.printer.sig_connected.connect(self.printer_connected)
        self.printer.sig_failure.connect(self.printer_failure)
        self.printer.sig_data_update.connect(self.printer_update)
        self.printer.sig_temp_reached.connect(self.printer_temp_reached)
        self.thread_printer.start()
        self.sig_printer_connect.emit()

    def printer_connected(self):
        ''' The printer connection established sucessfully. '''
        self.sig_printer_connect.emit()
        self.log_event('Connected to printer')
        self.log_event('[RRF3-STD] Printer Firmware: v{} running on: {}'.format(self.printer.cfg_board[0]['firmware'], self.printer.cfg_board[0]['board']), True)
        self.log_event('[RRF3-STD] Found {} tool(s)'.format(len(self.printer.cfg_tools)), True)
        self.lbl_printer_fw.setText('v{} ({})'.format(self.printer.cfg_board[0]['firmware'], self.printer.cfg_board[0]['board']))
        self.cbx_tool.clear()
        for tool, data in enumerate(self.printer.cfg_tools):
            self.cbx_tool.addItem('Tool {}'.format(tool))
        self.groupbox_settings.setEnabled(True)

    def printer_failure(self):
        ''' The printer connection failed. '''
        self.printer.run_thread = False
        self.thread_printer.quit()
        self.log_event('Error connecting to printer')
        self.log_event('[RRF-STD] [ERROR] {}'.format(self.printer.err), True)
        self.printer = None
        self.sig_printer_disconnect.emit()
        self.groupbox_settings.setEnabled(False)

    def printer_update(self):
        ''' The printer has signalled that updated data is
        available. '''
        if self.printer == None:
            return
        tool_data = self.printer.cfg_tools[self.current_tool]
        self.txt_tool_curstep.setText('{}'.format(tool_data['stepsPerMm']))
        self.txt_tool_curtemp.setText('{} C'.format(tool_data['cur_temp']))
        #print(tool_data)

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
        #FIXME: Do not enable btn_tool_run if a job is running
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
        ''' Signalled when the tool combobox is altered. If we change
        tool, we must update aspects of the GUI and make sure the previous
        tool heater is disabled. '''
        print('index: {} -- current_tool: {}'.format(index, self.current_tool))
        if index != -1:
            if self.current_tool != index:
                self.printer.set_tool_temperature(0, self.current_tool)
            self.current_tool = index

    def printer_estop(self):
        ''' Trigger an immediate emergency stop and then close all
        printer connections. '''
        self.log_event('**** EMERGENCY STOP TRIGGERED ****')
        self.printer.estop()
        self.printer_disconnect()

    def printer_run(self):
        ''' Triggered when the run button is pressed. We determine the
        correct test to run based upon tabMain.currentIndex(). '''
        #FIXME: Prevent user from changing tab during processing
        if self.tabMain.currentIndex() == 0:
            return
        if self.tabMain.currentIndex() == 1:
            ''' Extruder consistency'''
            self.encoder.set_relative()
            self.encoder.start()
            self.chart_const.reset()
            self.printer.send_gcode('G1 E122 F120')
            self.btn_tool_run.setEnabled(False)
            return
        if self.tabMain.currentIndex() == 2:
            return

    def chart_const_finished(self):
        ''' Signalled when the readings for the chart have completed. We
        can now perform a report on the extruder consistency. '''
        #TODO: Show results to user and also log to the event log
        self.btn_tool_run.setEnabled(True)

if __name__ == '__main__':
    app = QApplication([])
    window_main = MainWindow()
    app.exec_()
