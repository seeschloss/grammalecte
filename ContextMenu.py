# -*- coding: utf8 -*-
# Grammalecte - Lexicographe
# by Olivier R. License: MPL 2

import uno
import unohelper
import traceback

from com.sun.star.task import XJob
from com.sun.star.ui import XContextMenuInterceptor
from com.sun.star.ui.ContextMenuInterceptorAction import IGNORED
from com.sun.star.ui.ContextMenuInterceptorAction import EXECUTE_MODIFIED

import grammalecte.fr.lexicographe as lxg


xDesktop = None
oDict = None
oLexicographe = None


def printServices (o):
    for s in o.getAvailableServiceNames():
        print(' >'+s)


def getConfigSetting (sNodeConfig, bUpdate):
    # get a configuration node
    # example: aSettings = getConfigSetting("/org.openoffice.Office.Common/Path/Current", false)
    xSvMgr = uno.getComponentContext().ServiceManager
    xConfigProvider = xSvMgr.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", uno.getComponentContext())
    xPropertyValue = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    xPropertyValue.Name = "nodepath"
    xPropertyValue.Value = sNodeConfig
    if bUpdate:
        sService = "com.sun.star.configuration.ConfigurationUpdateAccess"
    else:
        sService = "com.sun.star.configuration.ConfigurationAccess"
    return xConfigProvider.createInstanceWithArguments(sService, (xPropertyValue,))


class MyContextMenuInterceptor (XContextMenuInterceptor, unohelper.Base):
    def __init__ (self, ctx):
        self.ctx = ctx

    def notifyContextMenuExecute (self, xEvent):
        sWord = self._getWord()
        try:
            aItem, aVerb = oLexicographe.analyzeWord(sWord)
            if not aItem:
                #return uno.Enum("com.sun.star.ui.ContextMenuInterceptorAction", "IGNORED") # don’t work on AOO, have to import the value
                return IGNORED

            xContextMenu = xEvent.ActionTriggerContainer
            if xContextMenu:
                # entries index
                i = xContextMenu.Count

                nUnoConstantLine = uno.getConstantByName("com.sun.star.ui.ActionTriggerSeparatorType.LINE")
                i = self._addItemToContextMenu(xContextMenu, i, "ActionTriggerSeparator", SeparatorType=nUnoConstantLine)
                for item in aItem:
                    if isinstance(item, str):
                        i = self._addItemToContextMenu(xContextMenu, i, "ActionTrigger", Text=item)
                    elif isinstance(item, tuple):
                        sRoot, lMorph = item
                        # submenu
                        xSubMenuContainer = xContextMenu.createInstance("com.sun.star.ui.ActionTriggerContainer")
                        for j, s in enumerate(lMorph):
                            self._addItemToContextMenu(xSubMenuContainer, j, "ActionTrigger", Text=s)
                        # create root menu entry
                        i = self._addItemToContextMenu(xContextMenu, i, "ActionTrigger", Text=sRoot, SubContainer=xSubMenuContainer)
                    else:
                        i = self._addItemToContextMenu(xContextMenu, i, "ActionTrigger", Text="# erreur : {}".format(item))
                
                # Links to Conjugueur
                if aVerb:
                    i = self._addItemToContextMenu(xContextMenu, i, "ActionTriggerSeparator", SeparatorType=nUnoConstantLine)
                    for sVerb in aVerb:
                        i = self._addItemToContextMenu(xContextMenu, i, "ActionTrigger", Text="Conjuguer “{}”…".format(sVerb),
                                                       CommandURL="service:net.grammalecte.AppLauncher?CJ/"+sVerb)

                # The controller should execute the modified context menu and stop notifying other interceptors.
                #return uno.Enum("com.sun.star.ui.ContextMenuInterceptorAction", "EXECUTE_MODIFIED") # don’t work on AOO, have to import the value
                return EXECUTE_MODIFIED
        except:
            traceback.print_exc()
        #return uno.Enum("com.sun.star.ui.ContextMenuInterceptorAction", "IGNORED") # don’t work on AOO, have to import the value
        return IGNORED

    def _addItemToContextMenu (self, xContextMenu, i, sType, **args):
        xMenuItem = xContextMenu.createInstance("com.sun.star.ui."+sType)
        for k, v in args.items():
            xMenuItem.setPropertyValue(k, v)
        xContextMenu.insertByIndex(i, xMenuItem)
        return i + 1

    def _getWord (self):
        try:
            xDoc = xDesktop.getCurrentComponent()
            xViewCursor = xDoc.CurrentController.ViewCursor
            if xViewCursor.CharLocale.Language != "fr":
                return ""
            xText = xViewCursor.Text
            xCursor = xText.createTextCursorByRange(xViewCursor)
            xCursor.gotoStartOfWord(False)
            xCursor.gotoEndOfWord(True)
        except:
            traceback.print_exc()
        return xCursor.String.strip('.')


class JobExecutor (XJob, unohelper.Base):
    def __init__ (self, ctx):
        self.ctx = ctx
        global xDesktop
        global oDict
        global oLexicographe

        if not xDesktop:
            xDesktop = self.ctx.getServiceManager().createInstanceWithContext('com.sun.star.frame.Desktop', self.ctx)
        if not oDict:
            xCurCtx = uno.getComponentContext()
            oGC = xCurCtx.ServiceManager.createInstanceWithContext("org.openoffice.comp.pyuno.Lightproof.grammalecte", xCurCtx)
            oDict = oGC.getDictionary()
        if not oLexicographe:
            oLexicographe = lxg.Lexicographe(oDict)
        
    def execute (self, args):
        if not args:
            return
        # what version of the software?
        xSettings = getConfigSetting("org.openoffice.Setup/Product", False)
        sProdName = xSettings.getByName("ooName")
        sVersion = xSettings.getByName("ooSetupVersion")
        if (sProdName == "LibreOffice" and sVersion < "4") or sProdName == "OpenOffice.org":
            return
        
        # what event?
        bCorrectEvent = False
        for arg in args:
            if arg.Name == "Environment":
                for v in arg.Value:
                    if v.Name == "EnvType" and v.Value == "DOCUMENTEVENT":
                        bCorrectEvent = True
                    elif v.Name == "EventName":
                        pass
                        # check is correct event
                        #print "Event: %s" % v.Value
                    elif v.Name == "Model":
                        model = v.Value
        if bCorrectEvent:
            if model.supportsService("com.sun.star.text.TextDocument"):
                xController = model.getCurrentController()
                if xController:
                    xController.registerContextMenuInterceptor(MyContextMenuInterceptor(self.ctx))
        

g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(JobExecutor, "grammalecte.ContextMenuHandler", ("grammalecte.ContextMenuHandler",),)
