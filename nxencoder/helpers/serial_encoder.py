#!/usr/bin/env python

'''
nxEncoder Module
serial_encoder.py

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

from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtSerialPort import QSerialPort

class SerialEncoder(QObject):
    sig_measurement = pyqtSignal(float)
    sig_handshake = pyqtSignal()

    def __init__(self, parent=None):
        super(SerialEncoder, self).__init__(parent)

    def connect(self, portName):
        ''' Connect to the encoder via the specified serial port, check
        the connection is open, and then return. Handling of the incoming
        data is handled via Qt signals. '''
        self.encoder = QSerialPort()
        self.encoder.setPortName(portName)
        self.encoder.setBaudRate(QSerialPort.Baud9600)
        self.encoder.setDataBits(QSerialPort.Data8)
        self.encoder.setParity(QSerialPort.NoParity)
        self.encoder.setStopBits(QSerialPort.OneStop)
        self.encoder.setFlowControl(QSerialPort.NoFlowControl)
        self.encoder.open(QSerialPort.ReadWrite)
        self.encoder.readyRead.connect(self.receive)

        if not self.encoder.isOpen():
            self.err = 'Connection to {} failed.'.format(portName)
            return False
        return True

    def receive(self):
        ''' Handle incoming data '''
        while self.encoder.canReadLine():
            raw_data = self.encoder.readLine()
            data = raw_data.data().decode().rstrip('\r\n')
            try:
                float(data)
                self.sig_measurement.emit(float(data))
            except ValueError:
                if data[:3] == 'NXE':
                    _, self.firmware_version, self.firmware_date, self.interval, self.calibration = data.strip().split('|')
                    self.interval = int(self.interval)
                    self.sig_handshake.emit()
                assert('Invalid data received from encoder. Raw: {}'.format(raw_data))

    def disconnect(self):
        ''' Disconnect from the serial port '''
        self.encoder.stop()
        self.encoder.close()

    def measure(self):
        ''' Make the arduino report a measurement now. '''
        self.encoder.write('MEASURE\n'.encode())

    def set_absolute(self):
        ''' Make the arduino report absolute measurements '''
        self.encoder.write('ABS\n'.encode())

    def set_relative(self):
        ''' Make the arduino report relative measurements '''
        self.encoder.write('REL\n'.encode())

    def set_interval(self, interval):
        ''' Adjust the reporting interval from the arduino '''
        self.interval = int(interval)
        self.encoder.write('INTERVAL {}\n'.format(interval).encode())

    def start(self):
        ''' Starts continuous reporting from the arduino '''
        self.encoder.write('START\n'.encode())

    def stop(self):
        ''' Stops the arduino reporting '''
        self.encoder.write('STOP\n'.encode())

    def reset(self):
        ''' Resets any acumulated value the arduino is tracking. '''
        self.encoder.write('RESET\n'.encode())
