#!/usr/bin/env python

'''
nxEncoder Module
printer_reprapfirmware.py

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

from PyQt5.QtCore import pyqtSignal, QEventLoop, QObject, QTimer

import json
import requests
import socket


class DuetRRF3(QObject):
    sig_connected = pyqtSignal()
    sig_failure = pyqtSignal()
    sig_data_update = pyqtSignal()
    sig_temp_reached = pyqtSignal(int)
    sig_finished = pyqtSignal()

    def __init__(self, host, parent=None):
        super(DuetRRF3, self).__init__(parent)
        self.rrf_host = host
        self.idle = False
        self.homed = False
        self.cfg_tools = []
        self.cfg_board = []
        self.run_thread = False

    def run(self):
        ''' Main thread used for connection, thruough to retrieving
        the status of the printer. Prior to entering the loop, connect,
        and retrieve the configuration. This way we don't block the
        GUI thread. Lastly, we resolve the provided hostname to an IP
        address so that each use of requests does not trigger a delay
        due to DNS lookups. '''
        self.loop = QEventLoop()

        try:
            self.rrf_address = 'http://' + socket.gethostbyname(self.rrf_host)

            cfg_json = json.loads(requests.get(self.rrf_address + '/rr_config').text)
            self.cfg_board.append({
                'board': cfg_json['firmwareElectronics'],
                'firmware': cfg_json['firmwareVersion']
            })

            self.cfg_tools.clear()
            for tool in self.get_objectmodel('tools'):
                self.cfg_tools.append({
                    'extruder': tool['extruders'][0],
                    'heater': tool['heaters'][0],
                    'stepsPerMm': self.get_objectmodel('move.extruders[{}].stepsPerMm'.format(tool['extruders'][0])),
                    'cur_temp': 0
                })
        except Exception as e:
            self.err = 'Connection to {} failed. Exception returned: {}'.format(self.rrf_host, e)
            self.sig_failure.emit()
            return

        self.sig_connected.emit()
        self.run_thread = True

        ''' The main status update pulls from /rr_status as this returns
        faster, and causes less load on RRF, than querying the object
        model. '''
        while self.run_thread:
            status_json = json.loads(requests.get(self.rrf_address + '/rr_status').text)

            ''' If the sum of the homed json equals the len, all axes are
            reporting 1 as their status, meaning they are homed. '''
            self.homed = True if sum(status_json['homed']) == len(status_json['homed']) else False
            self.idle = True if status_json['status'] == 'I' else False

            for tool, data in enumerate(self.cfg_tools):
                self.cfg_tools[tool]['cur_temp'] = status_json['heaters'][data['heater']]
                if status_json['active'][data['heater']] != 0 and status_json['heaters'][data['heater']] >= status_json['active'][data['heater']]:
                    self.sig_temp_reached.emit(tool)
            self.sig_data_update.emit()
            QTimer.singleShot(1000, self.loop.quit)
            self.loop.exec_()

        self.sig_finished.emit()

    def disconnect(self):
        ''' Clean up prior to clearing the class '''
        self.run_thread = False
        for tool, _ in enumerate(self.cfg_tools):
            self.set_tool_temperature(0, tool)
        return

    def estop(self):
        ''' Emergency stop. '''
        self.send_gcode('M112')
        self.run_thread = False

    def move_homeaxes(self):
        ''' Home all axes on the printer. '''
        self.send_gcode('G28')

    def move_tomiddle(self, tool=0):
        ''' Move the selected tool to the center of the bed. '''
        axes = self.get_objectmodel('move.axes')
        x_mid = (axes[0]['min'] + axes[0]['max']) / 2
        y_mid = (axes[1]['min'] + axes[1]['max']) / 2
        self.send_gcode('T{}'.format(tool))
        self.send_gcode('G1 X{} Y{} F6000'.format(x_mid, y_mid))
        self.send_gcode('G1 Z50 F1200')

    def send_gcode(self, gcode):
        ''' Transmit gcode to the printer via the HTTP interface. '''
        requests.get(self.rrf_address + '/rr_gcode?', {'gcode': gcode})

    def get_objectmodel(self, key=''):
        ''' Read the object model, returning a json object containing
        the resulting data. '''
        r = requests.get(self.rrf_address + '/rr_model?key=' + key)
        if not r.status_code == 200:
            r.raise_for_status()
        else:
            return json.loads(r.text)['result']

    def set_tool_temperature(self, temp, tool=0):
        ''' Begins heating the specified tool on the printer. '''
        self.send_gcode('M104 S{} T{}'.format(temp, tool))

    def set_tool_esteps(self, esteps, tool=0):
        ''' Change the esteps of the extruder configured to the
        specified tool. Internally update our configuration with
        the new value as well. '''
        self.cfg_tools[tool]['stepsPerMm'] = float(esteps)
        gcode = 'M92 E'
        esteps_list = []
        for tool, data in enumerate(self.cfg_tools):
            esteps_list.insert(data['extruder'], self.cfg_tools[tool]['stepsPerMm'])
        for ext in esteps_list:
            gcode = gcode + str(ext) + ":"
        gcode = gcode[0:-1]
        self.send_gcode(gcode)

    def wait_for_idle(self):
        ''' Waits for self.idle to be true, processing the event loop
        whilst doing so. This is mainly used to wait between
        extrusions. '''
        while not self.idle:
            self.loop.exec_()
