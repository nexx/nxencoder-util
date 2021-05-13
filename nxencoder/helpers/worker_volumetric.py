#!/usr/bin/env python

"""
nxEncoder Module
worker_volumetric.py

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
from PyQt5.QtChart import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis


class WorkerVolumetric(QObject):
    sig_encoder_measure = pyqtSignal()
    sig_encoder_reset = pyqtSignal()
    sig_printer_send_gcode = pyqtSignal(str)
    sig_log_debug = pyqtSignal(str)
    sig_log_event = pyqtSignal(str)
    sig_finished = pyqtSignal()

    under_extrusion = 0
    feedrate = 120
    feedrate_limit = 0
    feedrate_step = 60
    distance = 100

    running = True
    fine = False

    def __init__(self, parent=None):
        super(WorkerVolumetric, self).__init__(parent)
        self.xaxis = QBarCategoryAxis()
        self.xaxis.setLabelsAngle(-90)
        self.xaxis.setTitleText('Extruder Feedrate (mm/min)')
        self.xaxis.append(' ')

        self.yaxis = QValueAxis(min=0, max=4, labelFormat='%.2f')
        self.yaxis.setTitleText('Under Extrusion (%)')

        self.barset = QBarSet('Under Extrusion')
        self.barset.append(0.0)
        self.series = QBarSeries()
        self.series.append(self.barset)

        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.addAxis(self.yaxis, Qt.AlignLeft)
        self.chart.legend().setVisible(False)
        self.chart.setAxisX(self.xaxis, self.series)

        self.series.attachAxis(self.yaxis)

    def run(self):
        ''' Main thread used for running the maximum volumetric flow calculation. '''
        self.loop = QEventLoop()

        self.sig_log_event.emit('Priming the nozzle')
        self.sig_printer_send_gcode.emit('G1 E5 F600')
        QTimer.singleShot(2000, self.loop.quit)
        self.loop.exec_()
        self.sig_encoder_reset.emit()

        while self.running:
            self.sig_encoder_reset.emit()

            self.sig_log_event.emit('Running flow test at {} mm/min'.format(self.feedrate))
            self.sig_printer_send_gcode.emit('G1 E{} F{}'.format(self.distance, self.feedrate))
            delay = ((self.distance / (self.feedrate / 60)) + 2) * 1000
            QTimer.singleShot(delay, self.loop.quit)
            self.loop.exec_()

            self.sig_encoder_measure.emit()
            QTimer.singleShot(250, self.loop.quit)
            self.loop.exec_()

    def add(self, under_extrusion):
        ''' Add a data point to the chart, taking into account the existing
        points and inserting where appropriate. If data point 0 is a blank
        space, the chart is freshly cleared, so replace point 0 instead of
        appending. '''
        if (self.xaxis.at(0) == ' '):
            self.clear()
            self.xaxis.append(str(self.feedrate))
            self.barset.append(under_extrusion)
            return

        max_feedrate = int(self.xaxis.at(self.xaxis.count() - 1))
        if self.feedrate > max_feedrate:
            self.xaxis.append(str(self.feedrate))
            self.barset.append(under_extrusion)
            return

        if self.feedrate == max_feedrate:
            self.barset.replace(self.barset.count() - 1, under_extrusion)
            return

        if self.feedrate < max_feedrate:
            self.xaxis.insert(self.xaxis.count() - 1, str(self.feedrate))
            self.barset.insert(self.barset.count() - 1, under_extrusion)
            return

    def clear(self):
        ''' Remove all data from the chart. '''
        self.xaxis.clear()
        self.barset.remove(0, self.barset.count())

    def handle_measurement(self, measurement):
        ''' Retrieve the measurements from the encoder signal, run calculations,
        adjust as needed, then add them to the chart. '''
        self.under_extrusion = (100 - ((measurement / self.distance) * 100))
        if self.under_extrusion < 0.25:
            self.under_extrusion = 0.0
        self.sig_log_event.emit('The result for {} mm/min is {:.2f}% of under-extrusion'.format(self.feedrate, self.under_extrusion))
        self.add(self.under_extrusion)

        if self.under_extrusion >= 3 and not self.fine:
            ''' We've exceeded the final under_extrusion limit without starting
            fine tuning. Back off to the last data point and start the fine
            tuning process from there. '''
            self.feedrate -= 20

        if self.under_extrusion >= 2 and not self.fine:
            self.fine = True
            self.feedrate -= 30
            self.feedrate_step = 10
            self.sig_log_event.emit('We are approaching the flow limit of this tool. Now proceeding with fine tuning beginning at {} mm/min'.format(self.feedrate))
            return

        if self.under_extrusion >= 3 and self.fine:
            self.feedrate -= self.feedrate_step
            self.feedrate -= 5
            self.running = False
            self.sig_finished.emit()
            return

        self.feedrate += self.feedrate_step
