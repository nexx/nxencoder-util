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
    sig_log_event = pyqtSignal(str)
    sig_log_debug = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_force_close = pyqtSignal()

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
        self.encoder.errorOccurred.connect(self.error)

        if not self.encoder.isOpen():
            self.sig_error.emit('Connection to {} failed.'.format(portName))
            self.sig_force_close.emit()

    def receive(self):
        ''' Handle incoming data. '''
        while self.encoder.canReadLine():
            raw_data = self.encoder.readLine()
            data = raw_data.data().decode().rstrip('\r\n')
            try:
                float(data)
                self.sig_measurement.emit(float(data))
            except ValueError:
                if data[:3] == 'NXE':
                    _, self.firmware_version, self.firmware_date, self.calibration = data.strip().split('|')
                    self.sig_handshake.emit()
                    return
                self.sig_log_event.emit('Warning: Invalid data received from encoder. Raw: {}'.format(raw_data))

    def disconnect(self):
        ''' Disconnect from the serial port. '''
        self.encoder.close()

    def error(self, error):
        ''' QSerialPort signalled an error. Report to the event log and
        then signal the GUI to close the connection. '''
        if error == QSerialPort.NoError:
            return
        self.sig_error.emit('The encoder connection reported an error and has been closed.')
        self.sig_log_debug.emit('[SERIAL] Error: QSerialPort reported error code: {}'.format(error))
        self.sig_force_close.emit()

    def measure(self):
        ''' Make the arduino report a measurement now. '''
        self.encoder.write('MEASURE\n'.encode())

    def reset(self):
        ''' Resets any acumulated value the arduino is tracking. '''
        self.encoder.write('RESET\n'.encode())
