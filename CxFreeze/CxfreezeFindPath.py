# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2017 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Script to find the cxfreeze directory from running Python interpreter.
"""

import os
import sys

for sysPath in sys.path:
    modpath = os.path.join(sysPath, "cx_Freeze")
    if os.path.exists(modpath):
        print(modpath)
        break
