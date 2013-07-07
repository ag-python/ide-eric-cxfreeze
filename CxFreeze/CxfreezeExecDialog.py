# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2013 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the packager process.
"""

from __future__ import unicode_literals    # __IGNORE_WARNING__
try:
    str = unicode   # __IGNORE_WARNING__
except (NameError):
    pass

import os.path

from PyQt4.QtCore import pyqtSlot, QProcess, QTimer
from PyQt4.QtGui import QDialog, QDialogButtonBox, QAbstractButton

from E5Gui import E5MessageBox

from .Ui_CxfreezeExecDialog import Ui_CxfreezeExecDialog

import Preferences

class CxfreezeExecDialog(QDialog, Ui_CxfreezeExecDialog):
    """
    Module implementing a dialog to show the output of the cxfreeze process.
    
    This class starts a QProcess and displays a dialog that
    shows the output of the packager command process.
    """
    def __init__(self, cmdname, parent=None):
        """
        Constructor
        
        @param cmdname name of the packager (string)
        @param parent parent widget of this dialog (QWidget)
        """
        QDialog.__init__(self, parent)
        self.setupUi(self)
        
        self.buttonBox.button(QDialogButtonBox.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Cancel).setDefault(True)
        
        self.process = None
        self.cmdname = cmdname
    
    def start(self, args, script):
        """
        Public slot to start the packager command.
        
        @param args commandline arguments for packager program (list of strings)
        @param script main script name to be processed by by the packager (string)
        @return flag indicating the successful start of the process
        """
        self.errorGroup.hide()
        
        dname = os.path.dirname(script)
        script = os.path.basename(script)
        
        self.contents.clear()
        self.errors.clear()
        
        args.append(script)
        
        self.process = QProcess()
        self.process.setWorkingDirectory(dname)
        
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)
        self.process.finished.connect(self.__finish)
            
        self.setWindowTitle(self.trUtf8('{0} - {1}').format(self.cmdname, script))
        self.contents.insertPlainText(' '.join(args) + '\n\n')
        self.contents.ensureCursorVisible()
        
        program = args.pop(0)
        self.process.start(program, args)
        procStarted = self.process.waitForStarted()
        if not procStarted:
            E5MessageBox.critical(None,
                self.trUtf8('Process Generation Error'),
                self.trUtf8(
                    'The process {0} could not be started. '
                    'Ensure, that it is in the search path.'
                ).format(program))
        return procStarted
    
    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.
        
        @param button button that was clicked (QAbstractButton)
        """
        if button == self.buttonBox.button(QDialogButtonBox.Close):
            self.accept()
        elif button == self.buttonBox.button(QDialogButtonBox.Cancel):
            self.__finish()
    
    def __finish(self):
        """
        Private slot called when the process finished.
        
        It is called when the process finished or
        the user pressed the cancel button.
        """
        if self.process is not None and \
           self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            QTimer.singleShot(2000, self.process.kill)
            self.process.waitForFinished(3000)
        
        self.buttonBox.button(QDialogButtonBox.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Close).setDefault(True)
        
        self.process = None
        
        self.contents.insertPlainText(
            self.trUtf8('\n{0} finished.\n').format(self.cmdname))
        self.contents.ensureCursorVisible()
    
    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.
        
        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        self.process.setReadChannel(QProcess.StandardOutput)
        
        while self.process.canReadLine():
            s = str(self.process.readAllStandardOutput(),
                    Preferences.getSystem("IOEncoding"),
                    'replace')
            self.contents.insertPlainText(s)
            self.contents.ensureCursorVisible()
    
    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.
        
        It reads the error output of the process and inserts it into the
        error pane.
        """
        self.process.setReadChannel(QProcess.StandardError)
        
        while self.process.canReadLine():
            self.errorGroup.show()
            s = str(self.process.readAllStandardError(),
                    Preferences.getSystem("IOEncoding"),
                    'replace')
            self.errors.insertPlainText(s)
            self.errors.ensureCursorVisible()
