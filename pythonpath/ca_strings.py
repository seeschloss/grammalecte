# -*- encoding: UTF-8 -*-

def getUI (sLang):
    if sLang in dStrings:
        return dStrings[sLang]
    return dStrings["fr"]

dStrings = {
    "fr": {
            "title": u"Grammalecte · Édition du champ “Auteur”",

            "state": u"Valeur actuelle du champ “Auteur” :",
            "empty": u"[vide]",

            "newvalue": u"Entrez la nouvelle valeur :",

            "modify": u"Modifier",
            "cancel": u"Annuler"
          },
    "en": {
            "title": u"Grammalecte · Edition of field “Author”",

            "state": u"Current value of field “Author”:",
            "empty": u"[empty]",

            "newvalue": u"Enter the new value:",

            "modify": u"Modify",
            "cancel": u"Cancel"
          }
}


