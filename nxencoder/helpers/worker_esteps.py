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
    sig_printer_send_gcode = pyqtSignal(str)
    sig_log_debug = pyqtSignal(str)
    sig_result_ready = pyqtSignal()
    sig_finished = pyqtSignal()

    distance_coarse = 20
    distance_fine = 50
    feedrate_coarse = 120
    feedrate_fine = 120
    delay_coarse = ((distance_coarse / (feedrate_coarse / 60)) + 2) * 1000
    delay_fine = ((distance_fine / (feedrate_fine / 60)) + 2) * 1000

    cal_results = []

    iteration = 0

    def __init__(self, parent=None):
        super(WorkerEsteps, self).__init__(parent)

    def run(self):
        ''' Main thread used for running the eSteps calibration
        iterations. '''
        self.loop = QEventLoop()
        self.cal_results.clear()
        for self.iteration in range(0, 20):
            if self.iteration <= 9:
                self.sig_log_debug.emit('[ESTEPS] Running iteration {} (coarse)'.format(self.iteration + 1))
                self.sig_printer_send_gcode.emit('G1 E{} F{}'.format(self.distance_coarse, self.feedrate_coarse))
                QTimer.singleShot(self.delay_coarse, self.loop.quit)

            if self.iteration >= 10:
                self.sig_log_debug.emit('[ESTEPS] Running iteration {} (fine)'.format(self.iteration + 1))
                self.sig_printer_send_gcode.emit('G1 E{} F{}'.format(self.distance_fine, self.feedrate_fine))
                QTimer.singleShot(self.delay_fine, self.loop.quit)

            self.loop.exec_()

            self.sig_encoder_measure.emit()

            QTimer.singleShot(500, self.loop.quit)
            self.loop.exec_()

        self.sig_finished.emit()

    def handle_measurement(self, measurement):
        ''' Retrieve the measurements from the encoder signal, then
        add them to the results list. '''
        self.cal_results.append(measurement)
        self.sig_result_ready.emit()
