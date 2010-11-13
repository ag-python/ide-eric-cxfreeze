# -*- coding: utf-8 -*-

# Copyright (c) 2010 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the CxFreeze plugin.
"""

import os
import sys

from PyQt4.QtCore import QObject, SIGNAL, QTranslator, QCoreApplication
from PyQt4.QtGui import QDialog, QMessageBox

from E5Gui.E5Action import E5Action
from E5Gui.E5Application import e5App

from CxFreeze.CxfreezeConfigDialog import CxfreezeConfigDialog
from CxFreeze.CxfreezeExecDialog import CxfreezeExecDialog

import Utilities

# Start-of-Header
name = "CxFreeze Plugin"
author = "Detlev Offenbach <detlev@die-offenbachs.de>"
autoactivate = True
deactivateable = True
version = "5.0.0"
className = "CxFreezePlugin"
packageName = "CxFreeze"
shortDescription = "Show the CxFreeze dialogs."
longDescription = """This plugin implements the CxFreeze dialogs.""" \
 """ CxFreeze is used to generate a distribution package."""
needsRestart = False
pyqtApi = 2
# End-of-Header

error = ""

def exeDisplayData():
    """
    Public method to support the display of some executable info.
    
    @return dictionary containing the data to query the presence of
        the executable
    """
    data = {
        "programEntry"      : True, 
        "header"            : QCoreApplication.translate("CxFreezePlugin",
                                "Packagers - cx_freeze"), 
        "exe"               : 'dummyfreeze', 
        "versionCommand"    : '--version', 
        "versionStartsWith" : 'dummyfreeze', 
        "versionPosition"   : -1, 
        "version"           : "", 
        "versionCleanup"    : None, 
    }
    
    exe = _findExecutable()
    if exe:
        data["exe"] = exe
        if exe.startswith("FreezePython"):
            data["versionStartsWith"] = "FreezePython"
        elif exe.startswith("cxfreeze"):
            data["versionStartsWith"] = "cxfreeze"
    
    return data

def _findExecutable():
    """
    Restricted function to determine the name of the executable.
    
    @return name of the executable (string)
    """
    # step 1: check for version 4.x
    exe = 'cxfreeze'
    if sys.platform == "win32":
        exe += '.bat'
    if Utilities.isinpath(exe):
        return exe
    
    return None

def _checkProgram():
    """
    Restricted function to check the availability of cxfreeze.
    
    @return flag indicating availability (boolean)
    """
    global error
    
    if _findExecutable() is None:
        error = QCoreApplication.translate("CxFreezePlugin",
            "The cxfreeze executable could not be found.")
        return False
    else:
        return True
_checkProgram()

class CxFreezePlugin(QObject):
    """
    Class implementing the CxFreeze plugin.
    """
    def __init__(self, ui):
        """
        Constructor
        
        @param ui reference to the user interface object (UI.UserInterface)
        """
        QObject.__init__(self, ui)
        self.__ui = ui
        self.__initialize()
        _checkProgram()
        
        self.__translator = None
        self.__loadTranslator()
        
    def __initialize(self):
        """
        Private slot to (re)initialize the plugin.
        """
        self.__projectAct = None
        
    def activate(self):
        """
        Public method to activate this plugin.
        
        @return tuple of None and activation status (boolean)
        """
        global error
        
        # cxfreeze is only activated if it is available
        if not _checkProgram():
            return None, False
        
        menu = e5App().getObject("Project").getMenu("Packagers")
        if menu:
            self.__projectAct = E5Action(self.trUtf8('Use cx_freeze'),
                    self.trUtf8('Use cx_&freeze'), 0, 0,
                    self, 'packagers_cxfreeze')
            self.__projectAct.setStatusTip(
                self.trUtf8('Generate a distribution package using cx_freeze'))
            self.__projectAct.setWhatsThis(self.trUtf8(
            """<b>Use cx_freeze</b>"""
            """<p>Generate a distribution package using cx_freeze."""
            """ The command is executed in the project path. All"""
            """ files and directories must be given absolute or"""
            """ relative to the project directory.</p>"""
            ))
            self.connect(self.__projectAct, SIGNAL('triggered()'), self.__cxfreeze)
            e5App().getObject("Project").addE5Actions([self.__projectAct])
            menu.addAction(self.__projectAct)
        
        error = ""
        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        menu = e5App().getObject("Project").getMenu("Packagers")
        if menu:
            if self.__projectAct:
                menu.removeAction(self.__projectAct)
                e5App().getObject("Project").removeE5Actions([self.__projectAct])
        self.__initialize()
    
    def __loadTranslator(self):
        """
        Private method to load the translation file.
        """
        if self.__ui is not None:
            loc = self.__ui.getLocale()
            if loc and loc != "C":
                locale_dir = \
                    os.path.join(os.path.dirname(__file__), "CxFreeze", "i18n")
                translation = "cxfreeze_{0}".format(loc)
                translator = QTranslator(None)
                loaded = translator.load(translation, locale_dir)
                if loaded:
                    self.__translator = translator
                    e5App().installTranslator(self.__translator)
                else:
                    print("Warning: translation file '{0}' could not be loaded."\
                        .format(translation))
                    print("Using default.")
    
    def __cxfreeze(self):
        """
        Private slot to handle the cxfreeze execution.
        """
        project = e5App().getObject("Project")
        if len(project.pdata["MAINSCRIPT"]) == 0:
            # no main script defined
            QMessageBox.critical(None,
                self.trUtf8("cxfreeze"),
                self.trUtf8(
                    """There is no main script defined for the current project."""),
                QMessageBox.StandardButtons(
                    QMessageBox.Abort))
            return
        
        parms = project.getData('PACKAGERSPARMS', "CXFREEZE")
        exe = _findExecutable()
        if exe is None:
            QMessageBox.critical(None,
                self.trUtf8("cxfreeze"),
                self.trUtf8("""The cxfreeze executable could not be found."""))
            return

        dlg = CxfreezeConfigDialog(project, exe, parms)
        if dlg.exec_() == QDialog.Accepted:
            args, parms = dlg.generateParameters()
            project.setData('PACKAGERSPARMS', "CXFREEZE", parms)
            
            # now do the call
            dia = CxfreezeExecDialog("cxfreeze")
            dia.show()
            res = dia.start(args, 
                os.path.join(project.ppath, project.pdata["MAINSCRIPT"][0]))
            if res:
                dia.exec_()

