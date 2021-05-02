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
    sig_finished = pyqtSignal()

    cal_results = []

    under_extrusion = 0
    feedrate = 240
    feedrate_limit = 0
    feedrate_step = 60

    def __init__(self, parent=None):
        super(WorkerVolumetric, self).__init__(parent)
        self.xaxis = QBarCategoryAxis()
        self.xaxis.setLabelsAngle(-90)
        self.xaxis.setTitleText('Extruder Feedrate (mm/min)')
        self.xaxis.append(' ')

        self.yaxis = QValueAxis(min=0, max=5, labelFormat='%.2f')
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

        self.sig_log_debug.emit('[VOLUMETRIC] Priming Nozzle')
        self.sig_printer_send_gcode.emit('G1 E5 F600')
        QTimer.singleShot(2000, self.loop.quit)
        self.loop.exec_()
        self.sig_encoder_reset.emit()

        ''' Coarse calculation loop. '''
        while self.under_extrusion < 3:
            self.feedrate += self.feedrate_step
            self.sig_encoder_reset.emit()

            self.sig_printer_send_gcode.emit('G1 E60 F{}'.format(self.feedrate))
            delay = ((60 / (self.feedrate / 60)) * 1000) + 500
            QTimer.singleShot(delay, self.loop.quit)
            self.loop.exec_()

            self.sig_encoder_measure.emit()
            QTimer.singleShot(250, self.loop.quit)
            self.loop.exec_()

        ''' Adjust settings for fine calibration loop. '''
        self.under_extrusion = 0
        self.feedrate_limit = self.feedrate
        self.feedrate -= (self.feedrate_step - 5)
        self.feedrate_step = 5

        ''' Fine calibration loop. '''
        while self.under_extrusion < 1.5:
            self.feedrate += self.feedrate_step
            self.sig_encoder_reset.emit()

            self.sig_printer_send_gcode.emit('G1 E60 F{}'.format(self.feedrate))
            delay = ((60 / (self.feedrate / 60)) * 1000) + 500
            QTimer.singleShot(delay, self.loop.quit)
            self.loop.exec_()

            self.sig_encoder_measure.emit()
            QTimer.singleShot(250, self.loop.quit)
            self.loop.exec_()

        ''' Calculate final results. '''
        self.feedrate -= 5
        # FIXME: Calculate this using the filament diameter and nozzle size in the GUI
        self.max_volumetric = round(((self.feedrate / 60) * 2.405) - 0.5, 2)

        self.sig_finished.emit()

    def add(self, under_extrusion):
        ''' Add a data point to the chart, taking into account the
        existing points and inserting where appropriate. If data
        point 0 is 0, the chart is freshly cleared, so replace point
        0 instead of appending. '''
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

        if self.feedrate < max_feedrate:
            self.xaxis.insert(self.xaxis.count() - 1, str(self.feedrate))
            self.barset.insert(self.barset.count() - 1, under_extrusion)
            return

    def clear(self):
        ''' Remove all data from the chart. '''
        self.xaxis.clear()
        self.barset.remove(0, self.barset.count())

    def handle_measurement(self, measurement):
        ''' Retrieve the measurements from the encoder signal, then
        add them to the chart. '''
        self.under_extrusion = round(100 - ((measurement / 60) * 100), 1)
        self.sig_log_debug.emit('[VOLUMETRIC] Underextrusion of {}% at {} mm/s'.format(self.under_extrusion, round(self.feedrate / 60, 2)))
        self.add(self.under_extrusion)
