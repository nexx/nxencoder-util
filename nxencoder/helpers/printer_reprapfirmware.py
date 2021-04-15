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

import json
import requests
import time

class DuetRRF3:
    def __init__(self, address):
        self.rrf_address = 'http://' + address
        self.cfg_tools = []
        self.cfg_board = []

    def connect(self):
        ''' Attempt to connect to the printer using /rr_config. This is
        quicker than polling the object model, and returns useful data at
        this stage. '''
        try:
            cfg_json = json.loads(requests.get(self.rrf_address + '/rr_config').text)
        except Exception as e:
            self.err = 'Connection to {} failed. Exception returned: {}'.format(self.rrf_address, e)
            return False

        self.cfg_board.append({
            'board': cfg_json['firmwareElectronics'],
            'firmware': cfg_json['firmwareVersion']
        })
        self.read_configuration()
        return True

    def disconnect(self):
        ''' Clean up prior to clearing the class '''
        return

    def read_configuration(self):
        ''' Read the object model, creating a list of active tools,
        along with their associated extruders and heaters. '''
        self.cfg_tools.clear()
        for tool in self.get_objectmodel('tools'):
            self.cfg_tools.append({
                'extruder': tool['extruders'][0],
                'heater': tool['heaters'][0],
                'stepsPerMm': self.get_objectmodel('move.extruders[{}].stepsPerMm'.format(tool['extruders'][0])),
                'cur_temp': 0
            })

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
        r = requests.get(self.rrf_address + '/rr_gcode?', {'gcode': gcode})
        if not r.status_code == 200:
            r.raise_for_status()
    
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
        self.send_gcode('M109 S{} T{}'.format(temp, tool))
        while self.cfg_tools[tool]['cur_temp'] < temp:
            time.sleep(1)

    def set_tool_esteps(self, esteps, tool=0):
        ''' Change the esteps of the extruder configured to the specified 
        tool. Internally update our configuration with the new value as well. '''
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
        ''' Reads /rr_status?type=1 waiting for the printer to report
        that it is idle. Used to wait between extrusions. '''
        status = ''
        while status != 'I':
            r = requests.get(self.rrf_address + '/rr_status?', {'type': 1})
            status = json.loads(r.text)['status']
            time.sleep(1)
