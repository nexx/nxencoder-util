#!/usr/bin/env python

"""
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
"""

from PyQt5.QtCore import Qt, QState, QStateMachine, pyqtSignal, QCoreApplication
from PyQt5.QtGui import QPainter
from PyQt5.QtSerialPort import QSerialPortInfo
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow

from helpers.chart_volumetric import VolumetricChart
from helpers.serial_encoder import SerialEncoder
from helpers.util_workers import *
from resources.ui_mainwindow import Ui_MainWindow

import time

class MainWindow(QMainWindow, Ui_MainWindow):
    sig_serial_disable = pyqtSignal()
    sig_serial_enable = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)
        self.log_debug = False

        self.actn_save.triggered.connect(self.log_save)

        self.btn_encoder_refresh.clicked.connect(self.populate_serial_ports)
        self.pushButton.clicked.connect(self.test_thread)

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

        self.state_serial_disconnected.addTransition(self.btn_encoder_connect.clicked, self.state_serial_connected)
        self.state_serial_disconnected.addTransition(self.sig_serial_disable, self.state_serial_disabled)
        self.state_serial_disabled.addTransition(self.sig_serial_enable, self.state_serial_disconnected)
        self.state_serial_connected.addTransition(self.btn_encoder_disconnect.clicked, self.state_serial_disconnected)
        self.state_serial.start()

        self.state_printer = QStateMachine()
        self.state_printer_disconnected = QState(self.state_printer)
        self.state_printer_disconnected.assignProperty(self.lbl_printer_status, 'text', 'Disconnected')
        self.state_printer_disconnected.assignProperty(self.lbl_printer_status, 'styleSheet', 'color: rgb(170, 0, 0)')
        self.state_printer_disconnected.assignProperty(self.lbl_printer_fw, 'text', 'N/A')
        self.state_printer_disconnected.assignProperty(self.txt_printer_hostname, 'enabled', True)
        self.state_printer_disconnected.assignProperty(self.btn_printer_connect, 'enabled', True)
        self.state_printer_disconnected.assignProperty(self.btn_printer_disconnect, 'enabled', False)
        
        self.state_printer_connected = QState(self.state_printer)
        self.state_printer_connected.assignProperty(self.lbl_printer_status, 'text', 'Connected')
        self.state_printer_connected.assignProperty(self.lbl_printer_status, 'styleSheet', 'color: rgb(0, 170, 0)')
        self.state_printer_connected.assignProperty(self.txt_printer_hostname, 'enabled', False)
        self.state_printer_connected.assignProperty(self.btn_printer_connect, 'enabled', False)
        self.state_printer_connected.assignProperty(self.btn_printer_disconnect, 'enabled', True)
        self.state_printer.setInitialState(self.state_printer_disconnected)

        self.state_printer_disconnected.addTransition(self.btn_printer_connect.clicked, self.state_printer_connected)
        self.state_printer_connected.addTransition(self.btn_printer_disconnect.clicked, self.state_printer_disconnected)
        self.state_printer.start()

        self.populate_serial_ports()

        self.vcal_chart = VolumetricChart()
        self.vcal_chart_widget.setChart(self.vcal_chart.chart)
        self.vcal_chart_widget.setRenderHint(QPainter.Antialiasing)

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

if __name__ == '__main__':
    app = QApplication([])
    window_main = MainWindow()
    app.exec_()
