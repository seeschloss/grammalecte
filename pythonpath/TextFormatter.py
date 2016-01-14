# -*- coding: utf8 -*-
# Text Formatter
# by Olivier R.
# License: MPL 2

import unohelper
import uno
import sys
import os
import traceback
import time

if sys.version_info.major == 3:
    import imp

import tf_strings
import tf_options


from com.sun.star.task import XJobExecutor
from com.sun.star.awt import XActionListener


from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK
# BUTTONS_OK, BUTTONS_OK_CANCEL, BUTTONS_YES_NO, BUTTONS_YES_NO_CANCEL, BUTTONS_RETRY_CANCEL, BUTTONS_ABORT_IGNORE_RETRY
# DEFAULT_BUTTON_OK, DEFAULT_BUTTON_CANCEL, DEFAULT_BUTTON_RETRY, DEFAULT_BUTTON_YES, DEFAULT_BUTTON_NO, DEFAULT_BUTTON_IGNORE
from com.sun.star.awt.MessageBoxType import INFOBOX # MESSAGEBOX, INFOBOX, WARNINGBOX, ERRORBOX, QUERYBOX

def MessageBox (xParentWin, sMsg, sTitle, nBoxType=INFOBOX, nBoxButtons=BUTTONS_OK):
    ctx = uno.getComponentContext()
    xToolkit = ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Toolkit", ctx) 
    xMsgBox = xToolkit.createMessageBox(xParentWin, nBoxType, nBoxButtons, sTitle, sMsg)
    return xMsgBox.execute()


