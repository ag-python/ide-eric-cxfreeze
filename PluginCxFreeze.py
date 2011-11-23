# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2011 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the CxFreeze plugin.
"""

import os
import sys

from PyQt4.QtCore import QObject, QTranslator, QCoreApplication
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
version = "5.0.6"
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
        data["versionStartsWith"] = "cxfreeze"
    
    return data

def _findExecutable():
    """
    Restricted function to determine the name of the executable.
    
    @return name of the executable (string)
    """
    if Utilities.isWindowsPlatform():
        #
        # Windows
        #
        exe = 'cxfreeze.bat'
        if Utilities.isinpath(exe):
            return exe
        try:
            #only since python 3.2
            import sysconfig
            scripts = sysconfig.get_path('scripts','nt')
            return os.path.join(scripts, exe)
        except ImportError:
            try:
                import winreg
            except ImportError:
                # give up ...
                return None
            
            def getExePath(branch):
                version = str(sys.version_info.major) + '.' + \
                          str(sys.version_info.minor)
                try:
                    software = winreg.OpenKey(branch, 'Software')
                    python = winreg.OpenKey(software, 'Python')
                    pcore = winreg.OpenKey(python, 'PythonCore')
                    version = winreg.OpenKey(pcore, version)
                    installpath = winreg.QueryValue(version, 'InstallPath')
                    return os.path.join(installpath, 'Scripts', exe)
                except WindowsError:        # __IGNORE_WARNING__
                    return None
            
            exePath = getExePath(winreg.HKEY_CURRENT_USER)
            if not exePath:
                exePath = getExePath(winreg.HKEY_LOCAL_MACHINE)
            return exePath
    else:
        #
        # Linux, Unix ...
        cxfreezeScript = 'cxfreeze'
        # There could be multiple cxfreeze executables in the path
        # e.g. for different python variants
        path = Utilities.getEnvironmentEntry('PATH')
        # environment variable not defined
        if path is None:
            return None
        
        # step 1: determine possible candidates
        exes = []
        dirs = path.split(os.pathsep)
        for dir in dirs:
            exe = os.path.join(dir, cxfreezeScript)
            if os.access(exe, os.X_OK):
                exes.append(exe)
        
        # step 2: determine the Python 3 variant
        found = False
        if Utilities.isMacPlatform():
            checkStr = "Python.framework/Versions/3".lower()
        else:
            checkStr = "python3"
        for exe in exes:
            try:
                f = open(exe, "r")
                line0 = f.readline()
                if checkStr in line0.lower():
                    found = True
            finally:
                f.close()
            if found:
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
            self.__projectAct.triggered[()].connect(self.__cxfreeze)
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

