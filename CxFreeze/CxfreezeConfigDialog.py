# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2011 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for cxfreeze.
"""

import sys
import os
import copy

from PyQt4.QtCore import pyqtSlot, QDir
from PyQt4.QtGui import QDialog, QFileDialog

from E5Gui.E5Completers import E5FileCompleter, E5DirCompleter

from .Ui_CxfreezeConfigDialog import Ui_CxfreezeConfigDialog

import Utilities

class CxfreezeConfigDialog(QDialog, Ui_CxfreezeConfigDialog):
    """
    Class implementing a dialog to enter the parameters for cxfreeze.
    """
    def __init__(self, project, exe, parms = None, parent = None):
        """
        Constructor
        
        @param project reference to the project object (Project.Project)
        @param exe name of the cxfreeze executable (string)
        @param parms parameters to set in the dialog
        @param parent parent widget of this dialog (QWidget)
        """
        QDialog.__init__(self, parent)
        self.setupUi(self)
        
        self.__initializeDefaults()
        
        # get a copy of the defaults to store the user settings
        self.parameters = copy.deepcopy(self.defaults)
        
        # combine it with the values of parms
        if parms is not None:
            for key, value in parms.items():
                if key in self.parameters:
                    self.parameters[key] = parms[key]
        
        self.project = project
        
        self.exe = exe
        
        # version specific setup
        modpath = None
        if "cxfreeze" in self.exe:
            for sysPath in sys.path:
                modpath = os.path.join(sysPath, "cx_Freeze")
                if os.path.exists(modpath):
                    break
        
        # populate combo boxes
        if modpath:
            d = QDir(os.path.join(modpath, 'bases'))
            basesList = d.entryList(QDir.Filters(QDir.Files))
            if sys.platform == "win32":
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
            self.basenameCombo.addItems(basesList)
            
            d = QDir(os.path.join(modpath, 'initscripts'))
            initList = d.entryList(['*.py'])
            initList.insert(0, '')
            self.initscriptCombo.addItems(initList)
        
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
        self.defaultPathEdit.setText(os.pathsep.join(self.parameters['defaultPath']))
        self.includePathEdit.setText(os.pathsep.join(self.parameters['includePath']))
        self.replacePathsEdit.setText(os.pathsep.join(self.parameters['replacePaths']))
        self.includeModulesEdit.setText(','.join(self.parameters['includeModules']))
        self.excludeModulesEdit.setText(','.join(self.parameters['excludeModules']))
        self.extListFileEdit.setText(self.parameters['extListFile'])
    
    def __initializeDefaults(self):
        """
        Private method to set the default values. 
        
        These are needed later on to generate the commandline parameters.
        """
        self.defaults = {
            # general options
            'targetDirectory' : '',
            'targetName' : '',
            'baseName' : '',
            'initScript' : '',
            'applicationIcon' : '',
            'keepPath' : False,
            'compress' : False, 
            'optimize' : 0,     # 0, 1 or 2
            
            # advanced options
            'defaultPath' : [],
            'includePath' : [],
            'replacePaths' : [],
            'includeModules' : [],
            'excludeModules' : [],
            'extListFile' : '',
        }
    
    def generateParameters(self):
        """
        Public method that generates the commandline parameters.
        
        It generates a list of strings to be used to set the QProcess arguments 
        for the cxfreeze call and a list containing the non default parameters. 
        The second list can be passed back upon object generation to overwrite
        the default settings.
        
        @return a tuple of the commandline parameters and non default parameters
            (list of strings, dictionary)
        """
        parms = {}
        args = []
        
        # 1. the program name
        args.append(self.exe)
        
        # 2. the commandline options
        # 2.1 general options
        if self.parameters['targetDirectory'] != self.defaults['targetDirectory']:
            parms['targetDirectory'] = self.parameters['targetDirectory']
            args.append('--target-dir={0}'.format(self.parameters['targetDirectory']))
        if self.parameters['targetName'] != self.defaults['targetName']:
            parms['targetName'] = self.parameters['targetName'][:]
            args.append('--target-name={0}'.format(self.parameters['targetName']))
        if self.parameters['baseName'] != self.defaults['baseName']:
            parms['baseName'] = self.parameters['baseName'][:]
            args.append('--base-name={0}'.format(self.parameters['baseName']))
        if self.parameters['initScript'] != self.defaults['initScript']:
            parms['initScript'] = self.parameters['initScript'][:]
            args.append('--init-script={0}'.format(self.parameters['initScript']))
        if self.parameters['applicationIcon'] != self.defaults['applicationIcon']:
            parms['applicationIcon'] = self.parameters['applicationIcon'][:]
            args.append('--icon={0}'.format(self.parameters['applicationIcon']))
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
        if self.parameters['includeModules'] != self.defaults['includeModules']:
            parms['includeModules'] = self.parameters['includeModules'][:]
            args.append('--include-modules={0}'.format(
                        ','.join(self.parameters['includeModules'])))
        if self.parameters['excludeModules'] != self.defaults['excludeModules']:
            parms['excludeModules'] = self.parameters['excludeModules'][:]
            args.append('--exclude-modules={0}'.format(
                        ','.join(self.parameters['excludeModules'])))
        if self.parameters['extListFile'] != self.defaults['extListFile']:
            parms['extListFile'] = self.parameters['extListFile']
            args.append('--ext-list-file={0}'.format(self.parameters['extListFile']))
        
        return (args, parms)

    @pyqtSlot()
    def on_extListFileButton_clicked(self):
        """
        Private slot to select the external list file.
        
        It displays a file selection dialog to select the external list file,
        the list of include modules is written to.
        """
        extList = QFileDialog.getOpenFileName(
            self,
            self.trUtf8("Select external list file"),
            self.extListFileEdit.text(),
            "",
            QFileDialog.DontUseNativeDialog)
        
        if extList:
            # make it relative, if it is in a subdirectory of the project path 
            lf = Utilities.toNativeSeparators(extList)
            lf = self.project.getRelativePath(lf)
            self.extListFileEdit.setText(lf)
    
    @pyqtSlot()
    def on_targetDirButton_clicked(self):
        """
        Private slot to select the target directory.
        
        It displays a directory selection dialog to
        select the directory the files are written to.
        """
        directory = QFileDialog.getExistingDirectory(
            self,
            self.trUtf8("Select target directory"),
            self.targetDirEdit.text(),
            QFileDialog.Options(QFileDialog.ShowDirsOnly |
                                QFileDialog.DontUseNativeDialog))
        
        if directory:
            # make it relative, if it is a subdirectory of the project path 
            dn = Utilities.toNativeSeparators(directory)
            dn = self.project.getRelativePath(dn)
            while dn.endswith(os.sep):
                dn = dn[:-1]
            self.targetDirEdit.setText(dn)
    
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
