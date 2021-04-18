#!/usr/bin/env python

"""
nxEncoder Module
chart_consistency.py

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

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
import sys

class ConsistencyChart:
    def __init__(self):
        self.series = QLineSeries()

        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.addSeries(self.series)

        self.yaxis = QValueAxis(min=-5, max=5, labelFormat='%.2f')
        self.yaxis.setTitleText('Deviation (%)')
        self.xaxis = QValueAxis(min=1, max=60, tickCount=2, labelFormat='%.2f')
        self.xaxis.setTitleText('Time (s)')

        self.chart.addAxis(self.yaxis, Qt.AlignLeft)
        self.chart.legend().setVisible(False)
        self.chart.setAxisX(self.xaxis, self.series)
        self.series.attachAxis(self.yaxis)

        self.count = 1

    def add(self, value, interval):
        ''' Add a data point to the chart, updating the max of the
        x-axis each time '''
        elapsed = (interval * self.count) / 1000
        deviation = (-1 + value) * 100
        self.series.append(float(elapsed), float(deviation))
        self.count += 1
    
    def dump(self):
        ''' Dump the data points to the console. '''
        t = {}
        for i in range(0, self.xaxis.count()):
            t[self.xaxis.at(i)] = self.barset.at(i)
        print(t)

    def reset(self):
        ''' Reset the chart to an empty state. '''
        self.series.clear()
        # self.xaxis.setMin(1)
        # self.xaxis.setMax(30)
        self.count = 1
