# -*- encoding: UTF-8 -*-
# Grammalecte - Lexicographe
# License: MPL 2


import re
import traceback


_dTAGS = {  
    ':G': "",
    ':N': u" nom,",
    ':A': u" adjectif,",
    ':M1': u" prénom,",
    ':M2': u" patronyme,",
    ':MP': u" nom propre,",
    ':W': u" adverbe,",
    ':X': u" adverbe de négation,",
    ':U': u" adverbe interrogatif,",
    ':J': u" interjection,",
    ':B': u" nombre,",

    ':R': u" préposition,",
    ':Rv': u" préposition verbale,",
    ':D': u" déterminant,",
    ':Dd': u" déterminant démonstratif,",
    ':De': u" déterminant exclamatif,",
    ':Dp': u" déterminant possessif,",
    ':Di': u" déterminant indéfini,",
    ':Dn': u" déterminant négatif,",
    ':Od': u" pronom démonstratif,",
    ':Oi': u" pronom indéterminé,",
    ':Ot': u" pronom interrogatif,",
    ':Or': u" pronom relatif,",
    ':Ow': u" pronom adverbial,",
    ':Os': u" pronom personnel sujet,",
    ':Oo': u" pronom personnel objet,",
    ':Cc': u" conjonction de coordination,",
    ':Cs': u" conjonction de subordination,",
    
    ':Ŵ': u" locution adverbiale (él.),",
    ':Ñ': u" locution nominale (él.),",
    ':Â': u" locution adjectivale (él.),",
    ':Ṽ': u" locution verbale (él.),",
    ':Ŕ': u" locution prépositive (él.),",
    ':Ĵ': u" locution interjective (él.),",

    ':Zp': u" préfixe,",
    ':Zs': u" suffixe,",

    ':V1': u" verbe (1er gr.),",
    ':V2': u" verbe (2e gr.),",
    ':V3': u" verbe (3e gr.),",
    ':V0e': u" verbe,",
    ':V0a': u" verbe,",

    ':O1': u" 1re pers.,",
    ':O2': u" 2e pers.,",
    ':O3': u" 3e pers.,",
    
    ':e': u" épicène",
    ':m': u" masculin",
    ':f': u" féminin",
    ':s': u" singulier",
    ':p': u" pluriel",
    ':i': u" invariable",

    ':Y': u" infinitif,",
    ':P': u" participe présent,",
    ':Q': u" participe passé,",

    ':Ip': u" présent,",
    ':Iq': u" imparfait,",
    ':Is': u" passé simple,",
    ':If': u" futur,",
    ':K': u" conditionnel présent,",
    ':Sp': u" subjonctif présent,",
    ':Sq': u" subjonctif imparfait,",
    ':E': u" impératif,",

    ':1s': u" 1re pers. sing.,",
    u':1ŝ': u" 1re pers. sing. [je?],",
    u':1ś': u" 1re pers. sing. [je?],",
    ':2s': u" 2e pers. sing.,",
    ':3s': u" 3e pers. sing.,",
    ':1p': u" 1re pers. plur.,",
    ':2p': u" 2e pers. plur.,",
    ':3p': u" 3e pers. plur.,",
    ':3p!': u" 3e pers. plur.,",
}

_dPFX = {
    'd': u"(de), déterminant épicène invariable",
    'l': u"(le/la), déterminant masculin/féminin singulier",
    'j': u"(je), pronom personnel sujet, 1re pers., épicène singulier",
    'm': u"(me), pronom personnel objet, 1re pers., épicène singulier",
    't': u"(te), pronom personnel objet, 2e pers., épicène singulier",
    's': u"(se), pronom personnel objet, 3e pers., épicène singulier/pluriel",
    'n': u"(ne), adverbe de négation",
    'c': u"(ce), pronom démonstratif, masculin singulier/pluriel",
    u'ç': u"(ça), pronom démonstratif, masculin singulier",
    'qu': u"(que), conjonction de subordination",
    'lorsqu': u"(lorsque), conjonction de subordination",
    'quoiqu': u"(quoique), conjonction de subordination",
    'jusqu': u"(jusque), préposition",
}

