#!/usr/bin/env python

"""
nxEncoder GUI

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

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow

import os

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        root = os.path.dirname(os.path.realpath(__file__))
        uic.loadUi(os.path.join(root, 'resources/ui_mainwindow.ui'), self)

        self.show()

if __name__ == '__main__':
    app = QApplication([])
    window_main = MainWindow()
    app.exec_()
