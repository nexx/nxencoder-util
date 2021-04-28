#!/usr/bin/env python

"""
nxEncoder Module
worker_esteps.py

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

from PyQt5.QtCore import pyqtSignal, QEventLoop, QObject, QTimer


class WorkerEsteps(QObject):
    sig_encoder_measure = pyqtSignal()
    sig_encoder_reset = pyqtSignal()
    sig_printer_send_gcode = pyqtSignal(str)
    sig_event_log = pyqtSignal(str, bool)
    sig_result_ready = pyqtSignal()

    cal_results = []

    iteration = 0

    def __init__(self, parent=None):
        super(WorkerEsteps, self).__init__(parent)

    def run(self):
        ''' Main thread used for running the eSteps calibration
        iterations. '''
        self.loop = QEventLoop()
        self.cal_results.clear()

        for self.iteration in range(0, 16):
            self.sig_encoder_reset.emit()
            if self.iteration <= 7:
                self.sig_event_log.emit('[ESTEPS] Running iteration {} (coarse)'.format(self.iteration + 1), True)
                self.sig_printer_send_gcode.emit('G1 E20 F240')
                QTimer.singleShot(7500, self.loop.quit)

            if self.iteration >= 8:
                self.sig_event_log.emit('[ESTEPS] Running iteration {} (fine)'.format(self.iteration + 1), True)
                self.sig_printer_send_gcode.emit('G1 E50 F120')
                QTimer.singleShot(30000, self.loop.quit)

            self.loop.exec_()

            self.sig_encoder_measure.emit()

            QTimer.singleShot(500, self.loop.quit)
            self.loop.exec_()

    def handle_measurement(self, measurement):
        ''' Retrieve the measurements from the encoder signal, then
        add them to the results list. '''
        self.cal_results.append(measurement)
        self.sig_result_ready.emit()
