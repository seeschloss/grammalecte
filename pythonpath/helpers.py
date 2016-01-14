# -*- coding: utf8 -*-

import uno
import traceback

from com.sun.star.beans import PropertyValue


# XRay - API explorer
from com.sun.star.uno import RuntimeException as _rtex
def xray (myObject):
    try:
        sm = uno.getComponentContext().ServiceManager
        mspf = sm.createInstanceWithContext("com.sun.star.script.provider.MasterScriptProviderFactory", uno.getComponentContext())
        scriptPro = mspf.createScriptProvider("")
        xScript = scriptPro.getScript("vnd.sun.star.script:XrayTool._Main.Xray?language=Basic&location=application")
        xScript.invoke((myObject,), (), ())
        return
    except:
        raise _rtex("\nBasic library Xray is not installed", uno.getComponentContext())


# MRI - API Explorer
def mri (ctx, xTarget):
    try:
        xMri = ctx.ServiceManager.createInstanceWithContext("mytools.Mri", ctx)
        xMri.inspect(xTarget)
    except:
        raise _rtex("\Python extension MRI is not installed", uno.getComponentContext())


def getConfigSetting (sNodeConfig, bUpdate):
    "get a configuration node"
    # example: xNode = getConfigSetting("/org.openoffice.Office.Common/Path/Current", False)
    xSvMgr = uno.getComponentContext().ServiceManager
    xConfigProvider = xSvMgr.createInstanceWithContext("com.sun.star.configuration.ConfigurationProvider", uno.getComponentContext())
    xPropertyValue = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    xPropertyValue.Name = "nodepath"
    xPropertyValue.Value = sNodeConfig
    if bUpdate:
        sService = "com.sun.star.configuration.ConfigurationUpdateAccess"
    else:
        sService = "com.sun.star.configuration.ConfigurationAccess"
    return xConfigProvider.createInstanceWithArguments(sService, (xPropertyValue,)) # return xNode
