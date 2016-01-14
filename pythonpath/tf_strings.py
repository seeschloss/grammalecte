# -*- encoding: UTF-8 -*-

def getUI (sLang):
    if sLang in dStrings:
        return dStrings[sLang]
    return dStrings["fr"]

dStrings = {
    "fr": {
        "title": u"Grammalecte · Formateur de texte [Français]",

        "ssp": u"Espaces ~surnuméraires",
        "ssp1": u"En début de paragraphe",
        "ssp2": u"Entre les mots",
        "ssp3": u"En fin de paragraphe",
        "ssp4": u"Avant les points (.), les virgules (,)",
        "ssp5": u"À l’intérieur des parenthèses",
        "ssp6": u"À l’intérieur des crochets",
        "ssp7": u"À l’intérieur des guillemets “ et ”",

        "space": u"Espaces ~manquantes",
        "space1": u"Après , ; : ? ! . …",
        "space2": u"Autour des tirets d’incise",

        "nbsp": u"Espaces ~insécables",
        "nbsp1": u"Avant : ; ? et !",
        "nbsp2": u"Avec les guillemets « et »",
        "nbsp3": u"Avant % ‰ € $ £ ¥ ˚C",
        "nbsp4": u"À l’intérieur des nombres",
        "nbsp5": u"Avant les unités de mesure",
        "nnbsp": u"fines",

        "delete": u"Su~ppressions",
        "delete1": u"Tirets conditionnels",
        "delete2": u"Puces  → tirets cadratins + style :",
        "delete2a": u"Standard",
        "delete2b": u"Corps de texte",
        "delete2c": u"Ø",
        "delete2c_help": u"Pas de changement",

        "typo": u"Signes ~typographiques",
        "typo1": u"Apostrophe (’)",
        "typo2": u"Points de suspension (…)",
        "typo3": u"Tirets d’incise :",
        "typo4": u"Tirets en début de paragraphe :",
        "emdash": u"cadratin (—)",
        "endash": u"demi-cadratin (–)",
        "typo5": u"Modifier les guillemets droits (\" et ')",
        "typo6": u"Points médians des unités (N·m, Ω·m…)",
        "typo7": u"Ligatures : cœur, œuf, mœurs, sœur…",
        "typo8": u"Ligatures",
        "typo8_help": u"Avertissement : de nombreuses polices ne contiennent pas ces caractères.",
        "typo8a": u"Faire",
        "typo8b": u"Défaire",
        "typo_ff": u"ff",
        "typo_fi": u"fi",
        "typo_ffi": u"ffi",
        "typo_fl": u"fl",
        "typo_ffl": u"ffl",        
        "typo_ft": u"ft",
        "typo_st": u"st",

        "misc": u"~Divers",
        "misc1": u"Ordinaux (15e, XXIe…)",
        "misc1a": u"e → ᵉ",
        "misc2": u"Et cætera, etc.",
        "misc3": u"Traits d’union manquants",
        "misc5": u"Apostrophes manquantes",
        "misc5b": u"lettres isolées (j’ n’ m’ t’ s’ c’ d’ l’)",
        "misc5c": u"Maj.",

        "struct": u"~Restructuration [!]",
        "struct_help": u"Attention : la restructuration coupe ou fusionne les paragraphes.",
        "struct1": u"Retour à la ligne ⇒ fin de paragraphe",
        "struct2": u"Enlever césures en fin de ligne/paragraphe",
        "struct3": u"Fusionner les paragraphes contigus [!]",
        "struct3_help": u"Concatène tous les paragraphes non séparés par un paragraphe vide.\nAttention : LibreOffice et OpenOffice ne peuvent accepter des paragraphes de plus de 65535 caractères, ce qui fait environ 12 pages avec une police de taille 12. Un dépassement de cette limite fera planter le logiciel. À partir de LibreOffice 4.3, cette limitation n’existe plus.",

        "default": u"[·]",
        "default_help": u"Options par défaut",

        "bsel": u"Sur la sélection active",
        "apply": u"~Appliquer",
        "close": u"~Fermer",

        "info": u"(i)",
        "infotitle": u"Informations",
        "infomsg": u"Le formateur de texte est un outil qui automatise la correction d’erreurs typographiques en employant le moteur interne “Chercher & remplacer” de Writer.\n\nUtilisez l’outil avec prudence. À cause de certaines limitations, le formateur ne peut gérer tous les cas. Vérifiez votre texte après emploi."
    },
    "en": {
        "title": u"Grammalecte · Text Formatter [French]",

        "ssp": u"~Supernumerary spaces",
        "ssp1": u"At the beginning of paragraph",
        "ssp2": u"Between words",
        "ssp3": u"At the end of paragraph",
        "ssp4": u"Before dots (.), commas (,)",
        "ssp5": u"Within parenthesis",
        "ssp6": u"Within square brackets",
        "ssp7": u"Within “ and ”",

        "space": u"~Missing spaces",
        "space1": u"After , ; : ? ! . …",
        "space2": u"Surrounding dashes",

        "nbsp": u"~Non-breaking spaces ",
        "nbsp1": u"Before : ; ? and !",
        "nbsp2": u"With quoting marks « and »",
        "nbsp3": u"Before % ‰ € $ £ ¥ ˚C",
        "nbsp4": u"Within numbers",
        "nbsp5": u"Before units of measurement",
        "nnbsp": u"narrow",

        "delete": u"~Deletions",
        "delete1": u"Soft hyphens",
        "delete2": u"Bullets  → em-dash + style:",
        "delete2a": u"Standard",
        "delete2b": u"Text Body",
        "delete2c": u"Ø",
        "delete2c_help": u"No change",

        "typo": u"~Typographical signs",
        "typo1": u"Apostrophe (’)",
        "typo2": u"Ellipsis (…)",
        "typo3": u"Dashes:",
        "typo4": u"Dashes at beginning of paragraph:",
        "emdash": u"em dash (—)",
        "endash": u"en dash (–)",
        "typo5": u"Change quotation marks (\" and ')",
        "typo6": u"Interpuncts in units (N·m, Ω·m…)",
        "typo7": u"Ligatures : cœur, œuf, mœurs, sœur…",
        "typo8": u"Ligatures",
        "typo8_help": u"Warning: many fonts don’t contain these characters.",
        "typo8a": u"Set",
        "typo8b": u"Unset",
        "typo_ff": u"ff",
        "typo_fi": u"fi",
        "typo_ffi": u"ffi",
        "typo_fl": u"fl",
        "typo_ffl": u"ffl",        
        "typo_ft": u"ft",
        "typo_st": u"st",


        "misc": u"M~iscellaneous",
        "misc1": u"Ordinals (15e, XXIe…)",
        "misc1a": u"e → ᵉ",
        "misc2": u"Et cætera, etc.",
        "misc3": u"Missing hyphens",
        "misc5": u"Missing apostrophes",
        "misc5b": u"single letters (j’ n’ m’ t’ s’ c’ d’ l’)",
        "misc5c": u"Cap.",

        "struct": u"~Restructuration [!]",
        "struct_help": u"Caution: Restructuration cuts or merges paragraphs.",
        "struct1": u"End of line ⇒ end of paragraph",
        "struct2": u"Remove syllabification hyphens at EOL/EOP",
        "struct3": u"Merge contiguous paragraphs [!]",
        "struct3_help": u"Concatenate all paragraphs not separated by an empty paragraph.\nCaution: LibreOffice and OpenOffice can’t deal with paragraphs longer than 65,535 characters, which is about 12 pages with font size 12. Overstepping this limit will crash the software. For LibreOffice 4.3 and beyond, this limitation doesn’t exist any more.",

        "default": u"[·]",
        "default_help": u"Default options",

        "bsel": u"On current selection",
        "apply": u"~Apply",
        "close": u"~Close",

        "info": u"(i)",
        "infotitle": u"Informations",
        "infomsg": u"The text formatter is a tool which automates correction of typographical errors by using the internal engine “Search & replace” of Writer.\n\nUse this tool with caution. Due to several limitations, it cannot handle all cases. Check your text after use."
    }
}