_dAD = {
    'je': u" pronom personnel sujet, 1re pers. sing.",
    'tu': u" pronom personnel sujet, 2e pers. sing.",
    'il': u" pronom personnel sujet, 3e pers. masc. sing.",
    'on': u" pronom personnel sujet, 3e pers. sing. ou plur.",
    'elle': u" pronom personnel sujet, 3e pers. fém. sing.",
    'nous': u" pronom personnel sujet/objet, 1re pers. plur.",
    'vous': u" pronom personnel sujet/objet, 2e pers. plur.",
    'ils': u" pronom personnel sujet, 3e pers. masc. plur.",
    'elles': u" pronom personnel sujet, 3e pers. masc. plur.",
    
    u"là": u" particule démonstrative",
    "ci": u" particule démonstrative",
    
    'le': u" COD, masc. sing.",
    'la': u" COD, fém. sing.",
    'les': u" COD, plur.",
        
    'moi': u" COI (à moi), sing.",
    'toi': u" COI (à toi), sing.",
    'lui': u" COI (à lui ou à elle), sing.",
    'nous2': u" COI (à nous), plur.",
    'vous2': u" COI (à vous), plur.",
    'leur': u" COI (à eux ou à elles), plur.",

    'y': u" pronom adverbial",
    "m'y": u" (me) pronom personnel objet + (y) pronom adverbial",
    "t'y": u" (te) pronom personnel objet + (y) pronom adverbial",
    "s'y": u" (se) pronom personnel objet + (y) pronom adverbial",

    'en': u" pronom adverbial",
    "m'en": u" (me) pronom personnel objet + (en) pronom adverbial",
    "t'en": u" (te) pronom personnel objet + (en) pronom adverbial",
    "s'en": u" (se) pronom personnel objet + (en) pronom adverbial",
}


class Lexicographe:

    def __init__ (self, oDict):
        self.oDict = oDict
        self._zElidedPrefix = re.compile(u"(?i)^([dljmtsncç]|quoiqu|lorsqu|jusqu|puisqu|qu)['’](.+)")
        self._zCompoundWord = re.compile(u"(?i)(\\w+)-((?:les?|la)-(?:moi|toi|lui|[nv]ous|leur)|t-(?:il|elle|on)|y|en|[mts][’'](?:y|en)|les?|l[aà]|[mt]oi|leur|lui|je|tu|ils?|elles?|on|[nv]ous)$")
        self._zTag = re.compile(u":\\w[^:]*")

    def analyzeWord (self, sWord):
        try:
            if not sWord:
                return (None, None)
            if sWord.count("-") > 4:
                return ([u"élément complexe indéterminé"], None)
            if sWord.isdigit():
                return (["nombre"], None)

            aMorph = []
            # préfixes élidés
            m = self._zElidedPrefix.match(sWord)
            if m:
                sWord = m.group(2)
                aMorph.append( u"{}’ : {}".format(m.group(1), _dPFX.get(m.group(1).lower(), "[?]")) )
            # mots composés
            m2 = self._zCompoundWord.match(sWord)
            if m2:
                sWord = m2.group(1)
            # Morphologies
            lMorph = self.oDict.getMorph(sWord)
            if len(lMorph) > 1:
                # sublist
                aMorph.append( (sWord, [ self.formatTags(s) for s in lMorph ]) )
            elif len(lMorph) == 1:
                aMorph.append( u"{} : {}".format(sWord, self.formatTags(lMorph[0])) )
            else:
                aMorph.append( u"{} :  inconnu du dictionnaire".format(sWord) )
            # suffixe d’un mot composé
            if m2:
                aMorph.append( u"-{} : {}".format(m2.group(2), self._formatSuffix(m2.group(2).lower())) )
            # Verbes
            aVerb = set([ s[1:s.find(" ")]  for s in lMorph  if ":V" in s ])
            return (aMorph, aVerb)
        except:
            traceback.print_exc()
            return (["#erreur"], None)

    def formatTags (self, sTags):
        sRes = ""
        sTags = re.sub("(?<=V[1-3])[itpqnmr_!eax?]+", "", sTags)
        sTags = re.sub("(?<=V0[ea])[itpqnmr_!eax?]+", "", sTags)
        for m in self._zTag.finditer(sTags):
            sRes += _dTAGS.get(m.group(0), " [{}]".format(m.group(0)))
        if sRes.startswith(" verbe") and not sRes.endswith("infinitif"):
            sRes += " [{}]".format(sTags[1:sTags.find(" ")])
        return sRes.rstrip(",")

    def _formatSuffix (self, s):
        if s.startswith("t-"):
            return u"“t” euphonique +" + _dAD.get(s[2:], "[?]")
        if not "-" in s:
            return _dAD.get(s.replace(u"’", "'"), "[?]")
        if s.endswith("ous"):
            s += '2'
        nPos = s.find("-")
        return u"%s +%s" % (_dAD.get(s[:nPos], "[?]"), _dAD.get(s[nPos+1:], "[?]"))
