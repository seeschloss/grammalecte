# -*- encoding: UTF-8 -*-

def getUI (sLang):
    if sLang in dStrings:
        return dStrings[sLang]
    return dStrings["fr"]

dStrings = {
    "fr": {
            "windowtitle": u"À propos…",
            "title": u"Grammalecte",
            "version": u"Version : 0.5.0b4",
            "license": u"Licence : GPL 3",
            "website": u"Site web",

            "pythonver": u"Machine virtuelle Python : v",

            "message": u"Avec le soutien de",
            "sponsor": u"La Mouette…",
            "link": u"… et de nombreux contributeurs.",

            "close": u"~OK"
          },
    "en": {
            "windowtitle": u"About…",
            "title": u"Grammalecte",
            "version": u"Version: 0.5.0b4",
            "license": u"License: GPL 3",
            "website": u"Web site",

            "pythonver": u"Python virtual machine: v",

            "message": u"With the support of",
            "sponsor": u"La Mouette…",
            "link": u"… and many contributors.",

            "close": u"~OK"
          }
}
