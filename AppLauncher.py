# -*- coding: utf8 -*-
# Grammalecte AppLauncher
# by Olivier R.
# License: MPL 2

import unohelper
import uno
import traceback

import helpers

from com.sun.star.task import XJobExecutor


class AppLauncher (unohelper.Base, XJobExecutor):
    def __init__ (self, ctx):
        self.ctx = ctx
        # In this extension, French is default language.
        # It is assumed that those who need to use the French dictionaries understand French and may not understand English.
        xSettings = helpers.getConfigSetting("/org.openoffice.Setup/L10N", False)
        sLocale = xSettings.getByName("ooLocale")  # Note: look at ooSetupSystemLocale value?
        self.sLang = sLocale[0:2]

    # XJobExecutor
    def trigger (self, sCmd):
        try:
            if sCmd == "About":
                import About
                xDialog = About.AboutGrammalecte(self.ctx)
                xDialog.run(self.sLang)
            elif sCmd.startswith("CJ"):
                import Conjugueur
                xDialog = Conjugueur.Conjugueur(self.ctx)
                if sCmd[2:3] == "/":
                    xDialog.run(sCmd[3:])
                else:
                    xDialog.run()
            elif sCmd == "TF":
                import TextFormatter
                xDialog = TextFormatter.TextFormatter(self.ctx)
                xDialog.run(self.sLang)
            elif sCmd == "DS":
                import DictionarySwitcher
                xDialog = DictionarySwitcher.FrenchDictionarySwitcher(self.ctx)
                xDialog.run(self.sLang)
            elif sCmd == "MA":
                import Author
                xDialog = Author.Author(self.ctx)
                xDialog.run(self.sLang)
            elif sCmd == "OP":
                import Options
                xDialog = Options.GC_Options(self.ctx)
                xDialog.run(self.sLang)
            # elif sCmd.startswith("URL/"):
            #     # Call from context menu to launch URL?
            #     # http://opengrok.libreoffice.org/xref/core/sw/source/ui/lingu/olmenu.cxx#785
            #     xSystemShellExecute = self.ctx.getServiceManager().createInstanceWithContext('com.sun.star.system.SystemShellExecute', self.ctx)
            #     xSystemShellExecute.execute(url, "", uno.getConstantByName("com.sun.star.system.SystemShellExecuteFlags.URIS_ONLY"))
            else:
                print("Unknown command: "+str(sCmd))
        except:
            traceback.print_exc()
        

g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(AppLauncher, 'net.grammalecte.AppLauncher', ('com.sun.star.task.Job',))
