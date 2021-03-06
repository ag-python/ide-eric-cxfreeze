# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2020 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the CxFreeze plugin.
"""

import os
import platform

from PyQt5.QtCore import QObject, QTranslator, QCoreApplication, QProcess
from PyQt5.QtWidgets import QDialog

from E5Gui import E5MessageBox
from E5Gui.E5Action import E5Action
from E5Gui.E5Application import e5App
    
import Utilities

# Start-of-Header
name = "CxFreeze Plugin"
author = "Detlev Offenbach <detlev@die-offenbachs.de>"
autoactivate = True
deactivateable = True
version = "7.0.0"
className = "CxFreezePlugin"
packageName = "CxFreeze"
shortDescription = "Show the CxFreeze dialogs."
longDescription = (
    """This plugin implements the CxFreeze dialogs."""
    """ CxFreeze is used to generate a distribution package."""
)
needsRestart = False
pyqtApi = 2
# End-of-Header

error = ""

exePy3 = []


def exeDisplayDataList():
    """
    Public method to support the display of some executable info.
    
    @return dictionary containing the data to query the presence of
        the executable
    """
    dataList = []
    data = {
        "programEntry": True,
        "header": QCoreApplication.translate(
            "CxFreezePlugin", "Packagers - cx_freeze"),
        "exe": 'dummyfreeze',
        "versionCommand": '--version',
        "versionStartsWith": 'dummyfreeze',
        "versionPosition": -1,
        "version": "",
        "versionCleanup": None,
    }
    
    if _checkProgram():
        for exePath in exePy3:
            data["exe"] = exePath
            data["versionStartsWith"] = "cxfreeze"
            dataList.append(data.copy())
    else:
        dataList.append(data)
    return dataList


def _findExecutable(majorVersion):
    """
    Restricted function to determine the names of the executable.
    
    @param majorVersion major python version of the executables (int)
    @return names of the executable (list)
    """
    # Determine Python Version
    if majorVersion == 3:
        minorVersions = range(10)
    else:
        return []
    
    executables = set()
    if Utilities.isWindowsPlatform():
        #
        # Windows
        #
        try:
            import winreg
        except ImportError:
            import _winreg as winreg    # __IGNORE_WARNING__
        
        def getExePath(branch, access, versionStr):
            try:
                software = winreg.OpenKey(branch, 'Software', 0, access)
                python = winreg.OpenKey(software, 'Python', 0, access)
                pcore = winreg.OpenKey(python, 'PythonCore', 0, access)
                version = winreg.OpenKey(pcore, versionStr, 0, access)
                installpath = winreg.QueryValue(version, 'InstallPath')
                exe = os.path.join(installpath, 'Scripts', 'cxfreeze.bat')
                if os.access(exe, os.X_OK):
                    return exe
            except WindowsError:        # __IGNORE_WARNING__
                return None
            return None
        
        versionSuffixes = ["", "-32", "-64"]
        for minorVersion in minorVersions:
            for versionSuffix in versionSuffixes:
                versionStr = '{0}.{1}{2}'.format(majorVersion, minorVersion,
                                                 versionSuffix)
                exePath = getExePath(
                    winreg.HKEY_CURRENT_USER,
                    winreg.KEY_WOW64_32KEY | winreg.KEY_READ, versionStr)
                if exePath is not None:
                    executables.add(exePath)
                
                exePath = getExePath(
                    winreg.HKEY_LOCAL_MACHINE,
                    winreg.KEY_WOW64_32KEY | winreg.KEY_READ, versionStr)
                if exePath is not None:
                    executables.add(exePath)
                
                # Even on Intel 64-bit machines it's 'AMD64'
                if platform.machine() == 'AMD64':
                    exePath = getExePath(
                        winreg.HKEY_CURRENT_USER,
                        winreg.KEY_WOW64_64KEY | winreg.KEY_READ, versionStr)
                    if exePath is not None:
                        executables.add(exePath)
                    
                    exePath = getExePath(
                        winreg.HKEY_LOCAL_MACHINE,
                        winreg.KEY_WOW64_64KEY | winreg.KEY_READ, versionStr)
                    if exePath is not None:
                        executables.add(exePath)
        
        if not executables and majorVersion >= 3:
            # check the PATH environment variable if nothing was found
            # Python 3 only
            path = Utilities.getEnvironmentEntry('PATH')
            if path:
                dirs = path.split(os.pathsep)
                for directory in dirs:
                    for suffix in (".bat", ".exe"):
                        exe = os.path.join(directory, "cxfreeze" + suffix)
                        if os.access(exe, os.X_OK):
                            executables.add(exe)
    else:
        #
        # Linux, Unix ...
        cxfreezeScript = 'cxfreeze'
        scriptSuffixes = ["", "-python{0}".format(majorVersion)]
        for minorVersion in minorVersions:
            scriptSuffixes.append(
                "-python{0}.{1}".format(majorVersion, minorVersion))
        # There could be multiple cxfreeze executables in the path
        # e.g. for different python variants
        path = Utilities.getEnvironmentEntry('PATH')
        # environment variable not defined
        if path is None:
            return []
        
        # step 1: determine possible candidates
        exes = []
        dirs = path.split(os.pathsep)
        for directory in dirs:
            for suffix in scriptSuffixes:
                exe = os.path.join(directory, cxfreezeScript + suffix)
                if os.access(exe, os.X_OK):
                    exes.append(exe)
        
        # step 2: determine the Python variant
        _exePy3 = set()
        versionArgs = ["-c", "import sys; print(sys.version_info[0])"]
        for exe in exes:
            try:
                f = open(exe, "r")
                line0 = f.readline()
                program = line0.replace("#!", "").strip()
                process = QProcess()
                process.start(program, versionArgs)
                process.waitForFinished(5000)
                # get a QByteArray of the output
                versionBytes = process.readAllStandardOutput()
                versionStr = str(versionBytes, encoding='utf-8').strip()
                if versionStr == "3":
                    _exePy3.add(exe)
            finally:
                f.close()
        
        executables = _exePy3
    
    # sort items, the probably newest topmost
    executables = list(executables)
    executables.sort(reverse=True)
    return executables


def _checkProgram():
    """
    Restricted function to check the availability of cxfreeze.
    
    @return flag indicating availability (boolean)
    """
    global error, exePy3
    
    exePy3 = _findExecutable(3)
    if exePy3 == []:
        if Utilities.isWindowsPlatform():
            error = QCoreApplication.translate(
                "CxFreezePlugin",
                "The cxfreeze.bat executable could not be found."
                "Did you run the cxfreeze-postinstall script?")
        else:
            error = QCoreApplication.translate(
                "CxFreezePlugin",
                "The cxfreeze executable could not be found.")
        return False
    else:
        return True


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
        self.__projectSeparator = None
       
    def activate(self):
        """
        Public method to activate this plugin.
        
        @return tuple of None and activation status (boolean)
        """
        global error
        
        # There is already an error, don't activate
        if error:
            return None, False
        
        # cxfreeze is only activated if it is available
        if not _checkProgram():
            return None, False
        
        project = e5App().getObject("Project")
        menu = project.getMenu("Packagers")
        if menu:
            self.__projectAct = E5Action(
                self.tr('Use cx_freeze'),
                self.tr('Use cx_&freeze'), 0, 0,
                self, 'packagers_cxfreeze')
            self.__projectAct.setStatusTip(
                self.tr('Generate a distribution package using cx_freeze'))
            self.__projectAct.setWhatsThis(self.tr(
                """<b>Use cx_freeze</b>"""
                """<p>Generate a distribution package using cx_freeze."""
                """ The command is executed in the project path. All"""
                """ files and directories must be given absolute or"""
                """ relative to the project directory.</p>"""
            ))
            self.__projectAct.triggered.connect(self.__cxfreeze)
            project.addE5Actions([self.__projectAct])
            self.__projectSeparator = menu.addSeparator()
            menu.addAction(self.__projectAct)
            project.showMenu.connect(self.__projectShowMenu)
        
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
                e5App().getObject("Project").removeE5Actions(
                    [self.__projectAct])
            if self.__projectSeparator:
                menu.removeAction(self.__projectSeparator)
        
        self.__initialize()
    
    def __projectShowMenu(self, menuName, menu):
        """
        Private slot called, when the the project menu or a submenu is
        about to be shown.
        
        @param menuName name of the menu to be shown (string)
        @param menu reference to the menu (QMenu)
        """
        if menuName == "Packagers":
            if self.__projectAct is not None:
                self.__projectAct.setEnabled(
                    e5App().getObject("Project").getProjectLanguage() ==
                    "Python3"
                )
    
    def __loadTranslator(self):
        """
        Private method to load the translation file.
        """
        if self.__ui is not None:
            loc = self.__ui.getLocale()
            if loc and loc != "C":
                locale_dir = os.path.join(os.path.dirname(__file__),
                                          "CxFreeze", "i18n")
                translation = "cxfreeze_{0}".format(loc)
                translator = QTranslator(None)
                loaded = translator.load(translation, locale_dir)
                if loaded:
                    self.__translator = translator
                    e5App().installTranslator(self.__translator)
                else:
                    print("Warning: translation file '{0}' could not be"
                          " loaded.".format(translation))
                    print("Using default.")
    
    def __cxfreeze(self):
        """
        Private slot to handle the cxfreeze execution.
        """
        project = e5App().getObject("Project")
        if not project.getMainScript():
            # no main script defined
            E5MessageBox.critical(
                self.__ui,
                self.tr("cxfreeze"),
                self.tr(
                    """There is no main script defined for the current"""
                    """ project."""),
                E5MessageBox.StandardButtons(E5MessageBox.Abort))
            return
        
        majorVersionStr = project.getProjectLanguage()
        exe = {"Python3": exePy3}.get(majorVersionStr)
        if exe == []:
            E5MessageBox.critical(
                self.__ui,
                self.tr("cxfreeze"),
                self.tr("""The cxfreeze executable could not be found."""))
            return

        # check if all files saved and errorfree before continue
        if not project.checkAllScriptsDirty(reportSyntaxErrors=True):
            return

        from CxFreeze.CxfreezeConfigDialog import CxfreezeConfigDialog
        parms = project.getData('PACKAGERSPARMS', "CXFREEZE")
        dlg = CxfreezeConfigDialog(project, exe, parms)
        if dlg.exec_() == QDialog.Accepted:
            args, parms = dlg.generateParameters()
            project.setData('PACKAGERSPARMS', "CXFREEZE", parms)
            
            # now do the call
            from CxFreeze.CxfreezeExecDialog import CxfreezeExecDialog
            dia = CxfreezeExecDialog("cxfreeze")
            dia.show()
            res = dia.start(args, parms, project.ppath,
                            project.getMainScript())
            if res:
                dia.exec_()

#
# eflag: noqa = M801