class TextFormatter (unohelper.Base, XActionListener, XJobExecutor):
    def __init__ (self, ctx):
        self.ctx = ctx
        self.xSvMgr = self.ctx.ServiceManager
        self.xContainer = None
        self.xDialog = None

    # XJobExecutor
    def trigger (self, args):
        try:
            xTF = TextFormatter(self.ctx)
            xTF.run()
        except:
            traceback.print_exc()

    def _addWidget (self, name, wtype, x, y, w, h, **kwargs):
        xWidget = self.xDialog.createInstance('com.sun.star.awt.UnoControl%sModel' % wtype)
        xWidget.Name = name
        xWidget.PositionX = x
        xWidget.PositionY = y
        xWidget.Width = w
        xWidget.Height = h
        for k, w in kwargs.items():
            setattr(xWidget, k, w)
        self.xDialog.insertByName(name, xWidget)
        return xWidget

    def run (self, sLang):
        self.dUI = tf_strings.getUI(sLang)

        ## dialog
        self.xDialog = self.xSvMgr.createInstanceWithContext('com.sun.star.awt.UnoControlDialogModel', self.ctx)
        self.xDialog.Width = 320
        self.xDialog.Title = self.dUI.get('title', "#title#")

        xFD1 = uno.createUnoStruct("com.sun.star.awt.FontDescriptor")
        xFD1.Height = 12
        xFD1.Name = "Verdana"
        
        xFD2 = uno.createUnoStruct("com.sun.star.awt.FontDescriptor")
        xFD2.Height = 10
        xFD2.Weight = uno.getConstantByName("com.sun.star.awt.FontWeight.BOLD")
        xFD2.Name = "Verdana"
        
        xFDsmall = uno.createUnoStruct("com.sun.star.awt.FontDescriptor")
        xFDsmall.Height = 6
        xFDsmall.Name = "Verdana"

        ## widgets
        nGroupBoxWith = (self.xDialog.Width - 15) // 2
        nWidth = nGroupBoxWith-10
        nWidthHalf = (nWidth // 2) - 10
        nHeight = 10
        nColor = 0xAA2200
        
        # close or apply
        self.bClose = False

        # group box // surnumerary spaces
        x = 10; y = 5
        nPosRes = nGroupBoxWith - 22
        gbm1 = self._addWidget('groupbox1', 'GroupBox', x-5, y, nGroupBoxWith, 90, Label = "  " * len(self.dUI.get('ssp', "#err")), FontDescriptor = xFD1)
        self.ssp = self._addWidget('ssp', 'CheckBox', x, y+2, nWidth, nHeight, Label = self.dUI.get('ssp', "#err"), FontDescriptor = xFD1, \
                                   FontRelief = 1, TextColor = nColor, State = True)
        self.ssp1 = self._addWidget('ssp1', 'CheckBox', x, y+15, nWidth, nHeight, Label = self.dUI.get('ssp1', "#err"), State = True)
        self.ssp2 = self._addWidget('ssp2', 'CheckBox', x, y+25, nWidth, nHeight, Label = self.dUI.get('ssp2', "#err"), State = True)
        self.ssp3 = self._addWidget('ssp3', 'CheckBox', x, y+35, nWidth, nHeight, Label = self.dUI.get('ssp3', "#err"), State = True)
        self.ssp4 = self._addWidget('ssp4', 'CheckBox', x, y+45, nWidth, nHeight, Label = self.dUI.get('ssp4', "#err"), State = True)
        self.ssp5 = self._addWidget('ssp5', 'CheckBox', x, y+55, nWidth, nHeight, Label = self.dUI.get('ssp5', "#err"), State = True)
        self.ssp6 = self._addWidget('ssp6', 'CheckBox', x, y+65, nWidth, nHeight, Label = self.dUI.get('ssp6', "#err"), State = True)
        self.ssp7 = self._addWidget('ssp7', 'CheckBox', x, y+75, nWidth, nHeight, Label = self.dUI.get('ssp7', "#err"), State = True)
        self.ssp1_res = self._addWidget('ssp1_res', 'FixedText', nPosRes, y+15, 20, nHeight, Label = "", Align = 2)
        self.ssp2_res = self._addWidget('ssp2_res', 'FixedText', nPosRes, y+25, 20, nHeight, Label = "", Align = 2)
        self.ssp3_res = self._addWidget('ssp3_res', 'FixedText', nPosRes, y+35, 20, nHeight, Label = "", Align = 2)
        self.ssp4_res = self._addWidget('ssp4_res', 'FixedText', nPosRes, y+45, 20, nHeight, Label = "", Align = 2)
        self.ssp5_res = self._addWidget('ssp5_res', 'FixedText', nPosRes, y+55, 20, nHeight, Label = "", Align = 2)
        self.ssp6_res = self._addWidget('ssp6_res', 'FixedText', nPosRes, y+65, 20, nHeight, Label = "", Align = 2)
        self.ssp7_res = self._addWidget('ssp7_res', 'FixedText', nPosRes, y+75, 20, nHeight, Label = "", Align = 2)

        # group box // missing spaces
        x = 10; y = 100
        gbm2 = self._addWidget('groupbox2', 'GroupBox', x-5, y, nGroupBoxWith, 40, Label = "  " * len(self.dUI.get('space', "#err")), FontDescriptor = xFD1)
        self.space = self._addWidget('space', 'CheckBox', x, y+2, nWidth, nHeight, Label = self.dUI.get('space', "#err"), FontDescriptor = xFD1, \
                                     FontRelief = 1, TextColor = nColor, State = True)
        self.space1 = self._addWidget('space1', 'CheckBox', x, y+15, nWidth, nHeight, Label = self.dUI.get('space1', "#err"), State = True)
        self.space2 = self._addWidget('space2', 'CheckBox', x, y+25, nWidth, nHeight, Label = self.dUI.get('space2', "#err"), State = True)
        self.space1_res = self._addWidget('space1_res', 'FixedText', nPosRes, y+15, 20, nHeight, Label = "", Align = 2)
        self.space2_res = self._addWidget('space2_res', 'FixedText', nPosRes, y+25, 20, nHeight, Label = "", Align = 2)
        
        # group box // non-breaking spaces
        x = 10; y = 145
        gbm3 = self._addWidget('groupbox3', 'GroupBox', x-5, y, nGroupBoxWith, 70, Label = "  " * len(self.dUI.get('nbsp', "#err")), FontDescriptor = xFD1)
        self.nbsp = self._addWidget('nbsp', 'CheckBox', x, y+2, nWidth, nHeight, Label = self.dUI.get('nbsp', "#err"), FontDescriptor = xFD1, \
                                    FontRelief = 1, TextColor = nColor, State = True)
        self.nbsp1 = self._addWidget('nbsp1', 'CheckBox', x, y+15, 85, nHeight, Label = self.dUI.get('nbsp1', "#err"), State = True)
        self.nbsp2 = self._addWidget('nbsp2', 'CheckBox', x, y+25, 85, nHeight, Label = self.dUI.get('nbsp2', "#err"), State = True)
        self.nbsp3 = self._addWidget('nbsp3', 'CheckBox', x, y+35, nWidth, nHeight, Label = self.dUI.get('nbsp3', "#err"), State = True)
        self.nbsp4 = self._addWidget('nbsp4', 'CheckBox', x, y+45, 85, nHeight, Label = self.dUI.get('nbsp4', "#err"), State = True)
        self.nbsp5 = self._addWidget('nbsp5', 'CheckBox', x, y+55, 85, nHeight, Label = self.dUI.get('nbsp5', "#err"), State = True)
        self.nnbsp1 = self._addWidget('nnbsp1', 'CheckBox', x+85, y+15, 30, nHeight, Label = self.dUI.get('nnbsp', "#err"), State = False)
        self.nnbsp2 = self._addWidget('nnbsp2', 'CheckBox', x+85, y+25, 30, nHeight, Label = self.dUI.get('nnbsp', "#err"), State = False)
        self.nnbsp4 = self._addWidget('nnbsp4', 'CheckBox', x+85, y+45, 30, nHeight, Label = self.dUI.get('nnbsp', "#err"), State = False)
        self.nbsp1_res = self._addWidget('nbsp1_res', 'FixedText', nPosRes, y+15, 20, nHeight, Label = "", Align = 2)
        self.nbsp2_res = self._addWidget('nbsp2_res', 'FixedText', nPosRes, y+25, 20, nHeight, Label = "", Align = 2)
        self.nbsp3_res = self._addWidget('nbsp3_res', 'FixedText', nPosRes, y+35, 20, nHeight, Label = "", Align = 2)
        self.nbsp4_res = self._addWidget('nbsp4_res', 'FixedText', nPosRes, y+45, 20, nHeight, Label = "", Align = 2)
        self.nbsp5_res = self._addWidget('nbsp5_res', 'FixedText', nPosRes, y+55, 20, nHeight, Label = "", Align = 2)
        
        # group box // deletion
        x = 10; y = 220
        gbm7 = self._addWidget('groupbox7', 'GroupBox', x-5, y, nGroupBoxWith, 50, Label = "  " * len(self.dUI.get('delete', "#err")), FontDescriptor = xFD1)
        self.delete = self._addWidget('delete', 'CheckBox', x, y+2, nWidth, nHeight, Label = self.dUI.get('delete', "#err"), FontDescriptor = xFD1, \
                                      FontRelief = 1, TextColor = nColor, State = True)
        self.delete1 = self._addWidget('delete1', 'CheckBox', x, y+15, nWidth, nHeight, Label = self.dUI.get('delete1', "#err"), State = True)
        self.delete2 = self._addWidget('delete2', 'CheckBox', x, y+25, nWidth, nHeight, Label = self.dUI.get('delete2', "#err"), State = True)
        self.delete2a = self._addWidget('delete2a', 'RadioButton', x+10, y+35, 50, nHeight, Label = self.dUI.get('delete2a', "#"))
        self.delete2b = self._addWidget('delete2b', 'RadioButton', x+60, y+35, 60, nHeight, Label = self.dUI.get('delete2b', "#"), State = True)
        self.delete2c = self._addWidget('delete2c', 'RadioButton', x+120, y+35, 40, nHeight, Label = self.dUI.get('delete2c', "#"), \
                                        HelpText = self.dUI.get('delete2c_help', "#err"))
        self.delete1_res = self._addWidget('delete1_res', 'FixedText', nPosRes, y+15, 20, nHeight, Label = "", Align = 2)
        self.delete2_res = self._addWidget('delete2_res', 'FixedText', nPosRes, y+25, 20, nHeight, Label = "", Align = 2)

        # group box // typographical marks
        x = 168; y = 5
        nPosRes = x + nGroupBoxWith - 32
        gbm4 = self._addWidget('groupbox4', 'GroupBox', x-5, y, nGroupBoxWith, 130, Label = "  " * len(self.dUI.get('typo', "#err")), FontDescriptor = xFD1)
        self.typo = self._addWidget('typo', 'CheckBox', x, y+2, nWidth, nHeight, Label = self.dUI.get('typo', "#err"), FontDescriptor = xFD1, \
                                    FontRelief = 1, TextColor = nColor, State = True)
        self.typo1 = self._addWidget('typo1', 'CheckBox', x, y+15, nWidth, nHeight, Label = self.dUI.get('typo1', "#err"), State = True)
        self.typo2 = self._addWidget('typo2', 'CheckBox', x, y+25, nWidth, nHeight, Label = self.dUI.get('typo2', "#err"), State = True)
        self.typo3 = self._addWidget('typo3', 'CheckBox', x, y+35, nWidth, nHeight, Label = self.dUI.get('typo3', "#err"), State = True)
        self.typo3a = self._addWidget('typo3a', 'RadioButton', x+10, y+45, nWidthHalf, nHeight, Label = self.dUI.get('emdash', "#err"))
        self.typo3b = self._addWidget('typo3b', 'RadioButton', x+70, y+45, nWidthHalf, nHeight, Label = self.dUI.get('endash', "#err"), State = True)
        self.typo4 = self._addWidget('typo4', 'CheckBox', x, y+55, nWidth, nHeight, Label = self.dUI.get('typo4', "#err"), State = True)
        self.typo4a = self._addWidget('typo4a', 'RadioButton', x+10, y+65, nWidthHalf, nHeight, Label = self.dUI.get('emdash', "#err"), State = True)
        self.typo4b = self._addWidget('typo4b', 'RadioButton', x+70, y+65, nWidthHalf, nHeight, Label = self.dUI.get('endash', "#err"))
        self.typo5 = self._addWidget('typo5', 'CheckBox', x, y+75, nWidth, nHeight, Label = self.dUI.get('typo5', "#err"), State = True)
        self.typo6 = self._addWidget('typo6', 'CheckBox', x, y+85, nWidth, nHeight, Label = self.dUI.get('typo6', "#err"), State = True)
        self.typo7 = self._addWidget('typo7', 'CheckBox', x, y+95, nWidth, nHeight, Label = self.dUI.get('typo7', "#err"), State = True)
        self.typo8 = self._addWidget('typo8', 'CheckBox', x, y+105, 35, nHeight, Label = self.dUI.get('typo8', "#err"), \
                                     HelpText = self.dUI.get('typo8_help', "#err"), State = True)
        self.typo8a = self._addWidget('typo8a', 'RadioButton', x+45, y+105, 30, nHeight, Label = self.dUI.get('typo8a', "#err"))
        self.typo8b = self._addWidget('typo8b', 'RadioButton', x+75, y+105, 35, nHeight, Label = self.dUI.get('typo8b', "#err"), State = True)
        self.typo_ff = self._addWidget('typo_ff', 'CheckBox', x+10, y+115, 18, nHeight, Label = self.dUI.get('typo_ff', "#err"), State = True)
        self.typo_fi = self._addWidget('typo_fi', 'CheckBox', x+28, y+115, 18, nHeight, Label = self.dUI.get('typo_fi', "#err"), State = True)
        self.typo_ffi = self._addWidget('typo_ffi', 'CheckBox', x+46, y+115, 20, nHeight, Label = self.dUI.get('typo_ffi', "#err"), State = True)
        self.typo_fl = self._addWidget('typo_fl', 'CheckBox', x+66, y+115, 18, nHeight, Label = self.dUI.get('typo_fl', "#err"), State = True)
        self.typo_ffl = self._addWidget('typo_ffl', 'CheckBox', x+84, y+115, 20, nHeight, Label = self.dUI.get('typo_ffl', "#err"), State = True)
        self.typo_ft = self._addWidget('typo_ft', 'CheckBox', x+104, y+115, 18, nHeight, Label = self.dUI.get('typo_ft', "#err"), State = True)
        self.typo_st = self._addWidget('typo_st', 'CheckBox', x+122, y+115, 18, nHeight, Label = self.dUI.get('typo_st', "#err"), State = True)
        self.typo1_res = self._addWidget('typo1_res', 'FixedText', nPosRes, y+15, 20, nHeight, Label = "", Align = 2)
        self.typo2_res = self._addWidget('typo2_res', 'FixedText', nPosRes, y+25, 20, nHeight, Label = "", Align = 2)
        self.typo3_res = self._addWidget('typo3_res', 'FixedText', nPosRes, y+35, 20, nHeight, Label = "", Align = 2)
        self.typo4_res = self._addWidget('typo4_res', 'FixedText', nPosRes, y+55, 20, nHeight, Label = "", Align = 2)
        self.typo5_res = self._addWidget('typo5_res', 'FixedText', nPosRes, y+75, 20, nHeight, Label = "", Align = 2)
        self.typo6_res = self._addWidget('typo6_res', 'FixedText', nPosRes, y+85, 20, nHeight, Label = "", Align = 2)
        self.typo7_res = self._addWidget('typo7_res', 'FixedText', nPosRes, y+95, 20, nHeight, Label = "", Align = 2)
        self.typo8_res = self._addWidget('typo8_res', 'FixedText', nPosRes, y+105, 20, nHeight, Label = "", Align = 2)
        

        # group box // misc.
        x = 168; y = 140
        gbm5 = self._addWidget('groupbox5', 'GroupBox', x-5, y, nGroupBoxWith, 70, Label = "  " * len(self.dUI.get('misc', "#err")), FontDescriptor = xFD1)
        self.misc = self._addWidget('misc', 'CheckBox', x, y+2, nWidth, nHeight, Label = self.dUI.get('misc', "#err"), FontDescriptor = xFD1, \
                                    FontRelief = 1, TextColor = nColor, State = True)
        self.misc1 = self._addWidget('misc1', 'CheckBox', x, y+15, 80, nHeight, Label = self.dUI.get('misc1', "#err"), State = True)
        self.misc1a = self._addWidget('misc1a', 'CheckBox', x+80, y+15, 30, nHeight, Label = self.dUI.get('misc1a', "#err"), State = True)
        self.misc2 = self._addWidget('misc2', 'CheckBox', x, y+25, nWidth, nHeight, Label = self.dUI.get('misc2', "#err"), State = True)
        self.misc3 = self._addWidget('misc3', 'CheckBox', x, y+35, nWidth, nHeight, Label = self.dUI.get('misc3', "#err"), State = True)
        #self.misc4 = self._addWidget('misc4', 'CheckBox', x, y+45, nWidth, nHeight, Label = self.dUI.get('misc4', "#err"), State = True)
        self.misc5 = self._addWidget('misc5', 'CheckBox', x, y+45, nWidth, nHeight, Label = self.dUI.get('misc5', "#err"), State = True)
        self.misc5b = self._addWidget('misc5b', 'CheckBox', x+10, y+55, nWidth-40, nHeight, Label = self.dUI.get('misc5b', "#err"), State = False)
        self.misc5c = self._addWidget('misc5c', 'CheckBox', x+nWidth-25, y+55, 30, nHeight, Label = self.dUI.get('misc5c', "#err"), State = False)
        self.misc1_res = self._addWidget('misc1_res', 'FixedText', nPosRes, y+15, 20, nHeight, Label = "", Align = 2)
        self.misc2_res = self._addWidget('misc2_res', 'FixedText', nPosRes, y+25, 20, nHeight, Label = "", Align = 2)
        self.misc3_res = self._addWidget('misc3_res', 'FixedText', nPosRes, y+35, 20, nHeight, Label = "", Align = 2)
        #self.misc4_res = self._addWidget('misc4_res', 'FixedText', nPosRes, y+45, 20, nHeight, Label = "", Align = 2)
        self.misc5_res = self._addWidget('misc5_res', 'FixedText', nPosRes, y+45, 20, nHeight, Label = "", Align = 2)
        
        # group box // restructuration
        x = 168; y = 215
        gbm6 = self._addWidget('groupbox6', 'GroupBox', x-5, y, nGroupBoxWith, 50, Label = "  " * len(self.dUI.get('struct', "#err")), FontDescriptor = xFD1)
        self.struct = self._addWidget('struct', 'CheckBox', x, y+2, nWidth, nHeight, Label = self.dUI.get('struct', "#err"), FontDescriptor = xFD1, \
                                      FontRelief = 1, TextColor = nColor, HelpText = self.dUI.get('struct_help', "#err"), State = False)
        self.struct1 = self._addWidget('struct1', 'CheckBox', x, y+15, nWidth, nHeight, Label = self.dUI.get('struct1', "#err"), State = True, Enabled = False)
        self.struct2 = self._addWidget('struct2', 'CheckBox', x, y+25, nWidth, nHeight, Label = self.dUI.get('struct2', "#err"), State = True, Enabled = False)
        self.struct3 = self._addWidget('struct3', 'CheckBox', x, y+35, nWidth, nHeight, Label = self.dUI.get('struct3', "#err"), \
                                       HelpText = self.dUI.get('struct3_help', "#err"), State = False, Enabled = False)
        self.struct1_res = self._addWidget('struct1_res', 'FixedText', nPosRes, y+15, 20, nHeight, Label = "", Align = 2)
        self.struct2_res = self._addWidget('struct2_res', 'FixedText', nPosRes, y+25, 20, nHeight, Label = "", Align = 2)
        self.struct3_res = self._addWidget('struct3_res', 'FixedText', nPosRes, y+35, 20, nHeight, Label = "", Align = 2)
        
        # dialog height
        self.xDialog.Height = 292

        # lists of checkbox widgets
        self.dCheckboxWidgets = {
            "ssp":      [self.ssp1, self.ssp2, self.ssp3, self.ssp4, self.ssp5, self.ssp6, self.ssp7],
            "space":    [self.space1, self.space2],
            "nbsp":     [self.nbsp1, self.nbsp2, self.nbsp3, self.nbsp4, self.nbsp5, self.nnbsp1, self.nnbsp2, self.nnbsp4],
            "delete":   [self.delete1, self.delete2, self.delete2a, self.delete2b, self.delete2c],
            "typo":     [self.typo1, self.typo2, self.typo3, self.typo3a, self.typo3b, self.typo4, self.typo4a, self.typo4b, self.typo5, self.typo6, \
                         self.typo7, self.typo8, self.typo8a, self.typo8b, self.typo_ff, self.typo_fi, self.typo_ffi, self.typo_fl, self.typo_ffl, \
                         self.typo_ft, self.typo_st],
            "misc":     [self.misc1, self.misc2, self.misc3, self.misc5, self.misc1a, self.misc5b, self.misc5c], #self.misc4, 
            "struct":   [self.struct1, self.struct2, self.struct3]
        }

        # progress bar
        self.pbar = self._addWidget('pbar', 'ProgressBar', 22, self.xDialog.Height-16, 215, 10)
        self.pbar.ProgressValueMin = 0
        self.pbar.ProgressValueMax = 31
        # time counter
        self.time_res = self._addWidget('time_res', 'FixedText', self.xDialog.Width-80, self.xDialog.Height-15, 20, nHeight, Label = "", Align = 2)

        # buttons
        self.bdefault = self._addWidget('default', 'Button', 5, self.xDialog.Height-19, 15, 15, Label = self.dUI.get('default', "#err"), \
                                        HelpText = self.dUI.get('default_help', "#err"), FontDescriptor = xFD2, TextColor = 0x444444)
        #self.bsel = self._addWidget('bsel', 'CheckBox', x, self.xDialog.Height-40, nWidth-55, nHeight, Label = self.dUI.get('bsel', "#err"))        
        self.bapply = self._addWidget('apply', 'Button', self.xDialog.Width-55, self.xDialog.Height-19, 50, 15, Label = self.dUI.get('apply', "#err"), \
                                      FontDescriptor = xFD2, TextColor = 0x004400)
        self.binfo = self._addWidget('info', 'Button', self.xDialog.Width-15, 0, 10, 9, Label = self.dUI.get('info', "#err"), \
                                     HelpText = self.dUI.get('infotitle', "#err"), FontDescriptor = xFDsmall, TextColor = 0x444444)

        # load configuration
        self._loadConfig()

        ## container
        self.xContainer = self.xSvMgr.createInstanceWithContext('com.sun.star.awt.UnoControlDialog', self.ctx)
        self.xContainer.setModel(self.xDialog)
        self.xContainer.setVisible(False)
        self.xContainer.getControl('info').addActionListener(self)
        self.xContainer.getControl('info').setActionCommand('Info')
        self.xContainer.getControl('default').addActionListener(self)
        self.xContainer.getControl('default').setActionCommand('Default')
        self.xContainer.getControl('apply').addActionListener(self)
        self.xContainer.getControl('apply').setActionCommand('Apply')
        self.xContainer.getControl('ssp').addActionListener(self)
        self.xContainer.getControl('ssp').setActionCommand('SwitchSsp')
        self.xContainer.getControl('space').addActionListener(self)
        self.xContainer.getControl('space').setActionCommand('SwitchSpace')
        self.xContainer.getControl('nbsp').addActionListener(self)
        self.xContainer.getControl('nbsp').setActionCommand('SwitchNbsp')
        self.xContainer.getControl('delete').addActionListener(self)
        self.xContainer.getControl('delete').setActionCommand('SwitchDelete')
        self.xContainer.getControl('typo').addActionListener(self)
        self.xContainer.getControl('typo').setActionCommand('SwitchTypo')
        self.xContainer.getControl('misc').addActionListener(self)
        self.xContainer.getControl('misc').setActionCommand('SwitchMisc')
        self.xContainer.getControl('struct').addActionListener(self)
        self.xContainer.getControl('struct').setActionCommand('SwitchStruct')
        xToolkit = self.xSvMgr.createInstanceWithContext('com.sun.star.awt.ExtToolkit', self.ctx)
        self.xContainer.createPeer(xToolkit, None)
        self.xContainer.execute()
    
    # XActionListener
    def actionPerformed (self, xActionEvent):
        try:
            if xActionEvent.ActionCommand == 'Apply':
                if self.bClose:
                    self.xContainer.endExecute()
                else:
                    xDesktop = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
                    xElem = xDesktop.getCurrentComponent()

                    # Writer
                    if True:
                        # no selection
                        self._saveConfig()
                        self._replaceAll(xElem)
                    else:
                        # modify selected text only
                        pass    
                        #xSelecList = xDoc.getCurrentSelection()
                        #xSel = xSelecList.getByIndex(0)

                    # Impress
                    # Note: impossible to format text on Impress right now as ReplaceDescriptors don’t accept regex!
                    #xPages = xElem.getDrawPages()
                    #for i in range(xPages.Count):
                    #    self._replaceAll(xPages.getByIndex(i))
                    #xPages = xElem.getMasterPages()
                    #for i in range(xPages.Count):
                    #    self._replaceAll(xPages.getByIndex(i))
                    self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'SwitchSsp':
                self._switchCheckBox(self.ssp)
                self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'SwitchSpace':
                self._switchCheckBox(self.space)
                self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'SwitchNbsp':
                self._switchCheckBox(self.nbsp)
                self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'SwitchDelete':
                self._switchCheckBox(self.delete)
                self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'SwitchTypo':
                self._switchCheckBox(self.typo)
                self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'SwitchMisc':
                self._switchCheckBox(self.misc)
                self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'SwitchStruct':
                self._switchCheckBox(self.struct)
                self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'Default':
                self._setConfig(tf_options.dDefaultOpt)
                self._setApplyButtonLabel()
            elif xActionEvent.ActionCommand == 'Info':
                xDesktop = self.xSvMgr.createInstanceWithContext('com.sun.star.frame.Desktop', self.ctx)
                xDoc = xDesktop.getCurrentComponent()
                xWindow = xDoc.CurrentController.Frame.ContainerWindow
                MessageBox (xWindow, self.dUI.get('infomsg', "#err"), self.dUI.get('infotitle', "#err"))
            else:
                print("Wrong command: " + xActionEvent.ActionCommand)
        except:
            traceback.print_exc()

    def _loadConfig (self):
        try:
            if sys.version_info.major == 3:
                imp.reload(tf_options)
            else:
                reload(tf_options)
            self._setConfig(tf_options.dOpt)
        except:
            traceback.print_exc()

    def _setConfig (self, d):
        try:
            for key, val in d.items():
                w = getattr(self, key)
                w.State = val
                if key in self.dCheckboxWidgets:
                    self._switchCheckBox(w)
        except:
            raise

    def _saveConfig (self):
        try:
            # create options dictionary
            dOpt = {}
            for key, lWidget in self.dCheckboxWidgets.items():
                w = getattr(self, key)
                dOpt[w.Name] = w.State
                for w in lWidget:
                    dOpt[w.Name] = w.State
            # get extension path
            xDefaultContext = self.ctx.ServiceManager.DefaultContext
            xPackageInfoProvider = xDefaultContext.getValueByName("/singletons/com.sun.star.deployment.PackageInformationProvider")
            sExtPath = xPackageInfoProvider.getPackageLocation("French.linguistic.resources.from.Dicollecte.by.OlivierR")
            sExtPath = sExtPath[8:] + "/pythonpath/tf_options.py"  # remove "file:///"
            sExtPath = os.path.abspath(sExtPath)
            # write file
            if os.path.isfile(sExtPath):
                hOpt = open(sExtPath, "w")
                hOpt.write("dDefaultOpt = " + str(tf_options.dDefaultOpt) + "\n")
                hOpt.write("dOpt = " + str(dOpt))
                hOpt.close()
        except:
            traceback.print_exc()

    def _switchCheckBox (self, wGroupCheckbox):
        for w in self.dCheckboxWidgets.get(wGroupCheckbox.Name, []):
            w.Enabled = wGroupCheckbox.State

    def _setApplyButtonLabel (self):
        if self.ssp.State or self.space.State or self.nbsp.State or self.delete.State or self.typo.State or self.misc.State or self.struct.State:
            self.bClose = False
            self.bapply.Label = self.dUI.get('apply', "#err")
            self.bapply.TextColor = 0x004400
        else:
            self.bClose = True
            self.bapply.Label = self.dUI.get('close', "#err")
            self.bapply.TextColor = 0x440000
        self.xContainer.setVisible(True)

    def _replaceAll (self, xElem):
        try:
            nStartTime = time.clock()
            self.xContainer.setVisible(True)
            # change pointer
            xPointer = self.ctx.ServiceManager.createInstanceWithContext("com.sun.star.awt.Pointer", self.ctx)
            xPointer.setType(uno.getConstantByName("com.sun.star.awt.SystemPointer.WAIT"))
            xWindowPeer = self.xContainer.getPeer()
            xWindowPeer.setPointer(xPointer)
            for x in xWindowPeer.Windows:
                x.setPointer(xPointer)
            # NOTE: A LOT OF REGEX COULD BE MERGED IF ICU ENGINE WAS NOT SO BUGGY
            # "([;?!…])(?=[:alnum:])" => "$1 " doesn’t work properly
            # "(?<=[:alnum:])([;?!…])" => " $1 " doesn’t work properly
            self.pbar.ProgressValue = 0
            # Restructuration
            if self.struct.State:
                if self.struct1.State:
                    n = self._replaceText(xElem, "\\n", "\\n", True) # end of line => end of paragraph
                    self.struct1_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.struct2.State:
                    n = self._replaceText(xElem, u"([:alpha:])- *\n([:alpha:])", u"$1$2", True)  # EOL
                    n += self._replaceHyphenAtEndOfParagraphs(xElem) # EOP
                    self.struct2_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.struct3.State:
                    n = self._mergeContiguousParagraphs(xElem)
                    self.struct3_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                self.struct.State = False
                self._switchCheckBox(self.struct)
            self.pbar.ProgressValue = 3
            # espaces surnuméraires
            if self.ssp.State:
                if self.ssp3.State:
                    n = self._replaceText(xElem, u"[  ]+$", "", True)
                    self.ssp3_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.ssp2.State:
                    n = self._replaceText(xElem, u"  ", u" ", False) # espace + espace insécable -> espace
                    n += self._replaceText(xElem, u"  ", u" ", False) # espace insécable + espace -> espace
                    n += self._replaceText(xElem, u"  +", u" ", True) # espaces surnuméraires
                    n += self._replaceText(xElem, u"  +", u" ", True) # espaces insécables surnuméraires
                    self.ssp2_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.ssp1.State:
                    n = self._replaceText(xElem, u"^[  ]+", "", True)
                    self.ssp1_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.ssp4.State:
                    n = self._replaceText(xElem, u" +(?=[.,…])", "", True)
                    self.ssp4_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.ssp5.State:
                    n = self._replaceText(xElem, u"\\([  ]+", u"(", True)
                    n += self._replaceText(xElem, u"[  ]+\\)", u")", True)
                    self.ssp5_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.ssp6.State:
                    n = self._replaceText(xElem, u"\\[[  ]+", u"[", True)
                    n += self._replaceText(xElem, u"[  ]+\\]", u"]", True)
                    self.ssp6_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.ssp7.State:
                    n = self._replaceText(xElem, u"“[  ]+", u"“", True)
                    n += self._replaceText(xElem, u"[  ]”", u"”", True)
                    self.ssp7_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                self.ssp.State = False
                self._switchCheckBox(self.ssp)
            self.pbar.ProgressValue = 10
            # espaces typographiques
            if self.nbsp.State:
                if self.nbsp1.State:
                    if self.nnbsp1.State:
                        # espaces insécables fines
                        n = self._replaceText(xElem, u"(?<=[:alnum:]);", u" ;", True)
                        n += self._replaceText(xElem, u"(?<=[:alnum:])[?]", u" ?", True)
                        n += self._replaceText(xElem, u"(?<=[:alnum:])!", u" !", True)
                        n += self._replaceText(xElem, u"(?<=[]…)»}]);", u" ;", True)
                        n += self._replaceText(xElem, u"(?<=[]…)»}])[?]", u" ?", True)
                        n += self._replaceText(xElem, u"(?<=[]…)»}])!", u" !", True)
                        n += self._replaceText(xElem, u"[  ]+([;?!])", u" $1", True)
                        n += self._replaceText(xElem, u"(?<=[:alnum:]):", u" :", True)
                        n += self._replaceText(xElem, u"(?<=[]…)»}]):", u" :", True)
                        n += self._replaceText(xElem, u"[  ]+:", u" :", True)
                    else:
                        # espaces insécables
                        n = self._replaceText(xElem, u"(?<=[:alnum:]):", u" :", True)
                        n += self._replaceText(xElem, u"(?<=[:alnum:]);", u" ;", True)
                        n += self._replaceText(xElem, u"(?<=[:alnum:])[?]", u" ?", True)
                        n += self._replaceText(xElem, u"(?<=[:alnum:])!", u" !", True)
                        n += self._replaceText(xElem, u"(?<=[]…)»}]):", u" :", True)
                        n += self._replaceText(xElem, u"(?<=[]…)»}]);", u" ;", True)
                        n += self._replaceText(xElem, u"(?<=[]…)»}])[?]", u" ?", True)
                        n += self._replaceText(xElem, u"(?<=[]…)»}])!", u" !", True)
                        n += self._replaceText(xElem, u"[  ]+([:;?!])", u" $1", True)
                    n -= self._replaceText(xElem, u"([[(])[   ]([!?:;])", u"$1$2", True)
                    n -= self._replaceText(xElem, u"(?<=http)[   ]:(?=//)", u":", True)
                    n -= self._replaceText(xElem, u"(?<=https)[   ]:(?=//)", u":", True)
                    n -= self._replaceText(xElem, u"(?<=ftp)[   ]:(?=//)", u":", True)
                    self.nbsp1_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.nbsp2.State:
                    if self.nnbsp2.State:
                        # espaces insécables fines
                        n = self._replaceText(xElem, u"«(?=[:alnum:])", u"« ", True)
                        n += self._replaceText(xElem, u"«[  ]+", u"« ", True)
                        n += self._replaceText(xElem, u"(?<=[:alnum:]|[.!?])»", u" »", True)
                        n += self._replaceText(xElem, u"[  ]+»", u" »", True)
                    else:
                        # espaces insécables
                        n = self._replaceText(xElem, u"«(?=[:alnum:])", u"« ", True)
                        n += self._replaceText(xElem, u"«[  ]+", u"« ", True)
                        n += self._replaceText(xElem, u"(?<=[:alnum:]|[.!?])»", u" »", True)
                        n += self._replaceText(xElem, u"[  ]+»", u" »", True)
                    self.nbsp2_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.nbsp3.State:
                    n = self._replaceText(xElem, u"([:digit:])([%‰€$£¥˚Ω℃])", u"$1 $2", True)
                    n += self._replaceText(xElem, u"([:digit:]) ([%‰€$£¥˚Ω℃])", u"$1 $2", True)
                    self.nbsp3_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.nbsp4.State:
                    if self.nnbsp4.State:
                        # espaces insécables fines
                        n = self._replaceText(xElem, u"([:digit:])[  ]([:digit:])", u"$1 $2", True)
                    else:
                        # espaces insécables
                        n = self._replaceText(xElem, u"([:digit:])[  ]([:digit:])", u"$1 $2", True)
                    self.nbsp4_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.nbsp5.State:
                    n = self._replaceText(xElem, u"(?<=[0-9⁰¹²³⁴⁵⁶⁷⁸⁹]) ?([kcmµn]?(?:[slgJKΩ]|m[²³]?|Wh?|Hz|dB)|[%‰]|°C)\\b", " $1", True, True)
                    self.nbsp5_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if False:
                    n = self._replaceText(xElem, u"\\b(MM?\\.|Mlle|Mgr) ", u"$1 ", True)
                    self.nbsp3_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                self.nbsp.State = False
                self._switchCheckBox(self.nbsp)
            self.pbar.ProgressValue = 15
            # espaces manquants
            if self.typo.State:
                if self.typo6.State:
                    n = self._replaceText(xElem, u"\\bN\\.([ms])\\b", u"N·$1", True, True) # N·m et N·m-1, N·s
                    n += self._replaceText(xElem, u"\\bW\\.h\\b", u"W·h", True, True)
                    n += self._replaceText(xElem, u"\\bPa\\.s\\b", u"Pa·s", True, True)
                    n += self._replaceText(xElem, u"\\bA\\.h\\b", u"A·h", True, True)
                    n += self._replaceText(xElem, u"\\bΩ\\.m\\b", u"Ω·m", True, True)
                    n += self._replaceText(xElem, u"\\bS\\.m\\b", u"S·m", True, True)
                    n += self._replaceText(xElem, u"\\bg\\.s(?=-1)\\b", u"g·s", True, True)
                    n += self._replaceText(xElem, u"\\bm\\.s(?=-[12])\\b", u"m·s", True, True)
                    n += self._replaceText(xElem, u"\\bg\\.m(?=2|-3)\\b", u"g·m", True, True)
                    n += self._replaceText(xElem, u"\\bA\\.m(?=-1)\\b", u"A·m", True, True)
                    n += self._replaceText(xElem, u"\\bJ\\.K(?=-1)\\b", u"J·K", True, True)
                    n += self._replaceText(xElem, u"\\bW\\.m(?=-2)\\b", u"W·m", True, True)
                    n += self._replaceText(xElem, u"\\bcd\\.m(?=-2)\\b", u"cd·m", True, True)
                    n += self._replaceText(xElem, u"\\bC\\.kg(?=-1)\\b", u"C·kg", True, True)
                    n += self._replaceText(xElem, u"\\bH\\.m(?=-1)\\b", u"H·m", True, True)
                    n += self._replaceText(xElem, u"\\bJ\\.kg(?=-1)\\b", u"J·kg", True, True)
                    n += self._replaceText(xElem, u"\\bJ\\.m(?=-3)\\b", u"J·m", True, True)
                    n += self._replaceText(xElem, u"\\bm[2²]\\.s\\b", u"m²·s", True, True)
                    n += self._replaceText(xElem, u"\\bm[3³]\\.s(?=-1)\\b", u"m³·s", True, True)
                    
                    #n += self._replaceText(xElem, u"\\bJ.kg-1.K-1\\b", u"J·kg-1·K-1", True, True)
                    #n += self._replaceText(xElem, u"\\bW.m-1.K-1\\b", u"W·m-1·K-1", True, True)
                    #n += self._replaceText(xElem, u"\\bW.m-2.K-1\\b", u"W·m-2·K-1", True, True)
                    n += self._replaceText(xElem, u"\\b(Y|Z|E|P|T|G|M|k|h|da|d|c|m|µ|n|p|f|a|z|y)Ω\\b", u"$1Ω", True, True)
                    self.typo6_res.Label = str(n)
                    self.pbar.ProgressValue += 1
            if self.space.State:
                if self.space1.State:
                    n = self._replaceText(xElem, u";(?=[:alnum:])", u"; ", True)
                    n += self._replaceText(xElem, u"\\?(?=[:alnum:])", u"? ", True)
                    n += self._replaceText(xElem, u"!(?=[:alnum:])", u"! ", True)
                    n += self._replaceText(xElem, u"…(?=[:alnum:])", u"… ", True)
                    n += self._replaceText(xElem, u"\\.(?=[A-ZÉÈÎ][:alpha:])", u". ", True, True)
                    n += self._replaceText(xElem, u"\\.(?=À)", u". ", True, True)
                    n += self._replaceText(xElem, u",(?=[:alpha:])", u", ", True)
                    n += self._replaceText(xElem, u":(?=[:alpha:])", u": ", True)
                    # exceptions:
                    n -= self._replaceText(xElem, u"(?<=DnT), w\\b", u",w", True, True)
                    n -= self._replaceText(xElem, u"(?<=DnT), A\\b", u",A", True, True)
                    self.space1_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.space2.State:
                    n = self._replaceText(xElem, u" -(?=[:alpha:]|[\"«“'‘])", u" - ", True)
                    n += self._replaceText(xElem, u" –(?=[:alpha:]|[\"«“'‘])", u" – ", True) # demi-cadratin
                    n += self._replaceText(xElem, u" —(?=[:alpha:]|[\"«“'‘])", u" — ", True) # cadratin
                    n += self._replaceText(xElem, u"(?<=[:alpha:])– ", u" – ", True)
                    n += self._replaceText(xElem, u"(?<=[:alpha:])— ", u" — ", True)
                    n += self._replaceText(xElem, u"(?<=[:alpha:])- ", u" - ", True)
                    n += self._replaceText(xElem, u"(?<=[\"»”'’])– ", u" – ", True)
                    n += self._replaceText(xElem, u"(?<=[\"»”'’])— ", u" — ", True)
                    n += self._replaceText(xElem, u"(?<=[\"»”'’])- ", u" - ", True)
                    self.space2_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                self.space.State = False
                self._switchCheckBox(self.space)
            self.pbar.ProgressValue = 17
            # Suppression
            if self.delete.State:
                if self.delete1.State:
                    n = self._replaceText(xElem, u"­", "", False) # tiret conditionnel / soft hyphen
                    self.delete1_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.delete2.State:
                    n = self._replaceBulletsByEmDash(xElem)
                    self.delete2_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                self.delete.State = False
                self._switchCheckBox(self.delete)
            self.pbar.ProgressValue = 20
            # signes typographiques
            if self.typo.State:
                if self.typo1.State:
                    n = self._replaceText(xElem, u"\\bl['´‘′`](?=[:alnum:])", u"l’", True, True)
                    n += self._replaceText(xElem, u"\\bj['´‘′`](?=[:alnum:])", u"j’", True, True)
                    n += self._replaceText(xElem, u"\\bm['´‘′`](?=[:alnum:])", u"m’", True, True)
                    n += self._replaceText(xElem, u"\\bt['´‘′`](?=[:alnum:])", u"t’", True, True)
                    n += self._replaceText(xElem, u"\\bs['´‘′`](?=[:alnum:])", u"s’", True, True)
                    n += self._replaceText(xElem, u"\\bc['´‘′`](?=[:alnum:])", u"c’", True, True)
                    n += self._replaceText(xElem, u"\\bd['´‘′`](?=[:alnum:])", u"d’", True, True)
                    n += self._replaceText(xElem, u"\\bn['´‘′`](?=[:alnum:])", u"n’", True, True)
                    n += self._replaceText(xElem, u"\\bç['´‘′`](?=[:alnum:])", u"ç’", True, True)
                    n += self._replaceText(xElem, u"\\bL['´‘′`](?=[:alnum:])", u"L’", True, True)
                    n += self._replaceText(xElem, u"\\bJ['´‘′`](?=[:alnum:])", u"J’", True, True)
                    n += self._replaceText(xElem, u"\\bM['´‘′`](?=[:alnum:])", u"M’", True, True)
                    n += self._replaceText(xElem, u"\\bT['´‘′`](?=[:alnum:])", u"T’", True, True)
                    n += self._replaceText(xElem, u"\\bS['´‘′`](?=[:alnum:])", u"S’", True, True)
                    n += self._replaceText(xElem, u"\\bC['´‘′`](?=[:alnum:])", u"C’", True, True)
                    n += self._replaceText(xElem, u"\\bD['´‘′`](?=[:alnum:])", u"D’", True, True)
                    n += self._replaceText(xElem, u"\\bN['´‘′`](?=[:alnum:])", u"N’", True, True)
                    n += self._replaceText(xElem, u"\\bÇ['´‘′`](?=[:alnum:])", u"Ç’", True, True)
                    n += self._replaceText(xElem, u"(qu|jusqu|lorsqu|puisqu|quoiqu|quelqu|presqu|entr|aujourd)['´‘′`]", u"$1’", True)
                    self.typo1_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.typo2.State:
                    n = self._replaceText(xElem, u"...", u"…", False)
                    n += self._replaceText(xElem, u"(?<=…)[.][.]", u"…", True)
                    n += self._replaceText(xElem, u"…[.](?![.])", u"…", True)
                    self.typo2_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.typo3.State:
                    if self.typo3b.State:
                        # demi-cadratin
                        n = self._replaceText(xElem, u" - ", u" – ", False)
                        n += self._replaceText(xElem, u" — ", u" – ", False)
                        n += self._replaceText(xElem, u" -,", u" –,", False)
                        n += self._replaceText(xElem, u" —,", u" –,", False)
                    else:
                        # cadratin
                        n = self._replaceText(xElem, u" - ", u" — ", False)
                        n += self._replaceText(xElem, u" – ", u" — ", False)
                        n += self._replaceText(xElem, u" -,", u" —,", False)
                        n += self._replaceText(xElem, u" –,", u" —,", False)
                    self.typo3_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.typo4.State:
                    if self.typo4a.State:
                        # cadratin
                        n = self._replaceText(xElem, u"^-[  ]", u"— ", True)
                        n += self._replaceText(xElem, u"^–[  ]", u"— ", True)
                        n += self._replaceText(xElem, u"^— ", u"— ", True)
                        n += self._replaceText(xElem, u"^[-–—](?=[:alnum:])", u"— ", True)
                    else:
                        # demi-cadratin
                        n = self._replaceText(xElem, u"^-[  ]", u"– ", True)
                        n += self._replaceText(xElem, u"^—[  ]", u"– ", True)
                        n += self._replaceText(xElem, u"^– ", u"– ", True)
                        n += self._replaceText(xElem, u"^[-–—](?=[:alnum:])", u"– ", True)
                    self.typo4_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.typo5.State:
                    n = self._replaceText(xElem, u'"([:alpha:]+)"', u"“$1”", True)
                    n += self._replaceText(xElem, u"''([:alpha:]+)''", u"“$1”", True)
                    n += self._replaceText(xElem, u"'([:alpha:]+)'", u"“$1”", True)
                    n += self._replaceText(xElem, u'^"(?=[:alnum:])', u"« ", True)
                    n += self._replaceText(xElem, u"^''(?=[:alnum:])", u"« ", True)
                    n += self._replaceText(xElem, u' "(?=[:alnum:])', u" « ", True)
                    n += self._replaceText(xElem, u" ''(?=[:alnum:])", u" « ", True)
                    n += self._replaceText(xElem, u'\\("(?=[:alnum:])', u"(« ", True)
                    n += self._replaceText(xElem, u"\\(''(?=[:alnum:])", u"(« ", True)
                    n += self._replaceText(xElem, u'(?<=[:alnum:])"$', u" »", True)
                    n += self._replaceText(xElem, u"(?<=[:alnum:])''$", u" »", True)
                    n += self._replaceText(xElem, u'(?<=[:alnum:])"(?=[] ,.:;?!…)])', u" »", True)
                    n += self._replaceText(xElem, u"(?<=[:alnum:])''(?=[] ,.:;?!…)])", u" »", True)
                    n += self._replaceText(xElem, u'(?<=[.!?…])" ', u" » ", True)
                    n += self._replaceText(xElem, u'(?<=[.!?…])"$', u" »", True)
                    self.typo5_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.typo7.State:
                    # no initial cap
                    n = self._replaceText(xElem, u"coeur", u"cœur", False, True)
                    n += self._replaceText(xElem, u"coel([aeio])", u"cœl$1", True, True)
                    n += self._replaceText(xElem, u"choeur", u"chœur", False, True)
                    n += self._replaceText(xElem, u"foet", u"fœt", False, True)
                    n += self._replaceText(xElem, u"oeil", u"œil", False, True)
                    n += self._replaceText(xElem, u"oeno", u"œno", False, True)
                    n += self._replaceText(xElem, u"oesoph", u"œsoph", False, True)
                    n += self._replaceText(xElem, u"oestro", u"œstro", False, True)
                    n += self._replaceText(xElem, u"oeuf", u"œuf", False, True)
                    n += self._replaceText(xElem, u"oeuvr", u"œuvr", False, True)
                    n += self._replaceText(xElem, u"moeur", u"mœur", False, True)
                    n += self._replaceText(xElem, u"noeu", u"nœu", False, True)
                    n += self._replaceText(xElem, u"soeur", u"sœur", False, True)
                    n += self._replaceText(xElem, u"voeu", u"vœu", False, True)
                    n += self._replaceText(xElem, u"aequo", u"æquo", False, True)
                    # with initial cap
                    n += self._replaceText(xElem, u"Coeur", u"Cœur", False, True)
                    n += self._replaceText(xElem, u"Coel([aeio])", u"Cœl$1", True, True)
                    n += self._replaceText(xElem, u"Choeur", u"Chœur", False, True)
                    n += self._replaceText(xElem, u"Foet", u"Fœt", False, True)
                    n += self._replaceText(xElem, u"Oeil", u"Œil", False, True)
                    n += self._replaceText(xElem, u"Oeno", u"Œno", False, True)
                    n += self._replaceText(xElem, u"Oesoph", u"Œsoph", False, True)
                    n += self._replaceText(xElem, u"Oestro", u"Œstro", False, True)
                    n += self._replaceText(xElem, u"Oeuf", u"Œuf", False, True)
                    n += self._replaceText(xElem, u"Oeuvr", u"Œuvr", False, True)
                    n += self._replaceText(xElem, u"Moeur", u"Mœur", False, True)
                    n += self._replaceText(xElem, u"Noeu", u"Nœu", False, True)
                    n += self._replaceText(xElem, u"Soeur", u"Sœur", False, True)
                    n += self._replaceText(xElem, u"Voeu", u"Vœu", False, True)
                    n += self._replaceText(xElem, u"Aequo", u"Æquo", False, True)
                    self.typo7_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.typo8.State:
                    # ligatures typographiques : fi, fl, ff, ffi, ffl, ft, st
                    n = 0
                    if self.typo8a.State:
                        if self.typo_ffi.State:
                            n += self._replaceText(xElem, u"ffi", u"ﬃ", False, True)
                        if self.typo_ffl.State:
                            n += self._replaceText(xElem, u"ffl", u"ﬄ", False, True)
                        if self.typo_fi.State:
                            n += self._replaceText(xElem, u"fi", u"ﬁ", False, True)
                        if self.typo_fl.State:
                            n += self._replaceText(xElem, u"fl", u"ﬂ", False, True)
                        if self.typo_ff.State:
                            n += self._replaceText(xElem, u"ff", u"ﬀ", False, True)
                        if self.typo_ft.State:
                            n += self._replaceText(xElem, u"ft", u"ﬅ", False, True)
                        if self.typo_st.State:
                            n += self._replaceText(xElem, u"st", u"ﬆ", False, True)
                    if self.typo8b.State:
                        if self.typo_fi.State:
                            n += self._replaceText(xElem, u"ﬁ", u"fi", False, True)
                        if self.typo_fl.State:
                            n += self._replaceText(xElem, u"ﬂ", u"fl", False, True)
                        if self.typo_ff.State:
                            n += self._replaceText(xElem, u"ﬀ", u"ff", False, True)
                        if self.typo_ffi.State:
                            n += self._replaceText(xElem, u"ﬃ", u"ffi", False, True)
                        if self.typo_ffl.State:
                            n += self._replaceText(xElem, u"ﬄ", u"ffl", False, True)
                        if self.typo_ft.State:
                            n += self._replaceText(xElem, u"ﬅ", u"ft", False, True)
                        if self.typo_st.State:
                            n += self._replaceText(xElem, u"ﬆ", u"st", False, True)
                    self.typo8_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                self.typo.State = False
                self._switchCheckBox(self.typo)
            self.pbar.ProgressValue = 28
            # divers
            if self.misc.State:
                if self.misc1.State:
                    if self.misc1a.State:
                        n = self._replaceText(xElem, u"(?<=\\b[0-9][0-9][0-9][0-9])(i?[èe]me|è|e)\\b", u"ᵉ", True)
                        n += self._replaceText(xElem, u"(?<=\\b[0-9][0-9][0-9])(i?[èe]me|è|e)\\b", u"ᵉ", True)
                        n += self._replaceText(xElem, u"(?<=\\b[0-9][0-9])(i?[èe]me|è|e)\\b", u"ᵉ", True)
                        n += self._replaceText(xElem, u"(?<=\\b[0-9])(i?[èe]me|è|e)\\b", u"ᵉ", True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVICL][XVICL][XVICL][XVICL])(i?[èe]me|è|e)\\b", u"ᵉ", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVICL][XVICL][XVICL])(i?[èe]me|è|e)\\b", u"ᵉ", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVICL][XVICL])(i?[èe]me|è|e)\\b", u"ᵉ", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVICL])(i?[èe]me|è)\\b", u"ᵉ", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b(au|l[ea]|du) [XVICL])e\\b", u"ᵉ", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVI])e(?= siècle)", u"ᵉ", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[1I])er\\b", u"ᵉʳ", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[1I])re\\b", u"ʳᵉ", True, True)
                    else:
                        n = self._replaceText(xElem, u"(?<=\\b[0-9][0-9][0-9][0-9])(i?[èe]me|è|ᵉ)\\b", u"e", True)
                        n += self._replaceText(xElem, u"(?<=\\b[0-9][0-9][0-9])(i?[èe]me|è|ᵉ)\\b", u"e", True)
                        n += self._replaceText(xElem, u"(?<=\\b[0-9][0-9])(i?[èe]me|è|ᵉ)\\b", u"e", True)
                        n += self._replaceText(xElem, u"(?<=\\b[0-9])(i?[èe]me|è|ᵉ)\\b", u"e", True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVICL][XVICL][XVICL][XVICL])(i?[èe]me|è|ᵉ)\\b", u"e", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVICL][XVICL][XVICL])(i?[èe]me|è|ᵉ)\\b", u"e", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVICL][XVICL])(i?[èe]me|è|ᵉ)\\b", u"e", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[XVICL])(i?[èe]me|è|ᵉ)\\b", u"e", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[1I])ᵉʳ\\b", u"er", True, True)
                        n += self._replaceText(xElem, u"(?<=\\b[1I])ʳᵉ\\b", u"er", True, True)
                    self.misc1_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.misc2.State:
                    n = self._replaceText(xElem, u"etc(…|[.][.][.]?)", u"etc.", True, True)
                    n += self._replaceText(xElem, u"(?<!,) etc[.]", u", etc.", True, True)
                    self.misc2_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.misc3.State:
                    n = self._replaceText(xElem, u"[ -]t[’'](?=il\\b|elle|on\\b)", u"-t-", True)
                    n += self._replaceText(xElem, u" t-(?=il|elle|on)", u"-t-", True)
                    n += self._replaceText(xElem, u"[ -]t[’'-](?=ils|elles)", u"-", True)
                    n += self._replaceText(xElem, u"(?<=[td])-t-(?=il|elle|on)", u"-", True)
                    n += self._replaceText(xElem, u"(celles?|celui|ceux) (ci|là)", u"$1-$2", True)
                    n += self._replaceText(xElem, u"dix (sept|huit|neuf)", u"dix-$1", True)
                    n += self._replaceText(xElem, u"quatre vingt", u"quatre-vingt", False)
                    n += self._replaceText(xElem, u"(soixante|quatre-vingt) dix", u"$1-dix", True)
                    n += self._replaceText(xElem, u"(vingt|trente|quarante|cinquante|soixante(?:-dix|)|quatre-vingt(?:-dix|)) (deux|trois|quatre|cinq|six|sept|huit|neuf)", u"$1-$2", True)
                    n += self._replaceText(xElem, u"(?<!-)(ci) (joint|desso?us|contre|devant|avant|après|incluse|g[îi]t|gisent)", u"$1-$2", True)
                    n += self._replaceText(xElem, u"vis à vis", u"vis-à-vis", False, True)
                    n += self._replaceText(xElem, u"Vis à vis", u"Vis-à-vis", False, True)
                    n += self._replaceText(xElem, u"week end", u"week-end", False, True)
                    n += self._replaceText(xElem, u"Week end", u"Week-end", False, True)
                    n += self._replaceText(xElem, u"(plus|moins) value", u"$1-value", True)
                    self.misc3_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                if self.misc5.State:
                    n = self._replaceText(xElem, u"(qu|lorsqu|puisqu|quoiqu|presqu|jusqu|aujourd|entr|quelqu) ", u"$1’", True, True)
                    if self.misc5b.State:
                        n += self._replaceText(xElem, u"\\bj (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"j’", True, True)
                        n += self._replaceText(xElem, u"\\bn (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"n’", True, True)
                        n += self._replaceText(xElem, u"\\bm (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"m’", True, True)
                        n += self._replaceText(xElem, u"\\bt (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"t’", True, True)
                        n += self._replaceText(xElem, u"\\bs (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"s’", True, True)
                        n += self._replaceText(xElem, u"\\bc (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"c’", True, True)
                        n += self._replaceText(xElem, u"\\bç (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"ç’", True, True)
                        n += self._replaceText(xElem, u"\\bl (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"l’", True, True)
                        n += self._replaceText(xElem, u"\\bd (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"d’", True, True)
                        if self.misc5c.State:
                            n += self._replaceText(xElem, u"\\bJ (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"J’", True, True)
                            n += self._replaceText(xElem, u"\\bN (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"N’", True, True)
                            n += self._replaceText(xElem, u"\\bM (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"M’", True, True)
                            n += self._replaceText(xElem, u"\\bT (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"T’", True, True)
                            n += self._replaceText(xElem, u"\\bS (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"S’", True, True)
                            n += self._replaceText(xElem, u"\\bC (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"C’", True, True)
                            n += self._replaceText(xElem, u"\\bÇ (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"Ç’", True, True)
                            n += self._replaceText(xElem, u"\\bL (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"L’", True, True)
                            n += self._replaceText(xElem, u"\\bD (?=[aàeéêiîoôuyhAÀEÉÊIÎOÔUYH])", u"D’", True, True)
                    self.misc5_res.Label = str(n)
                    self.pbar.ProgressValue += 1
                self.misc.State = False
                self._switchCheckBox(self.misc)
            self.pbar.ProgressValue = self.pbar.ProgressValueMax
            # end of processing
            xPointer.setType(uno.getConstantByName("com.sun.star.awt.SystemPointer.ARROW"))
            xWindowPeer.setPointer(xPointer)
            for x in xWindowPeer.Windows:
                x.setPointer(xPointer)
            self.xContainer.setVisible(True) # seems necessary to refresh the dialog box and text widgets (why?)
            nEndTime = time.clock()
            self.time_res.Label = getTimeRes(nEndTime-nStartTime)
        except:
            traceback.print_exc()

    def _replaceText (self, xElem, sPattern, sRep, bRegex, bCaseSensitive=False):
        try:
            xRD = xElem.createReplaceDescriptor()
            xRD.SearchString = sPattern
            xRD.ReplaceString = sRep
            xRD.SearchRegularExpression = bRegex
            xRD.SearchCaseSensitive = bCaseSensitive
            return xElem.replaceAll(xRD)
        except:
            traceback.print_exc()
        return 0

    def _replaceHyphenAtEndOfParagraphs (self, xDoc):
        self._replaceText(xDoc, u"- *$", u"-", True) # remove spaces at end of paragraphs if - is the last character
        xHunspell = self.xSvMgr.createInstanceWithContext("com.sun.star.linguistic2.SpellChecker", self.ctx)
        xCursor = xDoc.Text.createTextCursor()
        xCursor.gotoStart(False)
        n = 0
        while xCursor.gotoNextParagraph(False):
            xCursor.goLeft(2, True)
            if xCursor.String.startswith("-"):
                xCursor.gotoStartOfWord(False)
                xLocale = xCursor.CharLocale
                xCursor.gotoEndOfWord(True)
                sWord1 = xCursor.String
                xCursor.gotoNextParagraph(False)
                xCursor.gotoEndOfWord(True)
                sWord2 = xCursor.String
                if sWord1 and sWord2 and xHunspell.isValid(sWord1+sWord2, xLocale, ()):
                    xCursor.gotoStartOfParagraph(False)
                    xCursor.goLeft(2, True)
                    xCursor.setString("")
                    n += 1
            else:
                xCursor.goRight(2, False)
        return n

    def _mergeContiguousParagraphs (self, xDoc):
        self._replaceText(xDoc, u"^[  ]+$", u"", True) # clear empty paragraphs
        xCursor = xDoc.Text.createTextCursor()
        xCursor.gotoStart(False)
        n = 0
        try:
            while xCursor.gotoNextParagraph(False):
                xCursor.gotoEndOfParagraph(True)
                if xCursor.String != "":
                    xCursor.gotoStartOfParagraph(False)
                    xCursor.goLeft(1, True)
                    xCursor.setString(" ")
                    n += 1
        except:
            traceback.print_exc()
        self._replaceText(xDoc, u"  +", u" ", True)
        return n

    def _replaceBulletsByEmDash (self, xDoc):
        xCursor = xDoc.Text.createTextCursor()
        xCursor.gotoStart(False)
        sParaStyleName = ""
        if not self.delete2c.State:
            sParaStyleName = u"Standard"  if self.delete2a.State  else u"Text body"
        n = 0
        try:
            if xCursor.NumberingStyleName != "":
                xCursor.NumberingStyleName = ""
                if sParaStyleName:
                    xCursor.ParaStyleName = sParaStyleName
                xDoc.Text.insertString(xCursor, u"— ", False)
                n += 1
            while xCursor.gotoNextParagraph(False):
                if xCursor.NumberingStyleName != "":
                    xCursor.NumberingStyleName = ""
                    if sParaStyleName:
                        xCursor.ParaStyleName = sParaStyleName
                    xDoc.Text.insertString(xCursor, u"— ", False)
                    n += 1
        except:
            traceback.print_exc()
        return n

def getTimeRes (n):
    "returns duration in seconds as string"
    if n < 10:
        return "{:.3f} s".format(n)
    if n < 100:
        return "{:.2f} s".format(n)
    if n < 1000:
        return "{:.1f} s".format(n)
    return str(int(n)) + " s"


#g_ImplementationHelper = unohelper.ImplementationHelper()
#g_ImplementationHelper.addImplementation(TextFormatter, 'dicollecte.TextFormatter', ('com.sun.star.task.Job',))
