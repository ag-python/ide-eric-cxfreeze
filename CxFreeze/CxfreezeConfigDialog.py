# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2014 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for cxfreeze.
"""

from __future__ import unicode_literals
try:
    str = unicode
except NameError:
    pass

import sys
import os
import copy

from PyQt4.QtCore import pyqtSlot, QDir, QProcess
from PyQt4.QtGui import QDialog, QListWidgetItem, QFileDialog, QPushButton, \
    QTreeView, QItemSelection, QLineEdit, QFileSystemModel

from E5Gui import E5FileDialog
from E5Gui.E5Completers import E5FileCompleter, E5DirCompleter

from .Ui_CxfreezeConfigDialog import Ui_CxfreezeConfigDialog

import Utilities


class DirFileDialog(QFileDialog):
    """
    Derived QFileDialog to select files and folders at once.
    
    For this purpose the none native filedialog is used.
    """
    def __init__(self, parent=None, caption="", directory="", filter=""):
        """
        Extend the normal none native file dialog to select files and folders
        at once.
        
        @param parent parent widget of the dialog (QWidget)
        @param caption window title of the dialog (string)
        @param directory working directory of the dialog (string)
        @param filter filter string for the dialog (string)
        """
        self.selectedFilesFolders = []
        
        QFileDialog.__init__(self, parent, caption, directory, filter)
        self.setFileMode(QFileDialog.ExistingFiles)
    
    def exec_(self):
        """
        Public slot to finalize initialisation and start the event loop.
        
        @return accepted or rejected (QDialog.DialogCode)
        """
        self.openBtn = self.findChildren(QPushButton)[0]
        self.fileNameEdit = self.findChild(QLineEdit)
        self.directoryEntered.connect(self.on_directoryEntered)
        self.tree = self.findChild(QTreeView)
        self.tree.selectionModel().selectionChanged.connect(
            self.on_selectionChanged)
        return QFileDialog.exec_(self)
    
    def accept(self):
        """
        Update the list with the selected files and folders.
        """
        # Avoid to close the dialog if only return is pressed
        if not self.openBtn.isEnabled():
            return

        self.selectedFilesFolders = [
            x.data(QFileSystemModel.FilePathRole)
            for x in self.tree.selectionModel().selectedIndexes()
            if x.column() == 0]
        self.hide()
    
    @pyqtSlot(str)
    def on_directoryEntered(self, dir):
        """
        Reset selections if another directory was entered.
        
        @param dir name of the directory entered (string)
        """
        self.tree.selectionModel().clear()
        self.fileNameEdit.clear()
        self.openBtn.setEnabled(False)
    
    @pyqtSlot(QItemSelection, QItemSelection)
    def on_selectionChanged(self, selected, deselected):
        """
        Determine the selected files and folders and update the lineedit.
        
        @param selected newly selected entries (QItemSelection)
        @param deselected deselected entries (QItemSelection)
        """
        selectedItems = self.tree.selectionModel().selectedIndexes()
        if self.tree.rootIndex() in selectedItems or selectedItems == []:
            return
        selectedFiles = [x.data(QFileSystemModel.FileNameRole)
                         for x in selectedItems if x.column() == 0]
        enteredFiles = self.fileNameEdit.text().split('"')
        enteredFiles = [x for x in enteredFiles if x.strip() != '']
        # Check if there is a directory in the selection. Then update the
        # lineEdit.
        for selectedFile in selectedFiles:
            if selectedFile not in enteredFiles:
                txt = '" "'.join(selectedFiles)
                if len(selectedFiles) > 1:
                    txt = '"{0}"'.format(txt)
                self.fileNameEdit.setText(txt)
                break
    
    @staticmethod
    def getOpenFileNames(parent=None, caption="", directory="",
                         filter="", options=QFileDialog.Options()):
        """
        Static method to get the names of files and folders for opening it.
        
        @param parent parent widget of the dialog (QWidget)
        @param caption window title of the dialog (string)
        @param directory working directory of the dialog (string)
        @param filter filter string for the dialog (string)
        @param options various options for the dialog (QFileDialog.Options)
        @return names of the selected files and folders (list of strings)
        """
        options |= QFileDialog.DontUseNativeDialog
        dlg = DirFileDialog(parent, caption, directory, filter)
        dlg.setOptions(options)
        dlg.exec_()
        return dlg.selectedFilesFolders


class CxfreezeConfigDialog(QDialog, Ui_CxfreezeConfigDialog):
    """
    Class implementing a dialog to enter the parameters for cxfreeze.
    """
    def __init__(self, project, exe, parms=None, parent=None):
        """
        Constructor
        
        @param project reference to the project object (Project.Project)
        @param exe name of the cxfreeze executable (string)
        @param parms parameters to set in the dialog
        @param parent parent widget of this dialog (QWidget)
        """
        QDialog.__init__(self, parent)
        self.setupUi(self)
        
        self.project = project
        self.__initializeDefaults()
        
        # get a copy of the defaults to store the user settings
        self.parameters = copy.deepcopy(self.defaults)
        
        # combine it with the values of parms
        if parms is not None:
            for key, value in parms.items():
                if key in self.parameters:
                    self.parameters[key] = parms[key]
        
        self.exe = exe
        self.cxfreezeExecCombo.addItems(exe)
        # try to set the saved script path
        try:
            idx = exe.index(self.parameters['script'])
            self.cxfreezeExecCombo.setCurrentIndex(idx)
        except ValueError:
            pass
        
        self.targetDirCompleter = E5DirCompleter(self.targetDirEdit)
        self.extListFileCompleter = E5FileCompleter(self.extListFileEdit)
        
        # initialize general tab
        self.targetDirEdit.setText(self.parameters['targetDirectory'])
        self.targetNameEdit.setText(self.parameters['targetName'])
        self.basenameCombo.setEditText(self.parameters['baseName'])
        self.initscriptCombo.setEditText(self.parameters['initScript'])
        self.applicationIconEdit.setText(self.parameters['applicationIcon'])
        self.keeppathCheckBox.setChecked(self.parameters['keepPath'])
        self.compressCheckBox.setChecked(self.parameters['compress'])
        if self.parameters['optimize'] == 0:
            self.nooptimizeRadioButton.setChecked(True)
        elif self.parameters['optimize'] == 1:
            self.optimizeRadioButton.setChecked(True)
        else:
            self.optimizeDocRadioButton.setChecked(True)
        
        # initialize advanced tab
        self.defaultPathEdit.setText(
            os.pathsep.join(self.parameters['defaultPath']))
        self.includePathEdit.setText(
            os.pathsep.join(self.parameters['includePath']))
        self.replacePathsEdit.setText(
            os.pathsep.join(self.parameters['replacePaths']))
        self.includeModulesEdit.setText(
            ','.join(self.parameters['includeModules']))
        self.excludeModulesEdit.setText(
            ','.join(self.parameters['excludeModules']))
        self.extListFileEdit.setText(self.parameters['extListFile'])
        
        # initialize additional files tab
        self.fileOrFolderList.addItems(self.parameters['additionalFiles'])
    
    def __initializeDefaults(self):
        """
        Private method to set the default values.
        
        These are needed later on to generate the commandline parameters.
        """
        self.defaults = {
            # general options
            'targetDirectory': '',
            'targetName': '',
            'baseName': 'Console',
            'initScript': 'Console',
            'applicationIcon': '',
            'script': '',
            'keepPath': False,
            'compress': False,
            'optimize': 0,     # 0, 1 or 2
            
            # advanced options
            'defaultPath': [],
            'includePath': [],
            'replacePaths': [],
            'includeModules': [],
            'excludeModules': [],
            'extListFile': '',
            
            # additional files tab
            'additionalFiles': [],
        }
        # overwrite 'baseName' if OS is Windows
        if sys.platform == 'win32':
            self.defaults['baseName'] = 'Win32GUI'
        # overwrite 'initScript' if version 3 interpreter
        if self.project.getProjectLanguage() == 'Python3':
            self.defaults['initScript'] = 'Console3'
    
    def generateParameters(self):
        """
        Public method that generates the commandline parameters.
        
        It generates a list of strings to be used to set the QProcess arguments
        for the cxfreeze call and a list containing the non default parameters.
        The second list can be passed back upon object generation to overwrite
        the default settings.
        
        @return a tuple of the commandline parameters and non default
            parameters (list of strings, dictionary)
        """
        parms = {}
        args = []
        
        # 1. the program name
        args.append(self.cxfreezeExecCombo.currentText())
        
        # 2. the commandline options
        # 2.1 general options
        if self.parameters['targetDirectory'] != \
                self.defaults['targetDirectory']:
            parms['targetDirectory'] = self.parameters['targetDirectory']
            args.append('--target-dir={0}'.format(
                self.parameters['targetDirectory']))
        if self.parameters['targetName'] != self.defaults['targetName']:
            parms['targetName'] = self.parameters['targetName'][:]
            args.append('--target-name={0}'.format(
                self.parameters['targetName']))
        parms['baseName'] = self.parameters['baseName'][:]
        if self.parameters['baseName'] != '':
            args.append('--base-name={0}'.format(self.parameters['baseName']))
        parms['initScript'] = self.parameters['initScript'][:]
        if self.parameters['initScript'] != '':
            args.append('--init-script={0}'.format(
                self.parameters['initScript']))
        parms['applicationIcon'] = self.parameters['applicationIcon'][:]
        if self.parameters['applicationIcon'] != \
                self.defaults['applicationIcon']:
            args.append('--icon={0}'.format(
                self.parameters['applicationIcon']))
        parms['script'] = self.parameters['script'][:]
        if self.parameters['keepPath'] != self.defaults['keepPath']:
            parms['keepPath'] = self.parameters['keepPath']
            args.append('--no-copy-deps')
        if self.parameters['compress'] != self.defaults['compress']:
            parms['compress'] = self.parameters['compress']
            args.append('--compress')
        if self.parameters['optimize'] != self.defaults['optimize']:
            parms['optimize'] = self.parameters['optimize']
            if self.parameters['optimize'] == 1:
                args.append('-O')
            elif self.parameters['optimize'] == 2:
                args.append('-OO')
        
        # 2.2 advanced options
        if self.parameters['defaultPath'] != self.defaults['defaultPath']:
            parms['defaultPath'] = self.parameters['defaultPath'][:]
            args.append('--default-path={0}'.format(
                        os.pathsep.join(self.parameters['defaultPath'])))
        if self.parameters['includePath'] != self.defaults['includePath']:
            parms['includePath'] = self.parameters['includePath'][:]
            args.append('--include-path={0}'.format(
                        os.pathsep.join(self.parameters['includePath'])))
        if self.parameters['replacePaths'] != self.defaults['replacePaths']:
            parms['replacePaths'] = self.parameters['replacePaths'][:]
            args.append('--replace-paths={0}'.format(
                        os.pathsep.join(self.parameters['replacePaths'])))
        if self.parameters['includeModules'] != \
                self.defaults['includeModules']:
            parms['includeModules'] = self.parameters['includeModules'][:]
            args.append('--include-modules={0}'.format(
                        ','.join(self.parameters['includeModules'])))
        if self.parameters['excludeModules'] != \
                self.defaults['excludeModules']:
            parms['excludeModules'] = self.parameters['excludeModules'][:]
            args.append('--exclude-modules={0}'.format(
                        ','.join(self.parameters['excludeModules'])))
        if self.parameters['extListFile'] != self.defaults['extListFile']:
            parms['extListFile'] = self.parameters['extListFile']
            args.append('--ext-list-file={0}'.format(
                self.parameters['extListFile']))
        
        # 2.3 additional files tab
        if self.parameters['additionalFiles'] != []:
            parms['additionalFiles'] = self.parameters['additionalFiles'][:]
        
        return (args, parms)

    @pyqtSlot()
    def on_extListFileButton_clicked(self):
        """
        Private slot to select the external list file.
        
        It displays a file selection dialog to select the external list file,
        the list of include modules is written to.
        """
        extList = E5FileDialog.getOpenFileName(
            self,
            self.trUtf8("Select external list file"),
            self.extListFileEdit.text(),
            "")
        
        if extList:
            # make it relative, if it is in a subdirectory of the project path
            lf = Utilities.toNativeSeparators(extList)
            lf = self.project.getRelativePath(lf)
            self.extListFileEdit.setText(lf)

    @pyqtSlot()
    def on_iconFileButton_clicked(self):
        """
        Private slot to select an icon.
        
        It displays a file selection dialog to select an icon to
        include into the executable.
        """
        iconsI18N = self.trUtf8("Icons")
        allFilesI18N = self.trUtf8("All files")
        if Utilities.isWindowsPlatform():
            iconFilter = "{0} (*.ico);;{1} (*.*)".format(
                iconsI18N, allFilesI18N)
        elif Utilities.isMacPlatform():
            iconFilter = "{0} (*.icns *.png);;{1} (*.*)".format(
                iconsI18N, allFilesI18N)
        else:
            iconFilter = "{0} (*.png);;{1} (*.*)".format(
                iconsI18N, allFilesI18N)
        
        iconList = E5FileDialog.getOpenFileName(
            self,
            self.trUtf8("Select the application icon"),
            self.applicationIconEdit.text(),
            iconFilter)
        
        if iconList:
            # make it relative, if it is in a subdirectory of the project path
            lf = Utilities.toNativeSeparators(iconList)
            lf = self.project.getRelativePath(lf)
            self.applicationIconEdit.setText(lf)

    @pyqtSlot()
    def on_targetDirButton_clicked(self):
        """
        Private slot to select the target directory.
        
        It displays a directory selection dialog to
        select the directory the files are written to.
        """
        directory = E5FileDialog.getExistingDirectory(
            self,
            self.trUtf8("Select target directory"),
            self.targetDirEdit.text(),
            E5FileDialog.Options(E5FileDialog.ShowDirsOnly))
        
        if directory:
            # make it relative, if it is a subdirectory of the project path
            dn = Utilities.toNativeSeparators(directory)
            dn = self.project.getRelativePath(dn)
            while dn.endswith(os.sep):
                dn = dn[:-1]
            self.targetDirEdit.setText(dn)
    
    @pyqtSlot(str)
    def on_cxfreezeExecCombo_currentIndexChanged(self, text):
        """
        Private slot to handle the selection of a cxfreeze executable.
        
        @param text selected cxfreeze executable (string)
        """
        # version specific setup
        if Utilities.isWindowsPlatform():
            # remove "\Scripts\cx_Freeze.bat" from path
            dirname = os.path.dirname(text)
            dirname = os.path.dirname(dirname)
            
            # first try the fast way
            modpath = os.path.join(
                dirname, "Lib", "site-packages", "cx_Freeze")
            if not os.path.exists(modpath):
                # but if it failed search in the whole directory tree
                modpath = None
                for dirpath, dirnames, filenames in os.walk(dirname):
                    if 'cx_Freeze' in dirnames:
                        modpath = os.path.join(dirpath, "cx_Freeze")
                        break
        else:
            with open(text, 'r') as f:
                args = f.readline()
            if not args:
                return
                
            args = args.strip('!#\n').split(' ')
            program = args.pop(0)

            script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'CxfreezeFindPath.py')
            if not os.path.exists(script):
                return
            
            args.append(script)
            process = QProcess()
            process.start(program, args)
            process.waitForFinished(5000)
            # get a QByteArray of the output
            cxPath = process.readAllStandardOutput()
            modpath = str(cxPath, encoding='utf-8').strip('\n\r')
            if not modpath.endswith('cx_Freeze'):
                return
        
        # populate combo boxes
        if modpath:
            d = QDir(os.path.join(modpath, 'bases'))
            basesList = d.entryList(QDir.Filters(QDir.Files))
            if Utilities.isWindowsPlatform():
                # strip the final '.exe' from the bases
                tmpBasesList = basesList[:]
                basesList = []
                for b in tmpBasesList:
                    base, ext = os.path.splitext(b)
                    if ext == ".exe":
                        basesList.append(base)
                    else:
                        basesList.append(b)
            
            basesList.insert(0, '')
            currentText = self.basenameCombo.currentText()
            self.basenameCombo.clear()
            self.basenameCombo.addItems(basesList)
            self.basenameCombo.setEditText(currentText)
            
            d = QDir(os.path.join(modpath, 'initscripts'))
            initList = d.entryList(['*.py'])
            initList.insert(0, '')
            currentText = self.initscriptCombo.currentText()
            self.initscriptCombo.clear()
            self.initscriptCombo.addItems(
                [os.path.splitext(i)[0] for i in initList])
            self.initscriptCombo.setEditText(currentText)
    
    def on_fileOrFolderList_currentRowChanged(self, row):
        """
        Private slot to handle the currentRowChanged signal of the
        fileOrFolderList.
        
        @param row the current row (integer)
        """
        self.deleteSelectedButton.setEnabled(row != -1)
        if row != -1:
            self.fileOrFolderList.setCurrentRow(row)
    
    @pyqtSlot(QListWidgetItem)
    def on_fileOrFolderList_itemDoubleClicked(self, itm):
        """
        Private slot to handle the itemDoubleClicked signal of the
        fileOrFolderList.
        
        @param itm the selected row (QListWidgetItem)
        """
        self.fileOrFolderEdit.setText(itm.text())
        row = self.fileOrFolderList.currentRow()
        itm = self.fileOrFolderList.takeItem(row)
        del itm
    
    @pyqtSlot()
    def on_addFileOrFolderButton_clicked(self):
        """
        Private slot to add the entered file or directory to the list view.
        """
        txt = self.fileOrFolderEdit.text()
        if txt:
            self.fileOrFolderList.addItem(txt)
            self.fileOrFolderEdit.clear()
        row = self.fileOrFolderList.currentRow()
        self.on_fileOrFolderList_currentRowChanged(row)

    @pyqtSlot(str)
    def on_fileOrFolderEdit_textChanged(self, txt):
        """
        Private slot to handle the textChanged signal of the directory edit.
        
        @param txt the text of the directory edit (string)
        """
        self.addFileOrFolderButton.setEnabled(txt != "")

    @pyqtSlot()
    def on_deleteSelectedButton_clicked(self):
        """
        Private slot to delete the selected entry from the list view.
        """
        row = self.fileOrFolderList.currentRow()
        itm = self.fileOrFolderList.takeItem(row)
        del itm
        row = self.fileOrFolderList.currentRow()
        self.on_fileOrFolderList_currentRowChanged(row)

    @pyqtSlot()
    def on_selectFileOrFolderButton_clicked(self):
        """
        Private slot to select files or folders.
        
        It displays a file and directory selection dialog to
        select the files and directorys which should copied into
        the distribution folder..
        """
        items = DirFileDialog.getOpenFileNames(
            None,
            self.trUtf8("Select files and folders"))

        for itm in items:
            itm = self.project.getRelativePath(itm)
            self.fileOrFolderList.addItem(Utilities.toNativeSeparators(itm))
        row = self.fileOrFolderList.currentRow()
        self.on_fileOrFolderList_currentRowChanged(row)

    def accept(self):
        """
        Protected slot called by the Ok button.
        
        It saves the values in the parameters dictionary.
        """
        # get data of general tab
        self.parameters['targetDirectory'] = self.targetDirEdit.text()
        self.parameters['targetName'] = self.targetNameEdit.text()
        self.parameters['baseName'] = self.basenameCombo.currentText()
        self.parameters['initScript'] = self.initscriptCombo.currentText()
        self.parameters['applicationIcon'] = self.applicationIconEdit.text()
        self.parameters['script'] = self.cxfreezeExecCombo.currentText()
        self.parameters['keepPath'] = self.keeppathCheckBox.isChecked()
        self.parameters['compress'] = self.compressCheckBox.isChecked()
        if self.nooptimizeRadioButton.isChecked():
            self.parameters['optimize'] = 0
        elif self.optimizeRadioButton.isChecked():
            self.parameters['optimize'] = 1
        else:
            self.parameters['optimize'] = 2
        
        # get data of advanced tab
        self.parameters['defaultPath'] = \
            self.__splitIt(self.defaultPathEdit.text(), os.pathsep)
        self.parameters['includePath'] = \
            self.__splitIt(self.includePathEdit.text(), os.pathsep)
        self.parameters['replacePaths'] = \
            self.__splitIt(self.replacePathsEdit.text(), os.pathsep)
        self.parameters['includeModules'] = \
            self.__splitIt(self.includeModulesEdit.text(), ',')
        self.parameters['excludeModules'] = \
            self.__splitIt(self.excludeModulesEdit.text(), ',')
        self.parameters['extListFile'] = self.extListFileEdit.text()
        
        # get data of the additional files tab
        additionalFiles = [self.fileOrFolderList.item(x).text()
                           for x in range(self.fileOrFolderList.count())]
        self.parameters['additionalFiles'] = additionalFiles

        # call the accept slot of the base class
        QDialog.accept(self)

    def __splitIt(self, s, sep):
        """
        Private method to split a string observing various conditions.
        
        @param s string to split (string)
        @param sep separator string (string)
        @return list of split values
        """
        if s == "" or s is None:
            return []
        
        if s.endswith(sep):
            s = s[:-1]
        
        return s.split(sep)
