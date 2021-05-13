#!/usr/bin/env python

'''
nxEncoder Module
printer_marlin.py

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

from PyQt5.QtCore import pyqtSignal, QEventLoop, QObject, QTimer, QCoreApplication
from PyQt5.QtSerialPort import QSerialPort


class Marlin(QObject):
    sig_connected = pyqtSignal()
    sig_data_update = pyqtSignal()
    sig_temp_reached = pyqtSignal(int)
    sig_log_event = pyqtSignal(str)
    sig_log_debug = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_force_close = pyqtSignal()

    def __init__(self, port, baudrate=115200, parent=None):
        super(Marlin, self).__init__(parent)
        self.portname = port
        self.baudrate = baudrate
        self.connected = False
        self.idle = False
        self.homed = False
        self.cfg_tools = []
        self.serial_log = False
        self.serial_buffer = []
        self.connect()

    def connect(self):
        ''' Connect to Marlin via the specified serial port, check
        the connection is open, and then return. Handling of the incoming
        data is handled via Qt signals. '''
        self.printer = QSerialPort()
        self.printer.setPortName(self.portname)
        self.printer.setBaudRate(self.baudrate)
        self.printer.setDataBits(QSerialPort.Data8)
        self.printer.setParity(QSerialPort.NoParity)
        self.printer.setStopBits(QSerialPort.OneStop)
        self.printer.setFlowControl(QSerialPort.NoFlowControl)
        self.printer.open(QSerialPort.ReadWrite)
        self.printer.readyRead.connect(self.receive)
        # self.printer.errorOccurred.connect(self.error)

        if not self.printer.isOpen():
            self.sig_error.emit('Connection to {} failed.'.format(self.portname))
            self.sig_force_close.emit()

    def receive(self):
        ''' Handle incoming data. '''
        while self.printer.canReadLine():
            raw_data = self.printer.readLine()
            data = raw_data.data().decode().rstrip('\r\n')

            if data[:3] == ' T:':
                for i in range(len(self.cfg_tools)):
                    tool = 'T{}'.format(i)
                    start = data.find(tool) + len(tool) + 1
                    end = data.find(' ', start)
                    self.cfg_tools[i]['cur_temp'] = float(data[start:end])

                    start = data.find('/', end) + 1
                    end = data.find(' ', start)
                    set_temp = float(data[start:end])
                    if set_temp > 0 and self.cfg_tools[i]['cur_temp'] >= set_temp:
                        self.sig_temp_reached.emit(i)
                self.sig_data_update.emit()

            if self.serial_log:
                self.serial_buffer.append(data)

            if data[:8] == 'Marlin 2':
                version = data[7:]
                self.sig_log_event.emit('Connected to Marlin v{} on {}'.format(version, self.portname))
                self.sig_log_debug.emit('[MARLIN] Printer Firmware: v{}'.format(version))
                self.fw_string = 'Marlin v{}'.format(version)

                # Send T0 to make sure Marlin is fully ready
                self.query_printer('T0')
                self.cfg_tools.clear()

                for i in range(0,10):
                    self.query_printer('T{}'.format(i))
                    if 'Invalid extruder' in self.serial_buffer[0]:
                        break

                    self.query_printer('M92 T{}'.format(i))
                    if len(self.serial_buffer) == 1:
                        stepsPerMm = float(self.serial_buffer[0][self.serial_buffer[0].find('E') + 1:])
                    else:
                        stepsPerMm = float(self.serial_buffer[1][self.serial_buffer[1].find('E') + 1:])

                    self.cfg_tools.append({
                        'stepsPerMm': stepsPerMm,
                        'cur_temp': 0,
                        'max_temp': 260
                    })

                self.connected = True
                self.sig_connected.emit()
                self.sig_log_event.emit('Switching to relative extrusion mode.')
                self.send_gcode('M83')
                self.send_gcode('M155 S2')

    def move_homeaxes(self):
        ''' Home all axes on the printer. '''
        self.send_gcode('G28')

    def move_to_safe(self, tool=0):
        ''' Move the selected tool a safe location. Marlin does not
        allow the retreval of the work area at runtime, so just move Z
        up from the home position. '''
        self.send_gcode('T{}'.format(tool))
        self.send_gcode('G28')
        self.send_gcode('G1 Z50 F1200')

    def set_tool_temperature(self, temp, tool=0):
        ''' Begins heating the specified tool on the printer. '''
        self.send_gcode('M104 S{} T{}'.format(temp, tool))

    def send_gcode(self, gcode):
        ''' Transmit gcode to the printer via the QSerialPort interface. '''
        self.printer.write('{}\n'.format(gcode).encode())
        self.printer.waitForBytesWritten(-1)

    def query_printer(self, gcode):
        ''' Transmit gcode to the printer via the QSerialPort interface,
        wait for replies to come in and return them. '''
        loop = QEventLoop()
        self.serial_buffer.clear()
        self.serial_log = True
        self.send_gcode(gcode)

        while len(self.serial_buffer) == 0 or self.serial_buffer[len(self.serial_buffer) - 1][:2] != 'ok':
            QTimer.singleShot(100, loop.quit)
            loop.exec_()
        self.serial_log = False
        self.serial_buffer.pop()

    def set_tool_esteps(self, esteps, tool=0):
        ''' Change the esteps of the extruder configured to the
        specified tool. Internally update our configuration with
        the new value as well. '''
        self.cfg_tools[tool]['stepsPerMm'] = float(esteps)
        self.send_gcode('M92 T{} E{}'.format(tool, esteps))
        self.send_gcode('M500')
