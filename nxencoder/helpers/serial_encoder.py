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

from PyQt5.QtCore import QThread, pyqtSlot, pyqtSignal, QCoreApplication
from PyQt5.QtSerialPort import QSerialPort
from time import sleep

class SerialEncoder:
    def __init__(self):
        self.line_buffer = []
        self.running_measurement = False

    def connect(self, portName):
        ''' Connect to the encoder via the specified serial port. We
        wait for 2 seconds after opening as the arduino resets when the
        serial connection is established. A faster alternative would
        be to utilize dsrdtr but this seems to cause further issues with
        reading and writing '''
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

        sleep(2)
        self.send('INFO')
        while len(self.line_buffer) == 0:
            QCoreApplication.processEvents()

        handshake = self.read_line_from_buffer()
        if handshake[:3] == 'NXE':
            _, self.firmware_version, self.firmware_date, self.interval, self.calibration = handshake.strip().split('|')
            self.interval = int(self.interval)
        return True

    def receive(self):
        ''' Handle incoming data, add it to the line_buffer list '''
        while self.encoder.canReadLine():
            raw_data = self.encoder.readLine()
            data = raw_data.data().decode().rstrip('\r\n')
            self.line_buffer.append(data)

    def send(self, data):
        ''' Send a command to the arduino '''
        if not '\n' in data:
           data = data + '\n'
        self.encoder.write(data.encode())

    def read_line_from_buffer(self):
        ''' Read and return a single line from the buffer '''
        if len(self.line_buffer) > 0:
            return self.line_buffer.pop(0)

    def disconnect(self):
        ''' Disconnect from the serial port '''
        self.encoder.close()

    def flush_buffer(self):
        ''' Clear the line_buffer list '''
        self.line_buffer.clear()

    def get_measurement(self):
        ''' Request a single measurement from the arduino '''
        self.flush_buffer()
        self.encoder.write('MEASURE\n'.encode())
        while len(self.line_buffer) == 0:
            QCoreApplication.processEvents()
        return self.read_line_from_buffer()

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
        self.running_measurement = True
        self.encoder.write('START\n'.encode())

    def stop(self):
        ''' Stops the arduino reporting '''
        self.running_measurement = False
        self.encoder.write('STOP\n'.encode())

    def reset(self):
        ''' Resets any acumulated value the arduino is tracking. '''
        self.encoder.write('RESET\n'.encode())
