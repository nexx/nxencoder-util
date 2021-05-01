#!/usr/bin/env python

"""
nxEncoder Module
worker_consistency.py

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

from PyQt5.QtCore import Qt, pyqtSignal, QEventLoop, QObject, QTimer
from PyQt5.QtChart import QChart, QLineSeries, QValueAxis


class WorkerConsistency(QObject):
    sig_encoder_measure = pyqtSignal()
    sig_encoder_reset = pyqtSignal()
    sig_printer_send_gcode = pyqtSignal(str)
    sig_log_debug = pyqtSignal(str)
    sig_finished = pyqtSignal()

    cal_results = []

    iteration = 0

    def __init__(self, parent=None):
        super(WorkerConsistency, self).__init__(parent)
        self.series = QLineSeries()

        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.addSeries(self.series)

        self.yaxis = QValueAxis(min=-10, max=10, labelFormat='%.2f')
        self.yaxis.setTitleText('Deviation (%)')
        self.xaxis = QValueAxis(min=1, max=20, labelFormat='%d')
        self.xaxis.setTitleText('Iteration')

        self.chart.addAxis(self.yaxis, Qt.AlignLeft)
        self.chart.legend().setVisible(False)
        self.chart.setAxisX(self.xaxis, self.series)
        self.series.attachAxis(self.yaxis)

    def run(self):
        ''' Main thread used for running the consistency check iterations. '''
        self.loop = QEventLoop()
        self.series.clear()

        self.sig_log_debug.emit('[CONSISTENCY] Purging Nozzle')
        self.sig_printer_send_gcode.emit('G1 E5 F600')
        QTimer.singleShot(2000, self.loop.quit)
        self.loop.exec_()
        self.sig_encoder_reset.emit()

        for self.iteration in range(1, 21):
            self.sig_log_debug.emit('[CONSISTENCY] Running iteration {} of 20'.format(self.iteration))
            self.sig_printer_send_gcode.emit('G1 E20 F120')
            QTimer.singleShot(10000, self.loop.quit)
            self.loop.exec_()

            self.sig_encoder_measure.emit()

            QTimer.singleShot(250, self.loop.quit)
            self.loop.exec_()

        self.sig_finished.emit()

    def reset(self):
        ''' Reset the chart to an empty state. '''
        self.series.clear()

    def handle_measurement(self, measurement):
        ''' Retrieve the measurements from the encoder signal, then
        add them to the chart. '''
        deviation = round((-1 + (measurement / 20)) * 100, 2)
        self.cal_results.append(deviation)
        self.series.append(self.iteration, float(deviation))
