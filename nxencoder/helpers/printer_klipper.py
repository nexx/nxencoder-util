#!/usr/bin/env python

'''
nxEncoder Module
printer_klipper.py

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


class Klipper(QObject):
    sig_connected = pyqtSignal()
    sig_data_update = pyqtSignal()
    sig_temp_reached = pyqtSignal(int)
    sig_finished = pyqtSignal()
    sig_log_event = pyqtSignal(str)
    sig_log_debug = pyqtSignal(str)
    sig_error = pyqtSignal(str)
    sig_force_close = pyqtSignal()

    def __init__(self, host, parent=None):
        super(Klipper, self).__init__(parent)
        self.host = host
        self.idle = False
        self.homed = False
        self.cfg_tools = []
        self.cfg_board = []
        self.run_thread = False
        self.isKlipper = True

    def run(self):
        ''' Main thread used for connection, thruough to retrieving
        the status of the printer. Prior to entering the loop, connect,
        and retrieve the configuration. This way we don't block the
        GUI thread. Lastly, we resolve the provided hostname to an IP
        address so that each use of requests does not trigger a delay
        due to DNS lookups. '''
        self.loop = QEventLoop()

        try:
            self.address = 'http://' + socket.gethostbyname(self.host)

            cfg_json = json.loads(requests.get(self.address + '/printer/info').text)['result']
            self.cfg_board.append({
                'firmware': cfg_json['software_version']
            })

            self.cfg_tools.clear()
            cfg_json = self.get_objectmodel('configfile')['settings']

            for i in range((sum(1 for x in cfg_json if x.startswith('extruder')))):
                if i == 0:
                    tool = 'extruder'
                if i != 0:
                    tool = 'extruder{}'.format(i)

                self.cfg_tools.append({
                    'name': tool,
                    'rotation_distance': float(cfg_json[tool]['rotation_distance']),
                    'full_steps_per_rotation': int(cfg_json[tool]['full_steps_per_rotation']),
                    'microsteps': int(cfg_json[tool]['microsteps']),
                    'stepsPerMm': round((int(cfg_json[tool]['full_steps_per_rotation']) * int(cfg_json[tool]['microsteps'])) / float(cfg_json[tool]['rotation_distance']), 6),
                    'cur_temp': 0,
                    'max_temp': int(cfg_json[tool]['max_temp'])
                })
        except Exception as e:
            self.sig_error.emit('Connection to {} failed.'.format(self.host))
            self.sig_log_debug.emit('[KLIPPER] Error: Connection to {} failed. Exception returned: {}'.format(self.host, e))
            self.sig_force_close.emit()
            return

        self.sig_log_event.emit('Connected to Klipper at {}'.format(self.host))
        self.sig_log_debug.emit('[KLIPPER] Printer Firmware: {}'.format(self.cfg_board[0]['firmware']))
        self.sig_log_debug.emit('[KLIPPER] Found {} tool(s)'.format(len(self.cfg_tools)))
        self.fw_string = 'Klipper {}'.format(self.cfg_board[0]['firmware'])
        self.sig_log_event.emit('Switching to relative extrusion mode.')
        self.send_gcode('M83')

        self.sig_connected.emit()
        self.run_thread = True

        ''' The main status update pulls from /rr_status as this returns
        faster, and causes less load on RRF, than querying the object
        model. '''
        while self.run_thread:

            self.homed = True if len(self.get_objectmodel('toolhead')['homed_axes']) >= 3 else False
            self.idle = True if self.get_objectmodel('print_stats')['state'] == 'standby' else False

            for tool, data in enumerate(self.cfg_tools):
                extruder = self.get_objectmodel(self.cfg_tools[tool]['name'])
                self.cfg_tools[tool]['cur_temp'] = round(extruder['temperature'], 2)
                if extruder['target'] != 0 and extruder['temperature'] >= extruder['target']:
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
        requests.post(self.address + '/printer/emergency_stop')
        self.run_thread = False

    def move_homeaxes(self):
        ''' Home all axes on the printer. '''
        self.send_gcode('G28')

    def move_tomiddle(self, tool=0):
        ''' Move the selected tool to the center of the bed. '''
        self.send_gcode('T{}'.format(tool))
        cfg_json = self.get_objectmodel('toolhead')
        x_mid = (cfg_json['axis_minimum'][0] + cfg_json['axis_maximum'][0]) / 2
        y_mid = (cfg_json['axis_minimum'][1] + cfg_json['axis_maximum'][1]) / 2
        self.send_gcode('G1 X{} Y{} F6000'.format(x_mid, y_mid))
        self.send_gcode('G1 Z50 F1200')

    def send_gcode(self, gcode):
        ''' Transmit gcode to the printer via the HTTP interface. '''
        requests.get(self.address + '/printer/gcode/script?', {'script': gcode})

    def get_tool_stepdistance(self, tool):
        ''' Query Klipper directly for the current tool step distance. '''
        requests.get(self.address + '/printer/gcode/script?', {'script': 'SET_EXTRUDER_STEP_DISTANCE EXTRUDER={}'.format(tool)})
        r = requests.get(self.address + '/server/gcode_store?count=1')
        __, *__, step_distance = json.loads(r.text)['result']['gcode_store'][0]['message'].split()
        try:
            step_distance = float(step_distance)
            return step_distance
        except ValueError:
            return False

    def get_objectmodel(self, key=''):
        ''' Read the object model, returning a json object containing
        the resulting data. '''
        r = requests.get(self.address + '/printer/objects/query?' + key)
        return json.loads(r.text)['result']['status'][key]

    def set_tool_temperature(self, temp, tool=0):
        ''' Begins heating the specified tool on the printer. '''
        self.send_gcode('M104 S{} T{}'.format(temp, tool))

    def set_tool_esteps(self, esteps, tool=0):
        ''' Klipper does not configure the extruder by esteps. Changing the
        extruder distance value at runtime requires jumping through some hoops,
        but we maintain this function name regardless to keep the other code clean. '''
        step_distance = round(1 / esteps, 6)
        self.cfg_tools[tool]['stepsPerMm'] = esteps
        self.cfg_tools[tool]['rotation_distance'] = round((self.cfg_tools[tool]['full_steps_per_rotation'] * self.cfg_tools[tool]['microsteps']) / esteps, 6)
        self.sig_log_debug.emit('[KLIPPER] Setting step distance of {} to {}'.format(self.cfg_tools[tool]['name'], step_distance))
        self.send_gcode('SET_EXTRUDER_STEP_DISTANCE EXTRUDER={} DISTANCE={}'.format(self.cfg_tools[tool]['name'], step_distance))
