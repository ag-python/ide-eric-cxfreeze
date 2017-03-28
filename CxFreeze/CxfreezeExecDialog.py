# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2017 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the packager process.
"""

from __future__ import unicode_literals
try:
    str = unicode
except NameError:
    pass

import shutil
import errno
import fnmatch
import os.path

from PyQt5.QtCore import pyqtSlot, QProcess, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QAbstractButton

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
        self.copyProcess = None
        self.cmdname = cmdname
    
    def start(self, args, parms, ppath, mainscript):
        """
        Public slot to start the packager command.
        
        @param args commandline arguments for packager program (list of
            strings)
        @param parms parameters got from the config dialog (dict)
        @param ppath project path (string)
        @param mainscript main script name to be processed by by the packager
            (string)
        @return flag indicating the successful start of the process
        """
        self.errorGroup.hide()
        script = os.path.join(ppath, mainscript)
        dname = os.path.dirname(script)
        script = os.path.basename(script)
        
        self.ppath = ppath
        self.additionalFiles = parms.get('additionalFiles', [])
        self.targetDirectory = os.path.join(
            parms.get('targetDirectory', 'dist'))
        
        self.contents.clear()
        self.errors.clear()
        
        args.append(script)
        
        self.process = QProcess()
        self.process.setWorkingDirectory(dname)
        
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)
        self.process.finished.connect(self.__finishedFreeze)
            
        self.setWindowTitle(self.tr('{0} - {1}').format(
            self.cmdname, script))
        self.contents.insertPlainText(' '.join(args) + '\n\n')
        self.contents.ensureCursorVisible()
        
        program = args.pop(0)
        self.process.start(program, args)
        procStarted = self.process.waitForStarted()
        if not procStarted:
            E5MessageBox.critical(
                self,
                self.tr('Process Generation Error'),
                self.tr(
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
            self.additionalFiles = []   # Skip copying additional files
            self.__finish()
    
    def __finish(self):
        """
        Private slot called when the process finished.
        
        It is called when the process finished or
        the user pressed the cancel button.
        """
        if self.process is not None:
            self.process.disconnect(self.__finishedFreeze)
            self.process.terminate()
            QTimer.singleShot(2000, self.process.kill)
            self.process.waitForFinished(3000)
        self.process = None
        
        if self.copyProcess is not None:
            self.copyProcess.terminate()
        self.copyProcess = None
        
        self.contents.insertPlainText(
            self.tr('\n{0} aborted.\n').format(self.cmdname))
        
        self.__enableButtons()
    
    def __finishedFreeze(self):
        """
        Private slot called when the process finished.
        
        It is called when the process finished or
        the user pressed the cancel button.
        """
        self.process = None

        self.contents.insertPlainText(
            self.tr('\n{0} finished.\n').format(self.cmdname))
        
        self.copyProcess = CopyAdditionalFiles(self)
        self.copyProcess.insertPlainText.connect(self.contents.insertPlainText)
        self.copyProcess.finished.connect(self.__enableButtons)
        self.copyProcess.start()
    
    def __enableButtons(self):
        """
        Private slot called when all processes finished.
        
        It is called when the process finished or
        the user pressed the cancel button.
        """
        self.copyProcess = None
        self.buttonBox.button(QDialogButtonBox.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Close).setDefault(True)
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


class CopyAdditionalFiles(QThread):
    """
    Thread to copy the distribution dependent files.
    
    @signal insertPlainText(text) emitted to inform user about the copy
        progress
    """
    insertPlainText = pyqtSignal(str)
    
    def __init__(self, main):
        """
        Constructor
        
        @param main self-object of the caller
        """
        super(CopyAdditionalFiles, self).__init__()
        
        self.ppath = main.ppath
        self.additionalFiles = main.additionalFiles
        self.targetDirectory = main.targetDirectory
    
    def __copytree(self, src, dst):
        """
        Private method to copy a file or folder.
       
        Wildcards allowed. Existing files are overwitten.
        
        @param src source file or folder to copy. Wildcards allowed. (str)
        @param dst destination (str)
        @exception OSError raised if there is an issue writing the package
        @exception IOError raised if the given source does not exist
        """                                             # __IGNORE_WARNING__
        def src2dst(srcname, base, dst):
            """
            Combines the relativ path of the source (srcname) with the
            destination folder.
            
            @param srcname actual file or folder to copy
            @param base basename of the source folder
            @param dst basename of the destination folder
            @return destination path
            """
            delta = srcname.split(base)[1]
            return os.path.join(dst, delta[1:])
        
        base, fileOrFolderName = os.path.split(src)
        initDone = False
        for root, dirs, files in os.walk(base):
            copied = False
            # remove all none matching directorynames, create all others
            for directory in dirs[:]:
                pathname = os.path.join(root, directory)
                if initDone or fnmatch.fnmatch(pathname, src):
                    newDir = src2dst(pathname, base, dst)
                    # avoid infinite loop
                    if fnmatch.fnmatch(newDir, src):
                        dirs.remove(directory)
                        continue
                    try:
                        copied = True
                        os.makedirs(newDir)
                    except OSError as err:
                        if err.errno != errno.EEXIST:
                            # it's ok if directory already exists
                            raise err
                else:
                    dirs.remove(directory)
            
            for file in files:
                fn = os.path.join(root, file)
                if initDone or fnmatch.fnmatch(fn, src):
                    newFile = src2dst(fn, base, dst)
                    # copy files, give errors to caller
                    shutil.copy2(fn, newFile)
                    copied = True
            
            # check if file was found and copied
            if len(files) and not copied:
                raise IOError(
                    errno.ENOENT,
                    self.tr("No such file or directory: '{0}'")
                    .format(src))
            
            initDone = True
            
    def run(self):
        """
        Public method to run the thread.
        
        QThread entry point to copy the selected additional files and folders.
        
        @exception OSError raised if there is an issue writing the package
        """
        self.insertPlainText.emit('----\n')
        os.chdir(self.ppath)
        for fn in self.additionalFiles:
            self.insertPlainText.emit(
                self.tr('\nCopying {0}: ').format(fn))
            
            # on linux normpath doesn't replace backslashes to slashes.
            fn = fn.replace('\\', '/')
            fn = os.path.abspath(os.path.normpath(fn))
            dst = os.path.join(self.ppath, self.targetDirectory)
            if fn.startswith(os.path.normpath(self.ppath)):
                dirname = fn.split(self.ppath + os.sep)[1]
                dst = os.path.join(dst, os.path.dirname(dirname))
                try:
                    os.makedirs(dst)
                except OSError as err:
                    if err.errno != errno.EEXIST:   # it's ok if directory
                                                    # already exists
                        raise err
            
            try:
                self.__copytree(fn, dst)
                self.insertPlainText.emit(self.tr('ok'))
            except IOError as err:
                self.insertPlainText.emit(
                    self.tr('failed: {0}').format(err.strerror))
