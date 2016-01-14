# -*- encoding: UTF-8 -*-

import re
import sys
import os
import traceback

from ..ibdawg import IBDAWG
from ..echo import echo
from . import gc_options


__all__ = [ "load", "parse", "setOptions", "ignoreRule", "resetIgnoreRules", "getDictionary", \
            "lang", "locales", "pkg", "name", "version", "author" ]


lang = u"fr"
locales = {'fr-FR': ['fr', 'FR', ''], 'fr-BE': ['fr', 'BE', ''], 'fr-MC': ['fr', 'MC', ''], 'fr-CH': ['fr', 'CH', ''], 'fr-LU': ['fr', 'LU', ''], 'fr-CA': ['fr', 'CA', '']}
pkg = u"grammalecte"
name = u"Grammalecte"
version = u"0.5.0b4"
author = u"Olivier R."

# commons regexes
_zEndOfSentence = re.compile(u'([.?!:;…][ .?!… »”")]*|.$)')
_zBeginOfParagraph = re.compile(u"^\W*")
_zEndOfParagraph = re.compile(u"\W*$")
_zNextWord = re.compile(u" +(\w[\w-]*)")
_zPrevWord = re.compile(u"(\w[\w-]*) +$")

# grammar rules and dictionary
_langmodule = None
_dOptions = dict(gc_options.dOpt)       # duplication necessary, to be able to reset to default
_aIgnoredRules = set()
_oDict = None
_dAnalyses = {}                         # cache for data from dictionary

_GLOBALS = globals()


#### Parsing

def parse (sText, sCountry="FR", bDebug=False):
    "analyses the paragraph sText and returns list of errors"
    aErr = []
    sAlt = sText
    dDA = {}
    # analyze by paragraph
    try:
        sNew, aErr = _proofread(sText, sAlt, 0, 0, dDA, sCountry, bDebug)
        if sNew:
            sText = sNew
    except:
        raise

    # analyze by sentence
    lTuplePos = []
    nBeginOfSentence = _zBeginOfParagraph.match(sText).end()
    for m in _zEndOfSentence.finditer(sText):
        lTuplePos.append((nBeginOfSentence, m.end()))
        nBeginOfSentence = m.end()
    for iStart, iEnd in lTuplePos:
        if 4 < (iEnd - iStart) < 2000:
            dDA = {}
            for i in range(1, _getNpass()):
                try:
                    sNew, errs = _proofread(sText[iStart:iEnd], sAlt[iStart:iEnd], iStart, i, dDA, sCountry, bDebug)
                    if sNew:
                        sText = sText[:iStart] + sNew + sText[iEnd:]
                    aErr += errs
                except:
                    raise
    return tuple(aErr)


def _proofread (s, sx, nOffset, nPass, dDA, sCountry, bDebug):
    aErrs = []
    bChange = False
    
    if nPass == 1:
        # after the first pass, we remove automatically some characters, and change some others
        if u" " in s:
            s = s.replace(u" ", u' ') # nbsp
            bChange = True
        if u" " in s:
            s = s.replace(u" ", u' ') # snbsp
            bChange = True
        if u"@" in s:
            s = s.replace(u"@", u' ')
            bChange = True
        if u"'" in s:
            s = s.replace(u"'", u"’")
            bChange = True
        if u"‑" in s:
            s = s.replace(u"‑", u"-") # nobreakdash
            bChange = True

    bIdRule = option('idrule')

    for sOption, zRegex, bUppercase, sIdRule, lActions in _getRules(nPass):
        if (not sOption or option(sOption)) and not sIdRule in _aIgnoredRules:
            for m in zRegex.finditer(s):
                for sFuncCond, cActionType, sWhat, *eAct in lActions:
                # action in lActions: [ condition, action type, replacement/suggestion/action[, iGroup[, message, URL]] ]
                    try:
                        if not sFuncCond or _GLOBALS[sFuncCond](s, sx, m, dDA, sCountry):
                            if cActionType == "-":
                                # grammar error
                                # (text, replacement, nOffset, m, iGroup, sId, bUppercase, sURL, bIdRule)
                                aErrs.append(_createError(s, sWhat, nOffset, m, eAct[0], sIdRule, bUppercase, eAct[1], eAct[2], bIdRule))
                            elif cActionType == "~":
                                # text processor
                                s = _rewrite(s, sWhat, eAct[0], m, bUppercase)
                                bChange = True
                                if bDebug:
                                    echo(u"~ " + s + "  -- " + m.group(eAct[0]) + "  # " + sIdRule)
                            elif cActionType == "=":
                                # disambiguation
                                _GLOBALS[sWhat](s, m, dDA)
                                if bDebug:
                                    echo(u"= " + m.group(0) + "  # " + sIdRule)
                            else:
                                echo("# error: unknown action at " + sIdRule)
                    except Exception as e:
                        raise Exception(str(e), sIdRule)
    if bChange:
        return (s, tuple(aErrs))
    return (False, tuple(aErrs))


def _createWriterError (s, sRepl, nOffset, m, iGroup, sId, bUppercase, sMsg, sURL, bIdRule):
    "error for Writer (LO/OO)"
    xErr = SingleProofreadingError()
    #xErr = uno.createUnoStruct( "com.sun.star.linguistic2.SingleProofreadingError" )
    xErr.nErrorStart        = nOffset + m.start(iGroup)
    xErr.nErrorLength       = m.end(iGroup) - m.start(iGroup)
    xErr.nErrorType         = PROOFREADING
    xErr.aRuleIdentifier    = sId
    # suggestions
    if sRepl[0:1] == "=":
        sugg = _GLOBALS[sRepl[1:]](s, m)
        if sugg:
            if bUppercase and m.group(iGroup)[0:1].isupper():
                xErr.aSuggestions = tuple(map(str.capitalize, sugg.split("|")))
            else:
                xErr.aSuggestions = tuple(sugg.split("|"))
        else:
            xErr.aSuggestions = ()
    elif sRepl == "_":
        xErr.aSuggestions = ()
    else:
        if bUppercase and m.group(iGroup)[0:1].isupper():
            xErr.aSuggestions = tuple(map(str.capitalize, m.expand(sRepl).split("|")))
        else:
            xErr.aSuggestions = tuple(m.expand(sRepl).split("|"))
    # Message
    if sMsg[0:1] == "=":
        sMessage = _GLOBALS[sMsg[1:]](s, m)
    else:
        sMessage = m.expand(sMsg)
    xErr.aShortComment      = sMessage   # sMessage.split("|")[0]     # in context menu
    xErr.aFullComment       = sMessage   # sMessage.split("|")[-1]    # in dialog
    if bIdRule:
        xErr.aShortComment += "  # " + sId
    # URL
    if sURL:
        p = PropertyValue()
        p.Name = "FullCommentURL"
        p.Value = sURL
        xErr.aProperties    = (p,)
    else:
        xErr.aProperties    = ()
    return xErr


def _createDictError (s, sRepl, nOffset, m, iGroup, sId, bUppercase, sMsg, sURL, bIdRule):
    "error as a dictionary"
    dErr = {}
    dErr["nStart"]          = nOffset + m.start(iGroup)
    dErr["nEnd"]            = nOffset + m.end(iGroup)
    dErr["sRuleId"]         = sId
    # suggestions
    if sRepl[0:1] == "=":
        sugg = _GLOBALS[sRepl[1:]](s, m)
        if sugg:
            if bUppercase and m.group(iGroup)[0:1].isupper():
                dErr["aSuggestions"] = tuple(map(str.capitalize, sugg.split("|")))
            else:
                dErr["aSuggestions"] = tuple(sugg.split("|"))
        else:
            dErr["aSuggestions"] = ()
    elif sRepl == "_":
        dErr["aSuggestions"] = ()
    else:
        if bUppercase and m.group(iGroup)[0:1].isupper():
            dErr["aSuggestions"] = tuple(map(str.capitalize, m.expand(sRepl).split("|")))
        else:
            dErr["aSuggestions"] = tuple(m.expand(sRepl).split("|"))
    # Message
    if sMsg[0:1] == "=":
        sMessage = _GLOBALS[sMsg[1:]](s, m)
    else:
        sMessage = m.expand(sMsg)
    dErr["sMessage"]      = sMessage
    if bIdRule:
        dErr["sMessage"] += "  # " + sId
    # URL
    dErr["URL"] = sURL  if sURL  else ""
    return dErr


def _rewrite (s, sRepl, iGroup, m, bUppercase):
    "text processor: write sRepl in s at iGroup position"
    ln = m.end(iGroup) - m.start(iGroup)
    if sRepl == "*":
        sNew = " " * ln
    elif sRepl == ">" or sRepl == "_" or sRepl == u"~":
        sNew = sRepl + " " * (ln-1)
    elif sRepl == "@":
        sNew = "@" * ln
    elif sRepl[0:1] == "=":
        if sRepl[1:2] != "@":
            sNew = _GLOBALS[sRepl[1:]](s, m)
            sNew = sNew + " " * (ln-len(sNew))
        else:
            sNew = _GLOBALS[sRepl[2:]](s, m)
            sNew = sNew + "@" * (ln-len(sNew))
        if bUppercase and m.group(iGroup)[0:1].isupper():
            sNew = sNew.capitalize()
    else:
        sNew = m.expand(sRepl)
        sNew = sNew + " " * (ln-len(sNew))
    return s[0:m.start(iGroup)] + sNew + s[m.end(iGroup):]


def ignoreRule (sId):
    _aIgnoredRules.add(sId)


def resetIgnoreRules ():
    _aIgnoredRules.clear()


#### init

try:
    # LibreOffice / OpenOffice
    from com.sun.star.linguistic2 import SingleProofreadingError
    from com.sun.star.text.TextMarkupType import PROOFREADING
    from com.sun.star.beans import PropertyValue
    #import lightproof_handler_grammalecte as opt
    _createError = _createWriterError
except ImportError:
    _createError = _createDictError


def load ():
    global _oDict
    try:
        _oDict = IBDAWG("french.bdic")
    except:
        traceback.print_exc()


def setOptions (dOpt):
    _dOptions.update(dOpt)


def getDictionary ():
    return _oDict


def _getNpass ():
    try:
        return len(_langmodule.rules)
    except:
        _loadRules()
    return len(_langmodule.rules)


def _getRules (n):
    try:
        return _langmodule.rules[n]
    except:
        _loadRules()
    return _langmodule.rules[n]


def _loadRules ():
    global _langmodule
    from . import gc_rules
    _langmodule = gc_rules
    _compileRulesRegex()


def _compileRulesRegex ():
    for gc_pass in _langmodule.rules:
        for rule in gc_pass:
            try:
                rule[1] = re.compile(rule[1])
            except:
                echo("Bad regular expression in # " + str(rule[3]))
                rule[1] = "(?i)<Grammalecte>"


def _getPath ():
    return os.path.join(os.path.dirname(sys.modules[__name__].__file__), __name__ + ".py")



#### common functions

def option (sOpt):
    "return True if option sOpt is active"
    return _dOptions.get(sOpt, False)
    #return opt.options.get(sOpt, False)


def _storeMorphFromFSA (sWord):
    "retrieves morphologies list from _oDict -> _dAnalyses"
    global _dAnalyses
    _dAnalyses[sWord] = _oDict.getMorph(sWord)
    return True  if _dAnalyses[sWord]  else False


def morph (dDA, tWord, pattern, strict=True, noword=False):
    "analyse a tuple (position, word), return True if pattern in morphologies (disambiguation on)"
    if not tWord:
        return noword
    if tWord[1] not in _dAnalyses and not _storeMorphFromFSA(tWord[1]):
        return False
    lMorph = dDA[tWord[0]]  if dDA.get(tWord[0], None)  else _dAnalyses[tWord[1]]
    if not lMorph:
        return False
    p = re.compile(pattern)
    if strict:
        return all(p.search(s)  for s in lMorph)
    return any(p.search(s)  for s in lMorph)


def morphex (dDA, tWord, pattern, negpattern, noword=False):
    "analyse a tuple (position, word), returns True if not negpattern in word morphologies and pattern in word morphologies (disambiguation on)"
    if not tWord:
        return noword
    if tWord[1] not in _dAnalyses and not _storeMorphFromFSA(tWord[1]):
        return False
    lMorph = dDA[tWord[0]]  if dDA.get(tWord[0], None)  else _dAnalyses[tWord[1]]
    # check negative condition
    np = re.compile(negpattern)
    if any(np.search(s)  for s in lMorph):
        return False
    # search pattern
    p = re.compile(pattern)
    return any(p.search(s)  for s in lMorph)


def analyse (sWord, pattern, strict=True):
    "analyse a word, return True if pattern in morphologies (disambiguation off)"
    if sWord not in _dAnalyses and not _storeMorphFromFSA(sWord):
        return False
    if not _dAnalyses[sWord]:
        return False
    p = re.compile(pattern)
    if strict:
        return all(p.search(s)  for s in _dAnalyses[sWord])
    return any(p.search(s)  for s in _dAnalyses[sWord])


def analysex (sWord, pattern, negpattern):
    "analyse a word, returns True if not negpattern in word morphologies and pattern in word morphologies (disambiguation off)"
    if sWord not in _dAnalyses and not _storeMorphFromFSA(sWord):
        return False
    # check negative condition
    np = re.compile(negpattern)
    if any(np.search(s)  for s in _dAnalyses[sWord]):
        return False
    # search pattern
    p = re.compile(pattern)
    return any(p.search(s)  for s in _dAnalyses[sWord])


def stem (sWord):
    "returns a list of sWord's stems"
    if not sWord:
        return []
    if sWord not in _dAnalyses and not _storeMorphFromFSA(sWord):
        return []
    return [ s[1:s.find(" ")]  for s in _dAnalyses[sWord] ]


## functions to get text outside pattern scope

# warning: check compile_rules.py to understand how it works

def nextword (s, iStart, n):
    "get the nth word of the input string or empty string"
    m = re.match(u"(?u)( +[\\w%-]+){" + str(n-1) + u"} +([\\w%-]+)", s[iStart:])
    if not m:
        return None
    return (iStart+m.start(2), m.group(2))


def prevword (s, n):
    "get the (-)nth word of the input string or empty string"
    m = re.search(u"(?u)([\\w%-]+) +([\\w%-]+ +){" + str(n-1) + u"}$", s)
    if not m:
        return None
    return (m.start(1), m.group(1))


def nextword1 (s, iStart):
    "get next word (optimization)"
    m = _zNextWord.match(s[iStart:])
    if not m:
        return None
    return (iStart+m.start(1), m.group(1))


def prevword1 (s):
    "get previous word (optimization)"
    m = _zPrevWord.search(s)
    if not m:
        return None
    return (m.start(1), m.group(1))


def look (s, p, np=None):
    "seek pattern p in s (before/after/fulltext), if antipattern np not in s"
    if np and re.search(np, s):
        return False
    if re.search(p, s):
        return True
    return False


def look_chk1 (dDA, s, nOffset, p, pmg1, negpmg1=None):
    "returns True if s has pattern p and m.group(1) has pattern pmg1"
    m = re.search(p, s)
    if not m:
        return False
    try:
        sWord = m.group(1)
        nPos = m.start(1) + nOffset
    except:
        #print("Missing group 1")
        return False
    if negpmg1:
        return morphex(dDA, (nPos, sWord), pmg1, negpmg1)
    return morph(dDA, (nPos, sWord), pmg1, False)


#### Disambiguator

def select (dDA, nPos, sWord, sPattern, lDefault=None):
    if not sWord:
        return True
    if nPos in dDA:
        return True
    if sWord not in _dAnalyses and not _storeMorphFromFSA(sWord):
        return True
    if len(_dAnalyses[sWord]) == 1:
        return True
    lSelect = [ sMorph  for sMorph in _dAnalyses[sWord]  if re.search(sPattern, sMorph) ]
    if lSelect:
        if len(lSelect) != len(_dAnalyses[sWord]):
            dDA[nPos] = lSelect
            #echo("= "+sWord+" "+str(dDA.get(nPos, "null")))
    elif lDefault:
        dDA[nPos] = lDefault
        #echo("= "+sWord+" "+str(dDA.get(nPos, "null")))
    return True


def exclude (dDA, nPos, sWord, sPattern, lDefault=None):
    if not sWord:
        return True
    if nPos in dDA:
        return True
    if sWord not in _dAnalyses and not _storeMorphFromFSA(sWord):
        return True
    if len(_dAnalyses[sWord]) == 1:
        return True
    lSelect = [ sMorph  for sMorph in _dAnalyses[sWord]  if not re.search(sPattern, sMorph) ]
    if lSelect:
        if len(lSelect) != len(_dAnalyses[sWord]):
            dDA[nPos] = lSelect
            #echo("= "+sWord+" "+str(dDA.get(nPos, "null")))
    elif lDefault:
        dDA[nPos] = lDefault
        #echo("= "+sWord+" "+str(dDA.get(nPos, "null")))
    return True


def define (dDA, nPos, lMorph):
    dDA[nPos] = lMorph
    #echo("= "+str(nPos)+" "+str(dDA[nPos]))
    return True


#### GRAMMAR CHECKER PLUGINS



#### GRAMMAR CHECKING ENGINE PLUGIN: Parsing functions for French language

from . import cregex as cr


def rewriteSubject (s1, s2):
    # s1 is supposed to be prn/patr/npr (M[12P])
    if s2 == "lui":
        return "ils"
    if s2 == "moi":
        return "nous"
    if s2 == "toi":
        return "vous"
    if s2 == "nous":
        return "nous"
    if s2 == "vous":
        return "vous"
    if s2 == "eux":
        return "ils"
    if s2 == "elle" or s2 == "elles":
        # We don’t check if word exists in _dAnalyses, for it is assumed it has been done before
        if cr.mbNprMasNotFem(_dAnalyses.get(s1, "")):
            return "ils"
        # si épicène, indéterminable, mais OSEF, le féminin l’emporte
        return "elles"
    return s1 + " et " + s2


def apposition (sWord1, sWord2):
    "returns True if nom + nom (no agreement required)"
    # We don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    return cr.mbNomNotAdj(_dAnalyses.get(sWord2, "")) and cr.mbPpasNomNotAdj(_dAnalyses.get(sWord1, ""))


def isAmbiguousNAV (sWord):
    "words which are nom|adj and verb are ambiguous (except être and avoir)"
    if sWord not in _dAnalyses and not _storeMorphFromFSA(sWord):
        return False
    if not cr.mbNomAdj(_dAnalyses[sWord]) or sWord == "est":
        return False
    if cr.mbVconj(_dAnalyses[sWord]) and not cr.mbMG(_dAnalyses[sWord]):
        return True
    return False


def isAmbiguousAndWrong (sWord1, sWord2, sReqMorphNA, sReqMorphConj):
    "use it if sWord1 won’t be a verb; word2 is assumed to be True via isAmbiguousNAV"
    # We don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    a2 = _dAnalyses.get(sWord2, [])
    if not a2:
        return False
    if cr.checkConjVerb(a2, sReqMorphConj):
        # verb word2 is ok
        return False
    a1 = _dAnalyses.get(sWord1, [])
    if not a1:
        return False
    if cr.checkAgreement(a1, a2, sReqMorphNA) and (cr.mbAdj(a2) or cr.mbAdj(a1)):
        return False
    return True


def isVeryAmbiguousAndWrong (sWord1, sWord2, sReqMorphNA, sReqMorphConj, bLastHopeCond):
    "use it if sWord1 can be also a verb; word2 is assumed to be True via isAmbiguousNAV"
    # We don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    a2 = _dAnalyses.get(sWord2, [])
    if not a2:
        return False
    if cr.checkConjVerb(a2, sReqMorphConj):
        # verb word2 is ok
        return False
    a1 = _dAnalyses.get(sWord1, [])
    if not a1:
        return False
    if cr.checkAgreement(a1, a2, sReqMorphNA) and (cr.mbAdj(a2) or cr.mbAdjNb(a1)):
        return False
    # now, we know there no agreement, and conjugation is also wrong
    if cr.isNomAdj(a1):
        return True
    #if cr.isNomAdjVerb(a1): # considered True
    if bLastHopeCond:
        return True
    return False


#### Syntagmes

_zEndOfNG1 = re.compile(u" +(?:, +|)(?:n(?:’|e |o(?:u?s|tre) )|l(?:’|e(?:urs?|s|) |a )|j(?:’|e )|m(?:’|es? |a |on )|t(?:’|es? |a |u )|s(?:’|es? |a )|c(?:’|e(?:t|tte|s|) )|ç(?:a |’)|ils? |vo(?:u?s|tre) )")
_zEndOfNG2 = re.compile(r" +(\w[\w-]+)")
_zEndOfNG3 = re.compile(r" *, +(\w[\w-]+)")


def isEndOfNG (dDA, s, iOffset):
    if _zEndOfNG1.match(s):
        return True
    m = _zEndOfNG2.match(s)
    if m and morphex(dDA, (iOffset+m.start(1), m.group(1)), ":[VR]", ":[NAQP]"):
        return True
    m = _zEndOfNG3.match(s)
    if m and not morph(dDA, (iOffset+m.start(1), m.group(1)), ":[NA]", False):
        return True
    return False


#### Exceptions

aREGULARPLURAL = frozenset(["abricot", "amarante", "aubergine", "acajou", "anthracite", "brique", "caca", u"café", "carotte", "cerise", "chataigne", "corail", "citron", u"crème", "grave", "groseille", "jonquille", "marron", "olive", "pervenche", "prune", "sable"])
aSHOULDBEVERB = frozenset(["aller", "manger"]) 


#### GRAMMAR CHECKING ENGINE PLUGIN

#### Check date validity

_lDay = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_dMonth = { "janvier":1, u"février":2, "mars":3, "avril":4, "mai":5, "juin":6, "juillet":7, u"août":8, "aout":8, "septembre":9, "octobre":10, "novembre":11, u"décembre":12 }

import datetime

def checkDate (day, month, year):
    "to use if month is a number"
    try:
        return datetime.date(int(year), int(month), int(day))
    except ValueError:
        return False
    except:
        return True

def checkDateWithString (day, month, year):
    "to use if month is a noun"
    try:
        return datetime.date(int(year), _dMonth.get(month.lower(), ""), int(day))
    except ValueError:
        return False
    except:
        return True

def checkDay (weekday, day, month, year):
    "to use if month is a number"
    oDate = checkDate(day, month, year)
    if oDate and _lDay[oDate.weekday()] != weekday.lower():
        return False
    return True
        
def checkDayWithString (weekday, day, month, year):
    "to use if month is a noun"
    oDate = checkDate(day, _dMonth.get(month, ""), year)
    if oDate and _lDay[oDate.weekday()] != weekday.lower():
        return False
    return True

def getDay (day, month, year):
    "to use if month is a number"
    return _lDay[datetime.date(int(year), int(month), int(day)).weekday()]

def getDayWithString (day, month, year):
    "to use if month is a noun"
    return _lDay[datetime.date(int(year), _dMonth.get(month.lower(), ""), int(day)).weekday()]


#### GRAMMAR CHECKING ENGINE PLUGIN: Suggestion mechanisms

from . import conj
from . import mfsp


## verbs

def suggVerb (sFlex, sWho, funcSugg2=None):
    aSugg = set()
    for sStem in stem(sFlex):
        tTags = conj._getTags(sStem)
        if tTags:
            # we get the tense
            aTense = set()
            for sMorph in _dAnalyses.get(sFlex, []): # we don’t check if word exists in _dAnalyses, for it is assumed it has been done before
                for m in re.finditer(sStem+" .*?(:(?:Y|I[pqsf]|S[pq]|K))", sMorph):
                    # stem must be used in regex to prevent confusion between different verbs (e.g. sauras has 2 stems: savoir and saurer)
                    if m:
                        if m.group(1) == ":Y":
                            aTense.add(":Ip")
                            aTense.add(":Iq")
                            aTense.add(":Is")
                        else:
                            aTense.add(m.group(1))
            for sTense in aTense:
                if sWho == u":1ś" and not conj._hasConjWithTags(tTags, sTense, u":1ś"):
                    sWho = ":1s"
                if conj._hasConjWithTags(tTags, sTense, sWho):
                    aSugg.add(conj._getConjWithTags(sStem, tTags, sTense, sWho))
    if funcSugg2:
        aSugg2 = funcSugg2(sFlex)
        if aSugg2:
            aSugg.add(aSugg2)
    if aSugg:
        return u"|".join(aSugg)
    return ""


def suggVerbPpas (sFlex, sWhat=None):
    aSugg = set()
    for sStem in stem(sFlex):
        tTags = conj._getTags(sStem)
        if tTags:
            if not sWhat:
                aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q1"))
                aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q2"))
                aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q3"))
                aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q4"))
                aSugg.discard("")
            elif sWhat == ":m:s":
                aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q1"))
            elif sWhat == ":m:p":
                if conj._hasConjWithTags(tTags, ":PQ", ":Q2"):
                    aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q2"))
                else:
                    aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q1"))
            elif sWhat == ":f:s":
                if conj._hasConjWithTags(sStem, tTags, ":PQ", ":Q3"):
                    aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q3"))
                else:
                    aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q1"))
            elif sWhat == ":f:p":
                if conj._hasConjWithTags(sStem, tTags, ":PQ", ":Q4"):
                    aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q4"))
                else:
                    aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q1"))
            else:
                aSugg.add(conj._getConjWithTags(sStem, tTags, ":PQ", ":Q1"))
    if aSugg:
        return u"|".join(aSugg)
    return ""


def suggVerbInfi (sFlex):
    return u"|".join(stem(sFlex))


_dQuiEst = { "je": ":1s", u"j’": ":1s", u"j’en": ":1s", u"j’y": ":1s", \
             "tu": ":2s", "il": ":3s", "on": ":3s", "elle": ":3s", "nous": ":1p", "vous": ":2p", "ils": ":3p", "elles": ":3p" }
_lIndicatif = [":Ip", ":Iq", ":Is", ":If"]
_lSubjonctif = [":Sp", ":Sq"]

def suggVerbMode (sFlex, cMode, sSuj):
    if cMode == ":I":
        lMode = _lIndicatif
    elif cMode == ":S":
        lMode = _lSubjonctif
    elif cMode.startswith((":I", ":S")):
        lMode = [cMode]
    else:
        return ""
    sWho = _dQuiEst.get(sSuj.lower(), None)
    if not sWho:
        if sSuj[0:1].islower(): # pas un pronom, ni un nom propre
            return ""
        sWho = ":3s"
    aSugg = set()
    for sStem in stem(sFlex):
        tTags = conj._getTags(sStem)
        if tTags:
            for sTense in lMode:
                if conj._hasConjWithTags(tTags, sTense, sWho):
                    aSugg.add(conj._getConjWithTags(sStem, tTags, sTense, sWho))
    if aSugg:
        return u"|".join(aSugg)
    return ""


## Nouns and adjectives

def suggPlur (sFlex, sWordToAgree=None):
    "returns plural forms assuming sFlex is singular"
    if sWordToAgree:
        if sWordToAgree not in _dAnalyses and not _storeMorphFromFSA(sWordToAgree):
            return ""
        sGender = cr.getGender(_dAnalyses[sWordToAgree])
        if sGender == ":m":
            return suggMasPlur(sFlex)
        elif sGender == ":f":
            return suggFemPlur(sFlex)
    aSugg = set()
    if "-" not in sFlex:
        if sFlex.endswith("l"):
            if sFlex.endswith("al") and len(sFlex) > 2 and _oDict.isValid(sFlex[:-1]+"ux"):
                aSugg.add(sFlex[:-1]+"ux")
            if sFlex.endswith("ail") and len(sFlex) > 3 and _oDict.isValid(sFlex[:-2]+"ux"):
                aSugg.add(sFlex[:-2]+"ux")
        if _oDict.isValid(sFlex+"s"):
            aSugg.add(sFlex+"s")
        if _oDict.isValid(sFlex+"x"):
            aSugg.add(sFlex+"x")
    if mfsp.isMiscPlural(sFlex):
        aSugg.add(mfsp.getMiscPlural(sFlex))
    if aSugg:
        return u"|".join(aSugg)
    return ""


def suggSing (sFlex):
    "returns singular forms assuming sFlex is plural"
    if "-" in sFlex:
        return ""
    aSugg = set()
    if sFlex.endswith("ux"):
        if _oDict.isValid(sFlex[:-2]+"l"):
            aSugg.add(sFlex[:-2]+"l")
        if _oDict.isValid(sFlex[:-2]+"il"):
            aSugg.add(sFlex[:-2]+"il")
    if _oDict.isValid(sFlex[:-1]):
        aSugg.add(sFlex[:-1])
    if aSugg:
        return u"|".join(aSugg)
    return ""


def suggMasSing (sFlex):
    "returns masculine singular forms"
    # we don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    aSugg = set()
    for sMorph in _dAnalyses.get(sFlex, []):
        if not ":V" in sMorph:
            # not a verb
            if ":m" in sMorph or ":e" in sMorph:
                aSugg.add(suggSing(sFlex))
            else:
                sStem = cr.getLemmaOfMorph(sMorph)
                if mfsp.isFemForm(sStem):
                    aSugg.add(mfsp.getMasForm(sStem, False))
        else:
            # a verb
            sVerb = cr.getLemmaOfMorph(sMorph)
            if conj.hasConj(sVerb, ":PQ", ":Q1"):
                aSugg.add(conj.getConj(sVerb, ":PQ", ":Q1"))
    if aSugg:
        return u"|".join(aSugg)
    return ""


def suggMasPlur (sFlex):
    "returns masculine plural forms"
    # we don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    aSugg = set()
    for sMorph in _dAnalyses.get(sFlex, []):
        if not ":V" in sMorph:
            # not a verb
            if ":m" in sMorph or ":e" in sMorph:
                aSugg.add(suggPlur(sFlex))
            else:
                sStem = cr.getLemmaOfMorph(sMorph)
                if mfsp.isFemForm(sStem):
                    aSugg.add(mfsp.getMasForm(sStem, True))
        else:
            # a verb
            sVerb = cr.getLemmaOfMorph(sMorph)
            if conj.hasConj(sVerb, ":PQ", ":Q2"):
                aSugg.add(conj.getConj(sVerb, ":PQ", ":Q2"))
            elif conj.hasConj(sVerb, ":PQ", ":Q1"):
                aSugg.add(conj.getConj(sVerb, ":PQ", ":Q1"))
    if aSugg:
        return u"|".join(aSugg)
    return ""


def suggFemSing (sFlex):
    "returns feminine singular forms"
    # we don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    aSugg = set()
    for sMorph in _dAnalyses.get(sFlex, []):
        if not ":V" in sMorph:
            # not a verb
            if ":f" in sMorph or ":e" in sMorph:
                aSugg.add(suggSing(sFlex))
            else:
                sStem = cr.getLemmaOfMorph(sMorph)
                if mfsp.isFemForm(sStem):
                    aSugg.add(sStem)
        else:
            # a verb
            sVerb = cr.getLemmaOfMorph(sMorph)
            if conj.hasConj(sVerb, ":PQ", ":Q3"):
                aSugg.add(conj.getConj(sVerb, ":PQ", ":Q3"))
    if aSugg:
        return u"|".join(aSugg)
    return ""


def suggFemPlur (sFlex):
    "returns feminine plural forms"
    # we don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    aSugg = set()
    for sMorph in _dAnalyses.get(sFlex, []):
        if not ":V" in sMorph:
            # not a verb
            if ":f" in sMorph or ":e" in sMorph:
                aSugg.add(suggPlur(sFlex))
            else:
                sStem = cr.getLemmaOfMorph(sMorph)
                if mfsp.isFemForm(sStem):
                    aSugg.add(sStem+"s")
        else:
            # a verb
            sVerb = cr.getLemmaOfMorph(sMorph)
            if conj.hasConj(sVerb, ":PQ", ":Q4"):
                aSugg.add(conj.getConj(sVerb, ":PQ", ":Q4"))
    if aSugg:
        return u"|".join(aSugg)
    return ""


def switchGender (sFlex, bPlur=None):
    # we don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    aSugg = set()
    if bPlur == None:
        for sMorph in _dAnalyses.get(sFlex, []): 
            if ":f" in sMorph:
                if ":s" in sMorph:
                    aSugg.add(suggMasSing(sFlex))
                elif ":p" in sMorph:
                    aSugg.add(suggMasPlur(sFlex))
            elif ":m" in sMorph:
                if ":s" in sMorph:
                    aSugg.add(suggFemSing(sFlex))
                elif ":p" in sMorph:
                    aSugg.add(suggFemPlur(sFlex))
                else:
                    aSugg.add(suggFemSing(sFlex))
                    aSugg.add(suggFemPlur(sFlex))
    elif bPlur:
        for sMorph in _dAnalyses.get(sFlex, []):
            if ":f" in sMorph:
                aSugg.add(suggMasPlur(sFlex))
            elif ":m" in sMorph:
                aSugg.add(suggFemPlur(sFlex))
    else:
        for sMorph in _dAnalyses.get(sFlex, []):
            if ":f" in sMorph:
                aSugg.add(suggMasSing(sFlex))
            elif ":m" in sMorph:
                aSugg.add(suggFemSing(sFlex))

    if aSugg:
        return u"|".join(aSugg)
    return ""


def switchPlural (sFlex):
    # we don’t check if word exists in _dAnalyses, for it is assumed it has been done before
    aSugg = set()
    for sMorph in _dAnalyses.get(sFlex, []):
        if ":s" in sMorph:
            aSugg.add(suggPlur(sFlex))
        elif ":p" in sMorph:
            aSugg.add(suggSing(sFlex))
    if aSugg:
        return u"|".join(aSugg)
    return ""


def ceOrCet (s):
    if re.match("(?i)[aeéèêiouyâîï]", s):
        return "cet"
    if s[0:1] == "h" or s[0:1] == "H":
        return "ce|cet"
    return "ce"


def formatNumber (s):
    nLen = len(s)
    if nLen == 10:
        sRes = s[0] + u" " + s[1:4] + u" " + s[4:7] + u" " + s[7:]                                  # nombre ordinaire
        if s.startswith("0"):
            sRes += u"|" + s[0:2] + u" " + s[2:4] + u" " + s[4:6] + u" " + s[6:8] + u" " + s[8:]    # téléphone français
            if s[1] == "4" and (s[2]=="7" or s[2]=="8" or s[2]=="9"):
                sRes += u"|" + s[0:4] + u" " + s[4:6] + u" " + s[6:8] + u" " + s[8:]                # mobile belge
            sRes += u"|" + s[0:3] + u" " + s[3:6] + u" " + s[6:8] + u" " + s[8:]                    # téléphone suisse
        sRes += u"|" + s[0:4] + u" " + s[4:7] + "-" + s[7:]                                         # téléphone canadien ou américain
        return sRes
    elif nLen == 9:
        sRes = s[0:3] + u" " + s[3:6] + u" " + s[6:]                                                # nombre ordinaire
        if s.startswith("0"):
            sRes += "|" + s[0:3] + u" " + s[3:5] + u" " + s[5:7] + u" " + s[7:9]                    # fixe belge 1
            sRes += "|" + s[0:2] + u" " + s[2:5] + u" " + s[5:7] + u" " + s[7:9]                    # fixe belge 2
        return sRes
    elif nLen < 4:
        return ""
    sRes = ""
    nEnd = nLen
    while nEnd > 0:
        nStart = max(nEnd-3, 0)
        sRes = s[nStart:nEnd] + u" " + sRes  if sRes  else s[nStart:nEnd]
        nEnd = nEnd - 3
    return sRes


def formatNF (s):
    try:
        m = re.match(u"NF[  -]?(C|E|P|Q|S|X|Z|EN(?:[  -]ISO|))[  -]?([0-9]+(?:[/‑-][0-9]+|))", s)
        if not m:
            return ""
        return u"NF " + m.group(1).upper().replace(" ", u" ").replace("-", u" ") + u" " + m.group(2).replace("/", u"‑").replace("-", u"‑")
    except:
        traceback.print_exc()
        return "# erreur #"


def undoLigature (c):
    if c == u"ﬁ":
        return "fi"
    elif c == u"ﬂ":
        return "fl"
    elif c == u"ﬀ":
        return "ff"
    elif c == u"ﬃ":
        return "ffi"
    elif c == u"ﬄ":
        return "ffl"
    elif c == u"ﬅ":
        return "ft"
    elif c == u"ﬆ":
        return "st"
    return "_"



# generated code, do not edit
def p63_1 (s, m):
    return m.group(1).replace(".", "")+"."
def p64_1 (s, m):
    return m.group(0).replace(".", "")
def c66_1 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)etc", m.group(1))
def c87_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)(?:etc|[A-Z]|chap|cf|fig|hab|litt|circ|coll|ref|étym|suppl|bibl|bibliogr|cit|op|vol|déc|nov|oct|janv|juil|avr|sept)$", m.group(1)) and morph(dDA, (m.start(1), m.group(1)), ":") and morph(dDA, (m.start(2), m.group(2)), ":")
def e87_1 (s, m):
    return m.group(2).capitalize()
def c93_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":[DR]", False)
def c99_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":(?:M1|N)", ":G")
def c110_1 (s, sx, m, dDA, sCountry):
    return look(s[:m.start()],"[a-zéàùèê][.] ") and not look(s[:m.start()],"(?i)^(?:\\d|\\w[.])")
def c115_1 (s, sx, m, dDA, sCountry):
    return not m.group(1).isdigit()
def c118_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"(?i)etc$")
def e119_1 (s, m):
    return m.group(0).replace("...", u"…").rstrip(".")
def c124_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?:etc|[A-Z]|fig|hab|litt|circ|coll|ref|étym|suppl|bibl|bibliogr|cit|vol|déc|nov|oct|janv|juil|avr|sept)$", m.group(1))
def e133_1 (s, m):
    return m.group(0)[1]
def c143_1 (s, sx, m, dDA, sCountry):
    return sCountry != "CA"
def e160_1 (s, m):
    return undoLigature(m.group(0))
def c184_1 (s, sx, m, dDA, sCountry):
    return not option("mapos") and morph(dDA, (m.start(2), m.group(2)), ":V", False)
def e184_1 (s, m):
    return m.group(1)[:-1]+u"’"
def c187_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V", False)
def e187_1 (s, m):
    return m.group(1)[:-1]+u"’"
def c191_1 (s, sx, m, dDA, sCountry):
    return option("mapos") and not look(s[:m.start()],u"(?i)(?:lettre|caractère|glyphe|dimension|variable|fonction|point) *$")
def e191_1 (s, m):
    return m.group(1)[:-1]+u"’"
def c197_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"onz[ei]|énième|iourte|ouistiti|one-?step|Ouagadougou|I(?:I|V|X|er|ᵉʳ|ʳᵉ|è?re)", m.group(2)) and not m.group(2).isupper() and not morph(dDA, (m.start(2), m.group(2)), ":G", False)
def e197_1 (s, m):
    return m.group(1)[0]+u"’"
def c200_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)(?:onz|énième)", m.group(2)) and morph(dDA, (m.start(2), m.group(2)), ":[me]")
def c207_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"NF (?:C|E|P|Q|S|X|Z|EN(?: ISO|)) [0-9]+(?:‑[0-9]+|)", m.group(0))
def e207_1 (s, m):
    return formatNF(m.group(0))
def e212_1 (s, m):
    return m.group(0).replace("2", u"₂").replace("3", u"₃").replace("4", u"₄")
def c219_1 (s, sx, m, dDA, sCountry):
    return option("typo") and not m.group(0).endswith(u"·e·s")
def c219_2 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False)
def d219_2 (s, m, dDA):
    return define(dDA, m.start(0), ":N:A:Q:e:i")
def c228_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"NF[  -]?(C|E|P|Q|X|Z|EN(?:[  -]ISO|)) *")
def e228_1 (s, m):
    return formatNumber(m.group(0))
def e233_1 (s, m):
    return m.group(0).replace("O", "0")
def e234_1 (s, m):
    return m.group(0).replace("O", "0")
def c244_1 (s, sx, m, dDA, sCountry):
    return not checkDate(m.group(1),m.group(2),m.group(3)) and not look(s[:m.start()],"(?i)\\bversions? +$")
def c247_1 (s, sx, m, dDA, sCountry):
    return not checkDateWithString(m.group(1),m.group(2),m.group(3))
def c250_1 (s, sx, m, dDA, sCountry):
    return not checkDay(m.group(1),m.group(2),m.group(3),m.group(4))
def e250_1 (s, m):
    return getDay(m.group(2),m.group(3),m.group(4))
def c253_1 (s, sx, m, dDA, sCountry):
    return not checkDayWithString(m.group(1),m.group(2),m.group(3),m.group(4))
def e253_1 (s, m):
    return getDayWithString(m.group(2),m.group(3),m.group(4))
def c283_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0", False) or m.group(1) == "en"
def c286_1 (s, sx, m, dDA, sCountry):
    return _oDict.isValid(m.group(1)+"-"+m.group(2)) and analyse(m.group(1)+"-"+m.group(2), ":", False)
def c289_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NB]", False)
def c290_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NB]", False) and not nextword1(s, m.end())
def c293_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":N") and not re.match(u"(?i)(?:aequo|nihilo|cathedra|absurdo|abrupto)", m.group(1))
def c295_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False)
def c296_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":N", ":[AGW]")
def c299_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False)
def c301_1 (s, sx, m, dDA, sCountry):
    return _oDict.isValid(m.group(1)+"-"+m.group(2)) and analyse(m.group(1)+"-"+m.group(2), ":", False)
def c305_1 (s, sx, m, dDA, sCountry):
    return _oDict.isValid(m.group(1)+"-"+m.group(2)) and analyse(m.group(1)+"-"+m.group(2), ":", False) and morph(dDA, prevword1(s[:m.start()]), ":D", False, not bool(re.match("(?i)s(?:ans|ous)$",m.group(1))))
def c309_1 (s, sx, m, dDA, sCountry):
    return _oDict.isValid(m.group(1)+"-"+m.group(2)) and analyse(m.group(1)+"-"+m.group(2), ":N", False) and morph(dDA, prevword1(s[:m.start()]), ":(?:D|V0e)", False, True) and not (morph(dDA, (m.start(1), m.group(1)), ":G", False) and morph(dDA, (m.start(2), m.group(2)), ":[GYB]", False))
def e316_1 (s, m):
    return m.group(0).replace(" ", "-")
def e317_1 (s, m):
    return m.group(0).replace(" ", "-")
def c328_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, prevword1(s[:m.start()]), ":Cs", False, True)
def e333_1 (s, m):
    return m.group(0).replace(" ", "-")
def c339_1 (s, sx, m, dDA, sCountry):
    return not nextword1(s, m.end())
def c341_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, prevword1(s[:m.start()]), ":G")
def c345_1 (s, sx, m, dDA, sCountry):
    return look(s[:m.start()],"(?i)\\b(?:les?|du|des|un|ces?|[mts]on) +")
def c352_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":D", False)
def c354_1 (s, sx, m, dDA, sCountry):
    return not ( morph(dDA, prevword1(s[:m.start()]), ":R", False) and look(s[m.end():],"^ +qu[e’]") )
def e400_1 (s, m):
    return m.group(0).replace(" ", "-")
def c402_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"(?i)quatre $")
def e402_1 (s, m):
    return m.group(0).replace(" ", "-").replace("vingts", "vingt")
def e404_1 (s, m):
    return m.group(0).replace(" ", "-")
def e406_1 (s, m):
    return m.group(0).replace(" ", "-").replace("vingts", "vingt")
def c417_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False, False)
def c429_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), u":(?:G|V0)|>(?:t(?:antôt|emps|rès)|loin|souvent|parfois|quelquefois|côte|petit) ", False) and not m.group(1)[0].isupper()
def p440_1 (s, m):
    return m.group(0).replace(u"‑", "")
def p441_1 (s, m):
    return m.group(0).replace(u"‑", "")
def c469_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(0), m.group(0)), ":", False)
def c472_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False)
def c473_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":A", False) and not morph(dDA, prevword1(s[:m.start()]), ":D", False)
def c498_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":(?:O[sp]|X)", False)
def d498_1 (s, m, dDA):
    return select(dDA, m.start(1), m.group(1), ":V")
def d500_1 (s, m, dDA):
    return select(dDA, m.start(1), m.group(1), ":V")
def c501_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":[YD]", False)
def d501_1 (s, m, dDA):
    return exclude(dDA, m.start(1), m.group(1), ":V")
def d502_1 (s, m, dDA):
    return exclude(dDA, m.start(1), m.group(1), ":V")
def c503_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":Y", False)
def d503_1 (s, m, dDA):
    return exclude(dDA, m.start(1), m.group(1), ":V")
def c513_1 (s, sx, m, dDA, sCountry):
    return option("mapos")
def e513_1 (s, m):
    return m.group(1)[:-1]+"’"
def c520_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[GNAY]", ":Q|>(?:priori|post[eé]riori|contrario|capella) ")
def c534_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":N.*:f:s")
def c537_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":A.*:f", False)
def c545_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)([nv]ous|faire|en|la|lui|donnant|œuvre|h[éo]|olé|joli|Bora|couvent|dément|sapiens|très|vroum|[0-9]+)$", m.group(1)) and not (re.match("(?:est|une?)$", m.group(1)) and look(s[:m.start()],u"[’']$")) and not (m.group(1) == "mieux" and look(s[:m.start()],"(?i)qui +$"))
def c572_1 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)avoir$", m.group(1)) and morph(dDA, (m.start(1), m.group(1)), ">avoir ", False)
def c580_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">(?:être|mettre) ", False)
def c601_1 (s, sx, m, dDA, sCountry):
    return not look_chk1(dDA, s[m.end():], m.end()," \w[\w-]+ en ([aeo]\w*)", ":V0a")
def c617_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">abolir ", False)
def c619_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">achever ", False)
def c620_1 (s, sx, m, dDA, sCountry):
    return not look(s[m.end():],r" +de?\b")
def c629_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, prevword1(s[:m.start()]), ":A|>un", False)
def c635_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">comparer ")
def c636_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">contraindre ", False)
def c647_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">joindre ")
def c673_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">suffire ")
def c674_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">talonner ")
def c681_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:prévenir|prévoir|prédire|présager|préparer|pressentir|pronostiquer|avertir|devancer|réserver) ", False)
def c686_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:ajourner|différer|reporter) ", False)
def c701_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V.*:(?:Y|[123][sp])") and m.group(2)[0].islower() and not re.match(r"(?i)quelques? soi(?:ent|t|s)\b", m.group(0))
def c705_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V.*:(?:Y|[123][sp])", ":N.*:[fe]|:[AW]") and m.group(2)[0].islower() or m.group(2) == "va"
def c709_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V.*:(?:Y|[123][sp])") and m.group(1)[0].islower() and not prevword1(s[:m.start()])
def c713_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[123][sp]", ":[NAQ]")
def c717_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[me]", ":[YG]") and m.group(2)[0].islower()
def c721_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Y|[123][sp])") and not look(s[:m.start()],"(?i)(?:dont|sauf) +$")
def c725_1 (s, sx, m, dDA, sCountry):
    return m.group(1)[0].islower() and morph(dDA, (m.start(1), m.group(1)), ":V.*:[123][sp]")
def c728_1 (s, sx, m, dDA, sCountry):
    return m.group(1)[0].islower() and morphex(dDA, (m.start(1), m.group(1)), ":V.*:[123][sp]", ":[GNA]")
def c731_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V.*:[123][sp]") and m.group(1)[0].islower()
def c739_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":P", False)
def c740_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]")
def c746_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":(?:[123][sp]|Y|P|O[on]|X)|>(?:[lmts]|surtout|guère) ", False) and not re.search("(?i)-(?:ils?|elles?|[nv]ous|je|tu|on|ce)$", m.group(2))
def c749_1 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)se que?", m.group(0)) and not morph(dDA, (m.start(2), m.group(2)), ":(?:[123][sp]|Y|P|Oo)|>[lmts] ", False) and not re.search("(?i)-(?:ils?|elles?|[nv]ous|je|tu|on|ce)$", m.group(2))
def c753_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":(?:[123][sp]|Y|P|Oo)", False) and not re.search("(?i)-(?:ils?|elles?|[nv]ous|je|tu|on|ce)$", m.group(2))
def c756_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":(?:[123][sp]|Y|P|O[onw]|X)", False) and not re.search("(?i)-(?:ils?|elles?|[nv]ous|je|tu|on|ce)$", m.group(2))
def c759_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":(?:[123][sp]|Y|P)|>(?:en|y|ils?) ", False) and not re.search("(?i)-(?:ils?|elles?|[nv]ous|je|tu|on|ce)$", m.group(2))
def c762_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":(?:[123][sp]|Y|P)|>(?:en|y|ils?|elles?) ", False) and not re.search("(?i)-(?:ils?|elles?|[nv]ous|je|tu|on|ce)$", m.group(2))
def c765_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":[123][sp]|>(?:en|y) ", False) and not re.search("(?i)-(?:ils?|elles?|[nv]ous|je|tu|on|dire)$", m.group(2))
def c771_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":W", False) and morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":[GAQW]")
def c775_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":(?:Y|[123][sp])", ":[GAQW]")
def c779_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[123][sp]", ":(?:G|N|A|Q|W|M[12])")
def c783_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[123][sp]", ":(?:G|N|A|Q|W|M[12]|T)")
def c787_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":(?:Y|[123][sp])", ":[GAQW]") and not morph(dDA, prevword1(s[:m.start()]), ":V[123].*:[123][sp]", False, False)
def c793_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, prevword1(s[:m.start()]), ":[VN]", False, True)
def c794_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()])
def c797_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"(?i)\\b(?:[lmts]a|leur|une|en) +$")
def c799_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">être ") and not look(s[:m.start()],r"(?i)\bce que? ")
def c818_1 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)(?:côtés?|coups?|peu(?:-près|)|pics?|propos|valoir|plat-ventrismes?)", m.group(2))
def c818_2 (s, sx, m, dDA, sCountry):
    return re.match("(?i)(?:côtés?|coups?|peu(?:-pr(?:ès|êts?|és?)|)|pics?|propos|valoir|plat-ventrismes?)", m.group(2))
def c823_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":3s", False, False)
def c826_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":(?:3s|R)", False, False) and not morph(dDA, nextword1(s, m.end()), ":Oo", False)
def c831_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":Q", ":M[12P]")
def c834_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ]", ":Y")
def c838_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ]", ":Y")
def c845_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"(?i)\bce que?\b")
def c847_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":(?:M[12]|D|Oo)")
def c850_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[123][sp]", True) and not m.group(2)[0:1].isupper()
def c853_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"(?i)[ln]’$|(?<!-)\\b(?:il|elle|on|y|n’en) +$")
def c856_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"(?i)(\\bque?\\b|[ln]’$|(?<!-)\\b(?:il|elle|on|y|n’en) +$)")
def c859_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"(?i)(\\bque?\\b|[ln]’$|(?<!-)\\b(?:il|elle|on|y|n’en) +$)")
def c862_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":Y", False) and not look(s[:m.start()],u"(?i)\\bque? |(?:il|elle|on|n’(?:en|y)) +$")
def c869_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()])
def c874_1 (s, sx, m, dDA, sCountry):
    return not nextword1(s, m.end()) or look(s[m.end():],"(?i)^ +que? ")
def c875_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":G", u">(?:tr(?:ès|op)|peu|bien|plus|moins) |:[NAQ].*:f")
def c879_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f") and not re.match("seule?s?", m.group(2))
def c881_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"(?i)\\b(?:oh|ah) +$")
def c883_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":R")
def c887_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ]", ":([123][sp]|Y|P|Q)|>l[ea]? ")
def c889_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":Y")  and m.group(1) != "CE"
def c891_1 (s, sx, m, dDA, sCountry):
    return (m.group(2).startswith(",") or morphex(dDA, (m.start(3), m.group(3)), ":G", ":[AYD]"))
def c894_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V[123].*:(?:Y|[123][sp])") and not morph(dDA, (m.start(2), m.group(2)), ">(?:devoir|pouvoir) ") and m.group(2)[0].islower() and m.group(1) != "CE"
def c901_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V", ":[NAQ].*:[me]") or look(s[:m.start()],"(?i)\\b[cs]e +")
def c904_1 (s, sx, m, dDA, sCountry):
    return look(s[m.end():],"^ +[ldmtsc]es ") or ( morph(dDA, prevword1(s[:m.start()]), ":Cs", False, True) and not look(s[:m.start()],", +$") and not look(s[m.end():],r"^ +(?:ils?|elles?)\b") and not morph(dDA, nextword1(s, m.end()), ":Q", False, False) )
def c910_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":N.*:s", ":A.*:[pi]")
def c920_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":N.*:p", ":(?:G|W|A.*:[si])")
def c925_1 (s, sx, m, dDA, sCountry):
    return m.group(1).endswith("en") or look(s[:m.start()],"^ *$")
def c931_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()])
def c934_1 (s, sx, m, dDA, sCountry):
    return not m.group(1).startswith("B")
def c942_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":E|>le ", False, False)
def c947_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":(?:[123][sp]|Y)", ":(?:G|N|A|M[12P])") and not look(s[:m.start()],r"(?i)\bles *$")
def c955_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":W", False) and not morph(dDA, prevword1(s[:m.start()]), ":V.*:3s", False, False)
def e960_1 (s, m):
    return m.group(1).replace("pal", u"pâl")
def e963_1 (s, m):
    return m.group(1).replace("pal", u"pâl")
def c970_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":[AQ]", False)
def c976_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ]", ":(?:G|[123][sp]|W)")
def e976_1 (s, m):
    return m.group(1).replace(" ", "")
def c981_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False)
def c986_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()]) and morph(dDA, (m.start(2), m.group(2)), ":V", False)
def c989_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()]) and morph(dDA, (m.start(2), m.group(2)), ":V", False) and not ( m.group(1) == "sans" and morph(dDA, (m.start(2), m.group(2)), ":[NY]", False) )
def c1007_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[AQ].*:[pi]", False)
def c1011_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"(?i)\\b(?:d[eu]|avant|après|sur|malgré) +$")
def c1013_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"(?i)\\b(?:d[eu]|avant|après|sur|malgré) +$")
def c1018_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":f") and not look(s[:m.start()],u"(?i)(?:à|pas|de|[nv]ous|eux) +$")
def c1020_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":m") and not look(s[:m.start()],u"(?i)(?:à|pas|de|[nv]ous|eux) +$")
def c1023_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":N.*:[fp]", ":(?:A|W|G|M[12P]|Y|[me]:i)") and morph(dDA, prevword1(s[:m.start()]), ":R|>de ", False, True)
def e1023_1 (s, m):
    return suggMasSing(m.group(1))
def c1027_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[mp]") and morph(dDA, prevword1(s[:m.start()]), ":R|>de ", False, True)
def e1027_1 (s, m):
    return suggFemSing(m.group(1))
def c1031_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[fs]") and morph(dDA, prevword1(s[:m.start()]), ":R|>de ", False, True)
def e1031_1 (s, m):
    return suggMasPlur(m.group(1))
def c1035_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[ms]") and morph(dDA, prevword1(s[:m.start()]), ":R|>de ", False, True)
def e1035_1 (s, m):
    return suggFemPlur(m.group(1))
def c1044_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[123][sp]", False) and not (re.match("(?i)(?:jamais|rien)$", m.group(3)) and look(s[:m.start()],"\\b(?:que?|plus|moins)\\b"))
def c1048_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[123][sp]", False) and not (re.match("(?i)(?:jamais|rien)$", m.group(3)) and look(s[:m.start()],"\\b(?:que?|plus|moins)\\b"))
def c1052_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":[123][sp]", False) and not (re.match("(?i)(?:jamais|rien)$", m.group(3)) and look(s[:m.start()],"\\b(?:que?|plus|moins)\\b"))
def c1056_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":[123][sp]", False) and not (re.match("(?i)(?:jamais|rien)$", m.group(3)) and look(s[:m.start()],"\\b(?:que?|plus|moins)\\b"))
def c1063_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V", False)
def c1080_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":[NAQ]", False)
def c1314_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ]", ":G")
def c1321_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def c1332_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)(?:janvier|février|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|décembre|vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor)s?$", m.group(3))
def c1364_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">faire ", False)
def c1365_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">faire ", False)
def c1381_1 (s, sx, m, dDA, sCountry):
    return m.group(2).isdigit() or morph(dDA, (m.start(2), m.group(2)), ":B", False)
def c1393_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">prendre ", False)
def c1401_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:sembler|para[îi]tre) ") and morphex(dDA, (m.start(3), m.group(3)), ":A", ":G")
def c1404_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">tenir ", False)
def c1406_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">trier ", False)
def c1408_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">venir ", False)
def c1422_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]", ":(?:G|3p)")
def c1427_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]", ":(?:G|3p)")
def c1434_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":B", False)
def c1435_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, prevword1(s[:m.start()]), ":V0", False) or not morph(dDA, nextword1(s, m.end()), ":A", False)
def c1436_1 (s, sx, m, dDA, sCountry):
    return isEndOfNG(dDA, s[m.end():], m.end())
def c1437_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":W", False)
def c1438_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":A .*:m:s", False)
def c1440_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, prevword1(s[:m.start()]), ":(?:R|C[sc])", False, True)
def c1441_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":B", False) or re.match("(?i)(?:plusieurs|maintes)", m.group(1))
def c1442_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, nextword1(s, m.end()), ":[NAQ]", False, True)
def c1443_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ]", ":V0")
def c1445_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":D", False)
def c1446_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":D.*:[me]:[si]", False)
def c1447_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">(?:croire|devoir|estimer|imaginer|penser) ")
def c1448_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:R|D|[123]s|X)", False)
def c1449_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False, False)
def c1450_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"(?i)\\bt(?:u|oi qui)\\b")
def c1451_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False, False)
def c1452_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":A", False)
def c1453_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False, False)
def c1454_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":W", False)
def c1455_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[AW]", ":G")
def c1456_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[AW]", False)
def c1457_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":Y", False)
def c1460_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NV]", ":D")
def c1461_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":(?:3s|X)", False)
def c1462_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":[me]", False)
def c1466_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":M[12]", False) and (morph(dDA, (m.start(2), m.group(2)), ":(?:M[12]|V)", False) or not _oDict.isValid(m.group(2)))
def c1467_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":M", False) and morph(dDA, (m.start(2), m.group(2)), ":M", False)
def c1468_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":M", False)
def c1469_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:M[12]|N)") and morph(dDA, (m.start(2), m.group(2)), ":(?:M[12]|N)")
def c1470_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:N|MP)") and m.group(1) != u"République"
def c1471_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":M[12]", False)
def c1472_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":M[12]", False)
def c1475_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[MT]", False) and morph(dDA, prevword1(s[:m.start()]), ":Cs", False, True) and not look(s[:m.start()],u"\\b(?:plus|moins|aussi) .* que +$")
def p1475_1 (s, m):
    return rewriteSubject(m.group(1),m.group(2))
def c1480_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False)
def c1482_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False)
def c1484_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:V0e|N)", False) and morph(dDA, (m.start(3), m.group(3)), ":[AQ]", False)
def c1485_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0", False)
def c1486_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0", False) and morph(dDA, (m.start(3), m.group(3)), ":[QY]", False)
def c1488_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False)
def c1490_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and morph(dDA, (m.start(3), m.group(3)), ":B", False) and morph(dDA, (m.start(4), m.group(4)), ":(?:Q|V1.*:Y)", False)
def c1494_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V", False)
def c1495_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V[123]")
def c1496_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V[123]", False)
def c1497_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V", False)
def c1500_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":G")
def c1503_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[me]", ":G") and morph(dDA, (m.start(3), m.group(3)), ":[AQ].*:[me]", False)
def c1505_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[fe]", ":G") and morph(dDA, (m.start(3), m.group(3)), ":[AQ].*:[fe]", False)
def c1507_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[pi]", ":[123][sp]") and morph(dDA, (m.start(3), m.group(3)), ":[AQ].*:[pi]", False)
def c1510_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[AW]")
def c1512_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[AW]", False)
def c1514_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[AQ]", False)
def c1515_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":W", ":3p")
def c1517_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[AW]", ":[123][sp]")
def c1522_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False) and morph(dDA, (m.start(3), m.group(3)), ":W", False) and morph(dDA, (m.start(4), m.group(4)), ":[AQ]", False)
def c1524_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False, True)
def c1525_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), r":W\b")
def c1528_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False)
def c1532_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:N|A|Q|V0e)", False)
def c1582_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and morphex(dDA, (m.start(1), m.group(1)), ":Q", ":G")
def d1582_1 (s, m, dDA):
    return exclude(dDA, m.start(2), m.group(2), ":A")
def c1589_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":1s", False, False)
def c1590_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":2s", False, False)
def c1591_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":3s", False, False)
def c1592_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":1p", False, False)
def c1593_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":2p", False, False)
def c1594_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":3p", False, False)
def c1595_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[123][sp]")
def c1601_1 (s, sx, m, dDA, sCountry):
    return isAmbiguousNAV(m.group(3)) and morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False)
def c1604_1 (s, sx, m, dDA, sCountry):
    return isAmbiguousNAV(m.group(3)) and morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False) and not re.match("[dD](?:’une?|e la) ", m.group(0))
def c1607_1 (s, sx, m, dDA, sCountry):
    return isAmbiguousNAV(m.group(3)) and ( morphex(dDA, (m.start(1), m.group(1)), ":[NAQ]", ":3[sp]") or (morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False) and not prevword1(s[:m.start()])) )
def c1620_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":(?:G|V0)", False)
def c1629_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ]", False)
def c1631_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ]", False)
def c1633_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", False)
def c1641_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":(?:e|m|P|G|W|[123][sp]|Y)")
def c1644_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f", ":(?:e|m|P|G|W|[123][sp]|Y)") or ( morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f", ":[me]") and morphex(dDA, (m.start(1), m.group(1)), ":R", ">(?:e[tn]|ou) ") and not (morph(dDA, (m.start(1), m.group(1)), ":Rv", False) and morph(dDA, (m.start(3), m.group(3)), ":Y", False)) )
def c1648_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":(?:e|m|P|G|W|Y)")
def c1652_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":[GWme]")
def c1655_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":(?:e|m|G|W|V0|3s)")
def c1658_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":(?:e|m|G|W|P)")
def c1661_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":[GWme]")
def c1664_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":[GWme]")
def c1667_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f:s", ":[GWme]")
def c1671_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":(?:e|f|P|G|W|[1-3][sp]|Y)")
def c1674_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m", ":(?:e|f|P|G|W|[1-3][sp]|Y)") or ( morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m", ":[fe]") and morphex(dDA, (m.start(1), m.group(1)), ":[RC]", ">(?:e[tn]|ou) ") and not (morph(dDA, (m.start(1), m.group(1)), ":(?:Rv|C)", False) and morph(dDA, (m.start(3), m.group(3)), ":Y", False)) )
def c1678_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":[efPGWY]")
def c1682_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":[efGW]")
def c1685_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":(?:e|f|G|W|V0|3s|P)") and not ( m.group(2) == "demi" and morph(dDA, nextword1(s, m.end()), ":N.*:f") )
def c1688_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":(?:e|f|G|W|V0|3s)")
def c1691_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":[efGWP]")
def c1694_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":[efGW]")
def c1697_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":[efGW]")
def e1697_1 (s, m):
    return ceOrCet(m.group(2))
def c1701_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f", ":[GWme]")
def c1704_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f", ":[eGW]")
def c1707_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m", ":[efGW]")
def c1712_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":[efGW]")
def c1718_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s") and not (look(s[m.end():]," +(?:et|ou) ") and morph(dDA, nextword(s, m.end(),2), ":[NAQ]", True, False))) or m.group(1) in aREGULARPLURAL
def e1718_1 (s, m):
    return suggPlur(m.group(1))
def c1723_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s") or (morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[pi]|>avoir") and morphex(dDA, (m.start(1), m.group(1)), ":[RC]", ">(?:e[tn]|ou) ") and not (morph(dDA, (m.start(1), m.group(1)), ":Rv", False) and morph(dDA, (m.start(2), m.group(2)), ":Y", False)))) and not (look(s[m.end():]," +(?:et|ou) ") and morph(dDA, nextword(s, m.end(),2), ":[NAQ]", True, False))
def e1723_1 (s, m):
    return suggPlur(m.group(2))
def c1727_1 (s, sx, m, dDA, sCountry):
    return (morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s", ":[ipYPGW]") and not (look(s[m.end():]," +(?:et|ou) ") and morph(dDA, nextword(s, m.end(),2), ":[NAQ]", True, False))) or m.group(1) in aREGULARPLURAL
def e1727_1 (s, m):
    return suggPlur(m.group(1))
def c1732_1 (s, sx, m, dDA, sCountry):
    return (morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[ipGW]") and not (look(s[m.end():]," +(?:et|ou) ") and morph(dDA, nextword(s, m.end(),2), ":[NAQ]", True, False))) or m.group(2) in aREGULARPLURAL
def e1732_1 (s, m):
    return suggPlur(m.group(2))
def c1737_1 (s, sx, m, dDA, sCountry):
    return (morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s", ":[ipPGW]") and not (look(s[m.end():]," +(?:et|ou) ") and morph(dDA, nextword(s, m.end(),2), ":[NAQ]", True, False))) or m.group(1) in aREGULARPLURAL
def e1737_1 (s, m):
    return suggPlur(m.group(1))
def c1743_1 (s, sx, m, dDA, sCountry):
    return (morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s", ":[ip]") and morphex(dDA, prevword1(s[:m.start()]), ":(?:G|[123][sp])", ":[AD]", True)) or m.group(1) in aREGULARPLURAL
def e1743_1 (s, m):
    return suggPlur(m.group(1))
def c1748_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[ip]") or m.group(2) in aREGULARPLURAL
def e1748_1 (s, m):
    return suggPlur(m.group(2))
def c1752_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[ip]") or m.group(2) in aREGULARPLURAL
def e1752_1 (s, m):
    return suggPlur(m.group(2))
def c1756_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p", ":[123][sp]|:[si]")
def e1756_1 (s, m):
    return suggSing(m.group(1))
def c1760_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p")
def e1760_1 (s, m):
    return suggSing(m.group(1))
def c1763_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p") or ( morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[si]") and morphex(dDA, (m.start(1), m.group(1)), ":[RC]", ">(?:e[tn]|ou)") and not (morph(dDA, (m.start(1), m.group(1)), ":Rv", False) and morph(dDA, (m.start(2), m.group(2)), ":Y", False)) )
def e1763_1 (s, m):
    return suggSing(m.group(2))
def c1767_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p", ":[siGW]")
def e1767_1 (s, m):
    return suggSing(m.group(1))
def c1771_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[siGW]")
def e1771_1 (s, m):
    return suggSing(m.group(2))
def c1775_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[siGW]")
def c1779_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[siG]")
def c1783_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p", ":[siGW]") and not morph(dDA, prevword(s[:m.start()],2), ":B", False)
def e1783_1 (s, m):
    return suggSing(m.group(1))
def c1787_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s") and not re.match(u"(?i)(janvier|février|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|décembre|rue|route|ruelle|place|boulevard|avenue|allée|chemin|sentier|square|impasse|cour|quai|chaussée|côte|vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor)$", m.group(2))) or m.group(2) in aREGULARPLURAL
def e1787_1 (s, m):
    return suggPlur(m.group(2))
def c1793_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s") and not morph(dDA, prevword1(s[:m.start()]), ":N", False) and not re.match(u"(?i)(janvier|février|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|décembre|rue|route|ruelle|place|boulevard|avenue|allée|chemin|sentier|square|impasse|cour|quai|chaussée|côte|vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor)$", m.group(2))) or m.group(2) in aREGULARPLURAL
def e1793_1 (s, m):
    return suggPlur(m.group(2))
def c1799_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s") or m.group(1) in aREGULARPLURAL) and not look(s[:m.start()],"(?i)\\b(?:le|un|ce|du) +$")
def e1799_1 (s, m):
    return suggPlur(m.group(1))
def c1803_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p") and not re.match(u"(?i)(janvier|février|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|décembre|rue|route|ruelle|place|boulevard|avenue|allée|chemin|sentier|square|impasse|cour|quai|chaussée|côte|vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor|Rois|Corinthiens|Thessaloniciens)$", m.group(1))
def e1803_1 (s, m):
    return suggSing(m.group(1))
def c1807_1 (s, sx, m, dDA, sCountry):
    return (m.group(1) != "1" and m.group(1) != "0" and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s") and not re.match(u"(?i)(janvier|février|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|décembre|rue|route|ruelle|place|boulevard|avenue|allée|chemin|sentier|square|impasse|cour|quai|chaussée|côte|vendémiaire|brumaire|frimaire|nivôse|pluviôse|ventôse|germinal|floréal|prairial|messidor|thermidor|fructidor)$", m.group(2))) or m.group(1) in aREGULARPLURAL
def e1807_1 (s, m):
    return suggPlur(m.group(2))
def c1815_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f:p", ":V0e")
def c1815_2 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m:p", ":V0e")
def c1815_3 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f:[si]", ":V0e")
def c1819_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f:s", ":V0e")
def c1819_2 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":V0e")
def c1819_3 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":V0e")
def c1823_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m:p", ":V0e")
def c1823_2 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f:p", ":V0e")
def c1823_3 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m:[si]", ":V0e")
def c1827_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m:s", ":V0e")
def c1827_2 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":V0e")
def c1827_3 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":V0e")
def c1832_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"\btel(?:le|)s? +$")
def c1835_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"\btel(?:le|)s? +$")
def e1835_1 (s, m):
    return m.group(1)[:-1]
def c1839_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"\btel(?:le|)s? +$") and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f", ":[mi]")
def c1843_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"\btel(?:le|)s? +$") and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m", ":[fi]")
def c1847_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"\btel(?:le|)s? +$") and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f", ":[mi]")
def c1851_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"\btel(?:le|)s? +$") and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m", ":[fi]")
def c1858_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">trouver ", False) and morphex(dDA, (m.start(3), m.group(3)), ":A.*:(?:f|m:p)", ":(?:G|3[sp]|M[12P])")
def e1858_1 (s, m):
    return suggMasSing(m.group(3))
def c1867_1 (s, sx, m, dDA, sCountry):
    return ((morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:m") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f")) or (morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:f") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m"))) and not apposition(m.group(1), m.group(2))
def e1867_1 (s, m):
    return switchGender(m.group(2))
def c1867_2 (s, sx, m, dDA, sCountry):
    return ((morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p")) or (morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s"))) and not apposition(m.group(1), m.group(2))
def e1867_2 (s, m):
    return switchPlural(m.group(2))
def c1875_1 (s, sx, m, dDA, sCountry):
    return ((morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:m") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f")) or (morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:f") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m"))) and not apposition(m.group(1), m.group(2)) and morph(dDA, prevword1(s[:m.start()]), ":[VRX]", True, True)
def e1875_1 (s, m):
    return switchGender(m.group(2))
def c1875_2 (s, sx, m, dDA, sCountry):
    return ((morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s")) or (morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p"))) and not apposition(m.group(1), m.group(2)) and morph(dDA, prevword1(s[:m.start()]), ":[VRX]", True, True)
def e1875_2 (s, m):
    return switchPlural(m.group(2))
def c1887_1 (s, sx, m, dDA, sCountry):
    return ((morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:m", ":[GYfe]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f")) or (morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:f", ":[GYme]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m"))) and not apposition(m.group(1), m.group(2)) and morph(dDA, prevword1(s[:m.start()]), ":[VRX]", True, True)
def e1887_1 (s, m):
    return switchGender(m.group(2))
def c1887_2 (s, sx, m, dDA, sCountry):
    return ((morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p", ":[GYsi]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s")) or (morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s", ":[GYpi]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p"))) and not apposition(m.group(1), m.group(2)) and morph(dDA, prevword1(s[:m.start()]), ":[VRX]", True, True)
def e1887_2 (s, m):
    return switchPlural(m.group(2))
def c1899_1 (s, sx, m, dDA, sCountry):
    return ((morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:m", ":[Gfe]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f")) or (morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:f", ":[Gme]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m"))) and not apposition(m.group(1), m.group(2)) and morph(dDA, prevword1(s[:m.start()]), ":[VRX]", True, True)
def e1899_1 (s, m):
    return switchGender(m.group(2))
def c1899_2 (s, sx, m, dDA, sCountry):
    return ((morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p", ":[Gsi]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s")) or (morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s", ":[Gpi]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p"))) and not apposition(m.group(1), m.group(2)) and morph(dDA, prevword1(s[:m.start()]), ":[VRX]", True, True)
def e1899_2 (s, m):
    return switchPlural(m.group(2))
def c1914_1 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)air$", m.group(1)) and not m.group(2).startswith("seul") and ((morph(dDA, (m.start(1), m.group(1)), ":m") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f")) or (morph(dDA, (m.start(1), m.group(1)), ":f") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m"))) and not apposition(m.group(1), m.group(2)) and not look(s[:m.start()],r"\b(et|ou|de) +$")
def e1914_1 (s, m):
    return switchGender(m.group(2), False)
def c1914_2 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)air$", m.group(1)) and not m.group(2).startswith("seul") and morph(dDA, (m.start(1), m.group(1)), ":[si]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p") and not apposition(m.group(1), m.group(2)) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e1914_2 (s, m):
    return suggSing(m.group(2))
def c1923_1 (s, sx, m, dDA, sCountry):
    return not m.group(2).startswith("seul") and ((morph(dDA, (m.start(1), m.group(1)), ":m") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f")) or (morph(dDA, (m.start(1), m.group(1)), ":f") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m"))) and not morph(dDA, prevword1(s[:m.start()]), ":[NAQ]", False, False) and not apposition(m.group(1), m.group(2))
def e1923_1 (s, m):
    return switchGender(m.group(2), False)
def c1923_2 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)air$", m.group(1)) and not m.group(2).startswith("seul") and morph(dDA, (m.start(1), m.group(1)), ":[si]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p") and not morph(dDA, prevword1(s[:m.start()]), ":[NAQ]", False, False) and not apposition(m.group(1), m.group(2))
def e1923_2 (s, m):
    return suggSing(m.group(2))
def c1938_1 (s, sx, m, dDA, sCountry):
    return m.group(1) != "fois" and not m.group(2).startswith("seul") and ((morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:m", ":[fe]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f")) or (morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:f", ":[me]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m"))) and morph(dDA, prevword1(s[:m.start()]), ":[VRBX]", True, True) and not apposition(m.group(1), m.group(2))
def e1938_1 (s, m):
    return switchGender(m.group(2), True)
def c1938_2 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[pi]", False) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s") and morph(dDA, prevword1(s[:m.start()]), ":[VRBX]", True, True) and not apposition(m.group(1), m.group(2))
def e1938_2 (s, m):
    return suggPlur(m.group(2))
def c1952_1 (s, sx, m, dDA, sCountry):
    return m.group(1) != "fois" and morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[si]", False) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p") and not m.group(2).startswith("seul") and not apposition(m.group(1), m.group(2)) and not look(s[:m.start()],u"\\b(?:et|ou|d’) *$")
def e1952_1 (s, m):
    return suggSing(m.group(2))
def c1956_1 (s, sx, m, dDA, sCountry):
    return m.group(1) != "fois" and morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[si]", False) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p") and not m.group(2).startswith("seul") and not apposition(m.group(1), m.group(2)) and not morph(dDA, prevword1(s[:m.start()]), ":[NAQB]", False, False)
def e1956_1 (s, m):
    return suggSing(m.group(2))
def c1966_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[me]", ":(?:B|G|V0|f)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f") and not apposition(m.group(2), m.group(3)) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e1966_1 (s, m):
    return suggMasPlur(m.group(3))  if m.group(1)=="certains"  else suggMasSing(m.group(3))
def c1971_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[me]", ":(?:B|G|V0|f)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f") and not apposition(m.group(2), m.group(3)) and not morph(dDA, prevword1(s[:m.start()]), ":[NAQ]|>(?:et|ou) ", False, False)
def e1971_1 (s, m):
    return suggMasPlur(m.group(3))  if m.group(1)=="certains"  else suggMasSing(m.group(3))
def c1978_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":(?:B|G|e|V0|f)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f") and not apposition(m.group(2), m.group(3)) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e1978_1 (s, m):
    return suggMasSing(m.group(3))
def c1983_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":(?:B|G|e|V0|f)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f") and not apposition(m.group(2), m.group(3)) and not morph(dDA, prevword1(s[:m.start()]), ":[NAQ]|>(?:et|ou) ", False, False)
def e1983_1 (s, m):
    return suggMasSing(m.group(3))
def c1990_1 (s, sx, m, dDA, sCountry):
    return m.group(2) != "fois" and not m.group(3).startswith("seul") and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[fe]", ":(?:B|G|V0|m)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m") and not apposition(m.group(2), m.group(3)) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e1990_1 (s, m):
    return suggFemPlur(m.group(3))  if m.group(1)=="certaines"  else suggFemSing(m.group(3))
def c1995_1 (s, sx, m, dDA, sCountry):
    return m.group(2) != "fois" and not m.group(3).startswith("seul") and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[fe]", ":(?:B|G|V0|m)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m") and not apposition(m.group(2), m.group(3)) and not morph(dDA, prevword1(s[:m.start()]), ":[NAQ]|>(?:et|ou) ", False, False)
def e1995_1 (s, m):
    return suggFemPlur(m.group(3))  if m.group(1)=="certaines"  else suggFemSing(m.group(3))
def c2002_1 (s, sx, m, dDA, sCountry):
    return m.group(2) != "fois" and not m.group(3).startswith("seul") and not re.match("(?i)quelque chose", m.group(0)) and ((morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":(?:B|e|G|V0|f)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f")) or (morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":(?:B|e|G|V0|m)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m"))) and not apposition(m.group(2), m.group(3)) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e2002_1 (s, m):
    return switchGender(m.group(3), m.group(1).endswith("s"))
def c2007_1 (s, sx, m, dDA, sCountry):
    return m.group(2) != "fois" and not m.group(3).startswith("seul") and not re.match("(?i)quelque chose", m.group(0)) and ((morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", ":(?:B|e|G|V0|f)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f")) or (morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", ":(?:B|e|G|V0|m)") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m"))) and not apposition(m.group(2), m.group(3)) and not morph(dDA, prevword1(s[:m.start()]), r":[NAQ]|>(?:et|ou) ", False, False)
def e2007_1 (s, m):
    return switchGender(m.group(3), m.group(1).endswith("s"))
def c2016_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[si]", False) and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p") and not apposition(m.group(2), m.group(3)) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e2016_1 (s, m):
    return suggSing(m.group(3))
def c2021_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[si]", False) and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p") and not apposition(m.group(2), m.group(3)) and not morph(dDA, prevword1(s[:m.start()]), ":[NAQ]|>(?:et|ou) ", False, False)
def e2021_1 (s, m):
    return suggSing(m.group(3))
def c2028_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[si]", False) and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWi]") and not apposition(m.group(2), m.group(3)) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e2028_1 (s, m):
    return suggSing(m.group(3))
def c2033_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[si]", False) and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWi]") and not apposition(m.group(2), m.group(3)) and not morph(dDA, prevword1(s[:m.start()]), ":[NAQ]|>(?:et|ou) ", False, False)
def e2033_1 (s, m):
    return suggSing(m.group(3))
def c2040_1 (s, sx, m, dDA, sCountry):
    return not m.group(2).startswith("seul") and morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[pi]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s") and not apposition(m.group(1), m.group(2))
def e2040_1 (s, m):
    return suggPlur(m.group(2))
def c2045_1 (s, sx, m, dDA, sCountry):
    return not m.group(2).startswith("seul") and morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[pi]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s") and not morph(dDA, (m.start(3), m.group(3)), ":A", False) and not apposition(m.group(1), m.group(2))
def e2045_1 (s, m):
    return suggPlur(m.group(2))
def c2051_1 (s, sx, m, dDA, sCountry):
    return not m.group(3).startswith("seul") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]", False) and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s") and not apposition(m.group(2), m.group(3)) and not look(s[:m.start()],r"(?i)\bune? de ")
def e2051_1 (s, m):
    return suggPlur(m.group(3))
def c2063_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s")) or (morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[si]") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p"))
def e2063_1 (s, m):
    return switchPlural(m.group(3))
def c2068_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[pi]") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]") and morph(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s")
def e2068_1 (s, m):
    return suggPlur(m.group(3))
def c2072_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]", False) and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:[pi]", ":G") and morph(dDA, (m.start(4), m.group(4)), ":[NAQ].*:s") and not look(s[:m.start()],r"(?i)\bune? de ")
def e2072_1 (s, m):
    return suggPlur(m.group(4))
def c2077_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[si]", False) and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:[si]", ":G") and morph(dDA, (m.start(4), m.group(4)), ":[NAQ].*:p")
def e2077_1 (s, m):
    return suggSing(m.group(4))
def c2084_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:(?:m|f:p)", ":(?:G|P|f:[is]|V0)") and not apposition(m.group(1), m.group(2))
def e2084_1 (s, m):
    return suggFemSing(m.group(2))
def c2088_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:(?:f|m:p)", ":(?:G|P|m:[is]|V0)") and not apposition(m.group(1), m.group(2))
def e2088_1 (s, m):
    return suggMasSing(m.group(2))
def c2092_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:f|>[aéeiou].*:e", False) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:(?:f|m:p)", ":(?:G|P|m:[is]|V0)") and not apposition(m.group(1), m.group(2))
def e2092_1 (s, m):
    return suggMasSing(m.group(2))
def c2096_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:m", ":G|>[aéeiou].*:[ef]") and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:(?:f|m:p)", ":(?:G|P|m:[is]|V0)") and not apposition(m.group(2), m.group(3))
def e2096_1 (s, m):
    return suggMasSing(m.group(3))
def c2101_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:m", ":G|>[aéeiou].*:[ef]") and not morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f|>[aéeiou].*:e", False) and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:(?:f|m:p)", ":(?:G|P|m:[is]|V0)") and not apposition(m.group(2), m.group(3))
def e2101_1 (s, m):
    return suggMasSing(m.group(3))
def c2106_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":(?:G|P|m:[ip]|V0)") and not apposition(m.group(1), m.group(2))
def e2106_1 (s, m):
    return suggPlur(m.group(2))
def c2116_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V0e", False)
def c2119_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V0e", False) and morphex(dDA, (m.start(4), m.group(4)), ":[NAQ].*:m", ":[fe]")
def e2119_1 (s, m):
    return m.group(1).replace("lle", "l")
def c2125_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V0e", False)
def c2128_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V0e", False) and morphex(dDA, (m.start(4), m.group(4)), ":[NAQ].*:f", ":[me]")
def e2128_1 (s, m):
    return m.group(1).replace("l", "lle")
def c2139_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":B.*:p", False)
def c2157_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()])
def c2158_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()])
def c2159_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()])
def c2165_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"(?i)\bquatre $")
def c2167_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, nextword1(s, m.end()), ":B") and not look(s[:m.start()],u"(?i)\\b(?:numéro|page|chapitre|référence|année|test|série)s? +$")
def c2178_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, nextword1(s, m.end()), ":B|>une?", False, True) and not look(s[:m.start()],u"(?i)\\b(?:numéro|page|chapitre|référence|année|test|série)s? +$")
def c2182_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, nextword1(s, m.end()), ":B|>une?", False, False)
def c2185_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]", ":G") and morphex(dDA, prevword1(s[:m.start()]), ":[VR]", ":B", True)
def c2190_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, nextword1(s, m.end()), ":B") or (morph(dDA, prevword1(s[:m.start()]), ":B") and morph(dDA, nextword1(s, m.end()), ":[NAQ]", False))
def c2198_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">faire ", False)
def c2200_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">faire ", False) and morph(dDA, (m.start(3), m.group(3)), ":(?:N|MP)")
def c2226_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u":(?:V0e|W)|>très", False)
def c2230_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:co[ûu]ter|payer) ", False)
def c2243_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">donner ", False)
def c2250_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:mettre|mise) ", False)
def c2258_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:avoir|perdre) ", False)
def c2260_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"(?i)\\b(?:lit|fauteuil|armoire|commode|guéridon|tabouret|chaise)s?\\b")
def c2265_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":(?:V|[NAQ].*:s)", ":[pi]", True)
def c2295_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:aller|partir) ", False)
def c2305_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)([lmtsn]|soussignée?s?|seule?s?)$", m.group(2)) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ]") and not morph(dDA, prevword1(s[:m.start()]), ":V0")
def c2310_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">(?:être|devenir|para[îi]tre|rendre|sembler) ", False)
def e2310_1 (s, m):
    return m.group(2).replace("oc", "o")
def c2321_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">tenir ")
def c2331_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">mettre ", False)
def c2332_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">faire ", False)
def c2351_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, nextword1(s, m.end()), ":[AQ]")
def c2361_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">faire ", False)
def c2368_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False)
def c2375_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">tordre ", False)
def c2377_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">rendre ", False)
def c2384_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">couper ")
def c2385_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:avoir|donner) ", False)
def c2393_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V.\w+:(?!Q)")
def c2399_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"(?i)\\b(?:[lmts]es|des?|[nv]os|leurs) +$")
def c2402_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, nextword1(s, m.end()), ":[GV]", ":[NAQ]", True)
def c2404_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, nextword1(s, m.end()), ":[GV]", ":[NAQ]")
def c2406_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, nextword1(s, m.end()), ":[GV]", ":[NAQ]", True)
def c2408_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, nextword1(s, m.end()), ":G", ":[NAQ]")
def c2410_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False)
def c2414_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, prevword1(s[:m.start()]), ":V0e", False)
def c2417_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), u">(?:abandonner|céder|résister) ", False)
def e2428_1 (s, m):
    return m.group(1).replace("nt", "mp")
def c2436_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False) and morph(dDA, (m.start(3), m.group(3)), ":Y", False)
def e2436_1 (s, m):
    return m.group(2).replace("sens", "cens")
def e2441_1 (s, m):
    return m.group(1).replace("o", u"ô")
def c2449_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False)
def c2452_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:desceller|desseller) ", False)
def e2452_1 (s, m):
    return m.group(2).replace("descell", u"décel").replace("dessell", u"décel")
def c2456_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:desceller|desseller) ", False)
def e2456_1 (s, m):
    return m.group(1).replace("descell", u"décel").replace("dessell", u"décel")
def c2464_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0", False)
def c2467_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"\\b(?:vous|et toi) +$")
def e2470_1 (s, m):
    return m.group(1).replace("and", "ant")
def c2473_1 (s, sx, m, dDA, sCountry):
    return not ( m.group(1) == "bonne" and look(s[:m.start()],"(?i)\\bune +$") and look(s[m.end():],"(?i)^ +pour toute") )
def c2476_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">(?:faire|perdre) ")
def c2490_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":D")
def c2525_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":[NAQ]")
def c2526_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ]", ":[123][sp]")
def c2530_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(3), m.group(3)), ":[123][sp]", ":[GQ]")
def c2533_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":[GQ]")
def c2535_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":[GQ]")
def c2542_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":Y") and not re.match("(?i)[ld]es$", m.group(1))
def c2549_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">soulever ", False)
def c2559_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">(?:être|habiter|trouver|situer|rester|demeurer?) ", False)
def c2572_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False)
def c2583_1 (s, sx, m, dDA, sCountry):
    return not (m.group(1) == "Notre" and look(s[m.end():],"Père"))
def e2583_1 (s, m):
    return m.group(1).replace("otre", u"ôtre")
def c2585_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"(?i)\\b(les?|la|du|des|aux?) +") and morph(dDA, (m.start(2), m.group(2)), ":[NAQ]", False)
def e2585_1 (s, m):
    return m.group(1).replace(u"ôtre", "otre").rstrip("s")
def c2590_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False, False)
def c2601_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()])
def c2604_1 (s, sx, m, dDA, sCountry):
    return ( re.match("[nmts]e$", m.group(2)) or (not re.match(u"(?i)(?:confiance|envie|peine|prise|crainte|affaire|hâte|force|recours)$", m.group(2)) and morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":[AG]")) ) and not prevword1(s[:m.start()])
def c2609_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(3), m.group(3)), ":V.*:(?:[1-3][sp])", ":(?:G|1p)") and not ( m.group(2) == "leur" and morph(dDA, (m.start(3), m.group(3)), ":[NA].*:[si]", False) ) and not prevword1(s[:m.start()])
def c2616_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":[VR]", False, False) and not look(s[m.end():],"^ +>") and not morph(dDA, nextword1(s, m.end()), ":3s", False)
def c2621_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V.\w+:(?!Y)")
def c2622_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V0e", ":Y")
def c2625_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False, False)
def c2629_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">aller ", False)
def c2632_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False)
def e2632_1 (s, m):
    return m.group(2).replace("pal", u"pâl")
def e2635_1 (s, m):
    return m.group(2).replace("pal", u"pâl")
def c2640_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">prendre ", False)
def c2641_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">tirer ", False)
def c2642_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">faire ", False)
def c2644_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">prendre ", False)
def c2650_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ]")
def c2651_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()])
def c2657_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":A") and not re.match("(?i)seule?s?$", m.group(2))
def c2662_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:N|A|Q|G|MP)")
def c2675_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":(?:Y|M[12P])")
def c2677_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"(?i)(?:peu|de) $") and morph(dDA, (m.start(2), m.group(2)), ":Y|>(tout|les?|la) ")
def c2687_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False)
def c2690_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ">(?:arriver|venir|à|revenir|partir|aller) ")
def c2695_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":P", False)
def c2699_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":Q")
def c2703_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, nextword1(s, m.end()), ":A", False)
def c2723_1 (s, sx, m, dDA, sCountry):
    return not nextword1(s, m.end())
def c2726_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ">résonner ", False)
def e2726_1 (s, m):
    return m.group(2).replace(u"résonn", "raisonn")
def c2733_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":M1", False)
def e2742_1 (s, m):
    return m.group(1).replace("scep","sep")
def c2745_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False)
def c2749_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">suivre ", False)
def c2753_1 (s, sx, m, dDA, sCountry):
    return not look(s[m.end():]," soit ")
def c2754_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, nextword1(s, m.end()), ":[GY]", True, True) and not look(s[:m.start()],"quel(?:s|les?|) qu $")
def c2766_1 (s, sx, m, dDA, sCountry):
    return ( morphex(dDA, (m.start(2), m.group(2)), ":N.*:[me]:s", ":G") or (re.match(u"(?i)[aeéiîou]", m.group(2)) and morphex(dDA, (m.start(2), m.group(2)), ":N.*:f:s", ":G")) ) and (look(s[:m.start()],u"(?i)^ *$|\\b(?:à|avec|chez|dès|contre|devant|derrière|en|par|pour|sans|sur) +$"))
def e2780_1 (s, m):
    return m.group(1).replace("sur", u"sûr")
def e2783_1 (s, m):
    return m.group(1).replace("sur", u"sûr")
def c2789_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":M1", False)
def c2793_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":Y", False)
def e2793_1 (s, m):
    return m.group(1).replace("sur", u"sûr")
def c2802_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":N", ":M[12P]")
def c2813_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False) and morph(dDA, (m.start(3), m.group(3)), ":Y", False)
def c2819_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">avoir ", False)
def c2835_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[me]:s")
def c2851_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">ouvrir ", False)
def c2864_1 (s, sx, m, dDA, sCountry):
    return not m.group(1).isdigit() and not m.group(2).isdigit() and not morph(dDA, (m.start(0), m.group(0)), ":", False) and not morph(dDA, (m.start(2), m.group(2)), ":G", False) and _oDict.isValid(m.group(1)+m.group(2))
def c2864_2 (s, sx, m, dDA, sCountry):
    return m.group(2) != u"là" and not re.match("(?i)(?:ex|mi|quasi|semi|non|demi|pro|anti|multi|pseudo|proto|extra)$", m.group(1)) and not m.group(1).isdigit() and not m.group(2).isdigit() and not morph(dDA, (m.start(2), m.group(2)), ":G", False) and not morph(dDA, (m.start(0), m.group(0)), ":", False) and not _oDict.isValid(m.group(1)+m.group(2))
def e2877_1 (s, m):
    return m.group(0).lower()
def c2882_1 (s, sx, m, dDA, sCountry):
    return not( ( m.group(0)=="Juillet" and look(s[:m.start()],"(?i)monarchie +de +$") ) or ( m.group(0)=="Octobre" and look(s[:m.start()],"(?i)révolution +d’$") ) )
def e2882_1 (s, m):
    return m.group(0).lower()
def c2899_1 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)fonctions? ", m.group(0)) or not look(s[:m.start()],r"(?i)\ben $")
def c2904_1 (s, sx, m, dDA, sCountry):
    return m.group(2).istitle() and morphex(dDA, (m.start(1), m.group(1)), ":[NV]", ":(?:A|V0e|D)")
def e2904_1 (s, m):
    return m.group(2).lower()
def c2904_2 (s, sx, m, dDA, sCountry):
    return m.group(2).islower() and not m.group(2).startswith("canadienne") and ( re.match("(?i)(?:certaine?s?|cette|ce[ts]?|[dl]es|[nv]os|quelques|plusieurs|chaque|une)$", m.group(1)) or ( re.match("(?i)un$", m.group(1)) and not look(s[m.end():],u"(?:approximatif|correct|courant|parfait|facile|aisé|impeccable|incompréhensible)") ) )
def e2904_2 (s, m):
    return m.group(2).capitalize()
def e2911_1 (s, m):
    return m.group(1).capitalize()
def c2915_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:parler|cours|leçon|apprendre|étudier|traduire|enseigner|professeur|enseignant|dictionnaire|méthode) ", False)
def e2915_1 (s, m):
    return m.group(2).lower()
def e2919_1 (s, m):
    return m.group(1).lower()
def c2927_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":D", False)
def c2937_1 (s, sx, m, dDA, sCountry):
    return look(s[:m.start()],r"\w")
def e2943_1 (s, m):
    return m.group(1).capitalize()
def e2944_1 (s, m):
    return m.group(1).capitalize()
def c2948_1 (s, sx, m, dDA, sCountry):
    return re.match(u"(?:Mètre|Watt|Gramme|Seconde|Ampère|Kelvin|Mole|Cand[eé]la|Hertz|Henry|Newton|Pascal|Joule|Coulomb|Volt|Ohm|Farad|Tesla|W[eé]ber|Radian|Stéradian|Lumen|Lux|Becquerel|Gray|Sievert|Siemens|Katal)s?|(?:Exa|P[ée]ta|Téra|Giga|Méga|Kilo|Hecto|Déc[ai]|Centi|Mi(?:lli|cro)|Nano|Pico|Femto|Atto|Ze(?:pto|tta)|Yo(?:cto|etta))(?:mètre|watt|gramme|seconde|ampère|kelvin|mole|cand[eé]la|hertz|henry|newton|pascal|joule|coulomb|volt|ohm|farad|tesla|w[eé]ber|radian|stéradian|lumen|lux|becquerel|gray|sievert|siemens|katal)s?", m.group(2))
def e2948_1 (s, m):
    return m.group(2).lower()
def c2958_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":Y", False)
def c2959_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V1") and not look(s[:m.start()],u"(?i)(quelqu(?:e chose|’une?) d(?:e |’)|(?:l(es?|a)|nous|vous|me|te|se)[ @]trait|(?:quelqu(?:e chose|’une?)|personne|rien(?: +\w+|)) +$)")
def c2963_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V1", ":M[12P]")
def e2963_1 (s, m):
    return suggVerbInfi(m.group(1))
def c2965_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V1", False)
def c2967_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":[123][sp]")
def c2969_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V1", ":[NM]") and not morph(dDA, prevword1(s[:m.start()]), ">(?:tenir|passer) ", False)
def e2969_1 (s, m):
    return suggVerbInfi(m.group(1))
def c2973_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V1", False)
def c2974_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V1", ":[NM]")
def c2975_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":Q", False)
def c2977_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Q|2p)", False)
def c2979_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":Q", False) and not morph(dDA, prevword1(s[:m.start()]), "V0.*[12]p", False)
def e2986_1 (s, m):
    return m.group(2)[:-1]
def c3012_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V", False)
def c3016_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">sembler ", False)
def c3029_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False) and isEndOfNG(dDA, s[m.end():], m.end())
def c3031_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V[123]_i_._") and isEndOfNG(dDA, s[m.end():], m.end())
def c3032_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":A", False) and morphex(dDA, (m.start(2), m.group(2)), ":A", ":[GM]")
def c3034_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":A", False)
def c3035_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:s", False) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[GV]") and isEndOfNG(dDA, s[m.end():], m.end())
def c3037_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":N", ":[GY]") and isEndOfNG(dDA, s[m.end():], m.end())
def c3039_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ]", ":V0") and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ]", ":(?:G|[123][sp]|P)")
def c3050_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False) and isEndOfNG(dDA, s[m.end():], m.end())
def c3063_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ]", ":G") and isEndOfNG(dDA, s[m.end():], m.end())
def c3066_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False) and isEndOfNG(dDA, s[m.end():], m.end())
def c3069_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False) and isEndOfNG(dDA, s[m.end():], m.end())
def c3037_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":N", ":[GY]") and isEndOfNG(dDA, s[m.end():], m.end())
def c3076_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ]", False) and isEndOfNG(dDA, s[m.end():], m.end())
def c3078_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ]", ":Y") and isEndOfNG(dDA, s[m.end():], m.end())
def c3096_1 (s, sx, m, dDA, sCountry):
    return re.match("(?i)(?:fini|terminé)s?", m.group(2)) and morph(dDA, prevword1(s[:m.start()]), ":C", False, True)
def c3096_2 (s, sx, m, dDA, sCountry):
    return re.match("(?i)assez|trop", m.group(2)) and (look(s[m.end():],"^ +d(?:e |’)") or not nextword1(s, m.end()))
def c3096_3 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":A", ":[GVW]") and morph(dDA, prevword1(s[:m.start()]), ":C", False, True)
def c3110_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:faire|vouloir) ", False) and not look(s[:m.start()],"(?i)\\b(?:en|[mtsld]es?|[nv]ous|un) +$") and morphex(dDA, (m.start(2), m.group(2)), ":V", ":M")
def c3113_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">savoir ", False) and morph(dDA, (m.start(2), m.group(2)), ":V", False) and not look(s[:m.start()],"(?i)\\b(?:[mts]e|[vn]ous|les?|la|un) +$")
def c3116_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Q|2p)", False)
def e3116_1 (s, m):
    return suggVerbInfi(m.group(1))
def c3119_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":(?:Q|2p)", ":N")
def e3119_1 (s, m):
    return suggVerbInfi(m.group(1))
def c3126_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(2), m.group(2)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) or m.group(2).endswith(u" été")) and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWYsi]")
def e3126_1 (s, m):
    return suggSing(m.group(3))
def c3130_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(1), m.group(1)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) or m.group(1).endswith(u" été")) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[GWYsi]")
def e3130_1 (s, m):
    return suggSing(m.group(2))
def c3134_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(2), m.group(2)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) or m.group(2).endswith(u" été")) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWYsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:f", ":[GWYme]"))
def e3134_1 (s, m):
    return suggMasSing(m.group(3))
def c3139_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p", ":[GWYsi]") or ( morphex(dDA, (m.start(1), m.group(1)), ":[AQ].*:f", ":[GWYme]") and not morph(dDA, nextword1(s, m.end()), ":N.*:f", False, False) )
def e3139_1 (s, m):
    return suggMasSing(m.group(1))
def c3143_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ].*:p", ":[GWYsi]") or ( morphex(dDA, (m.start(1), m.group(1)), ":[AQ].*:f", ":[GWYme]") and not morph(dDA, nextword1(s, m.end()), ":N.*:f", False, False) )
def e3143_1 (s, m):
    return suggMasSing(m.group(1))
def c3147_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(2), m.group(2)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) or m.group(2).endswith(u" été")) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWYsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:f", ":[GWYme]")) and not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def e3147_1 (s, m):
    return suggMasSing(m.group(3))
def c3153_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(2), m.group(2)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) or m.group(2).endswith(u" été")) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWYsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:m", ":[GWYfe]")) and not morph(dDA, prevword1(s[:m.start()]), ":R|>de ", False, False)
def e3153_1 (s, m):
    return suggFemSing(m.group(3))
def c3159_1 (s, sx, m, dDA, sCountry):
    return (morph(dDA, (m.start(2), m.group(2)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) or m.group(2).endswith(u" été")) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWYsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:m", ":[GWYfe]"))
def e3159_1 (s, m):
    return suggFemSing(m.group(3))
def c3164_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(2)) and ((morph(dDA, (m.start(1), m.group(1)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) and morph(dDA, (m.start(1), m.group(1)), ":1p", False)) or m.group(1).endswith(u" été")) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[GWYpi]")
def e3164_1 (s, m):
    return suggPlur(m.group(2))
def c3170_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(3)) and (morph(dDA, (m.start(2), m.group(2)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) or m.group(2).endswith(u" été")) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s", ":[GWYpi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:f", ":[GWYme]")) and not look(s[:m.start()],"ce que? +$") and (not re.match(u"(?:ceux-(?:ci|là)|lesquels)$", m.group(1)) or not morph(dDA, prevword1(s[:m.start()]), ":R", False, False))
def e3170_1 (s, m):
    return suggMasPlur(m.group(3))
def c3176_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(3)) and (morph(dDA, (m.start(2), m.group(2)), u">(?:être|sembler|devenir|re(?:ster|devenir)|para[îi]tre) ", False) or m.group(2).endswith(u" été")) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s", ":[GWYpi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:m", ":[GWYfe]")) and (not re.match(u"(?i)(?:elles|celles-(?:ci|là)|lesquelles)$", m.group(1)) or not morph(dDA, prevword1(s[:m.start()]), ":R", False, False))
def e3176_1 (s, m):
    return suggFemPlur(m.group(3))
def c3182_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">avoir ", False) and morphex(dDA, (m.start(2), m.group(2)), ":[123]s", ":[GNAQWY]")
def e3182_1 (s, m):
    return suggVerbPpas(m.group(2))
def c3188_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[MWYsi]")
def e3188_1 (s, m):
    return suggSing(m.group(3))
def c3192_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[MWYsi]")
def e3192_1 (s, m):
    return suggSing(m.group(2))
def c3196_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWYsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:f", ":[GWYme]"))
def e3196_1 (s, m):
    return suggMasSing(m.group(3))
def c3201_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[MWYsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:f", ":[GWYme]")) and not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def e3201_1 (s, m):
    return suggMasSing(m.group(3))
def c3207_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[MWYsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:m", ":[GWYfe]")) and not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def e3207_1 (s, m):
    return suggFemSing(m.group(3))
def c3213_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[MWYsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:m", ":[GWYfe]"))
def e3213_1 (s, m):
    return suggFemSing(m.group(3))
def c3218_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(2)) and morph(dDA, (m.start(1), m.group(1)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and morph(dDA, (m.start(1), m.group(1)), ":1p", False) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[GWYpi]")
def e3218_1 (s, m):
    return suggPlur(m.group(2))
def c3223_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(3)) and morph(dDA, (m.start(2), m.group(2)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s", ":[GWYpi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:f", ":[GWYme]")) and (not re.match(u"(?:ceux-(?:ci|là)|lesquels)$", m.group(1)) or not morph(dDA, prevword1(s[:m.start()]), ":R", False, False))
def e3223_1 (s, m):
    return suggMasPlur(m.group(3))
def c3229_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(3)) and morph(dDA, (m.start(2), m.group(2)), u">(?:sembler|para[îi]tre|pouvoir|penser|préférer|croire|d(?:evoir|éclarer|ésirer|étester|ire)|vouloir|affirmer|aimer|adorer|souhaiter|estimer|imaginer) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s", ":[GWYpi]") or morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:m", ":[GWYfe]")) and (not re.match(u"(?:elles|celles-(?:ci|là)|lesquelles)$", m.group(1)) or not morph(dDA, prevword1(s[:m.start()]), ":R", False, False))
def e3229_1 (s, m):
    return suggFemPlur(m.group(3))
def c3237_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[GMWYsi]") and not morph(dDA, (m.start(1), m.group(1)), ":G", False)
def e3237_1 (s, m):
    return suggSing(m.group(2))
def c3241_1 (s, sx, m, dDA, sCountry):
    return not re.match("(?i)légion$", m.group(2)) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[GWYpi]") and not morph(dDA, (m.start(1), m.group(1)), ":G", False)
def e3241_1 (s, m):
    return suggPlur(m.group(2))
def c3246_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(3)) and ((morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:f", ":[GWme]") and morphex(dDA, (m.start(2), m.group(2)), ":m", ":[Gfe]")) or (morphex(dDA, (m.start(3), m.group(3)), ":[AQ].*:m", ":[GWfe]") and morphex(dDA, (m.start(2), m.group(2)), ":f", ":[Gme]"))) and not ( morph(dDA, (m.start(3), m.group(3)), ":p", False) and morph(dDA, (m.start(2), m.group(2)), ":s", False) ) and not morph(dDA, prevword1(s[:m.start()]), ":(?:R|P|Q|Y|[123][sp])", False, False) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e3246_1 (s, m):
    return switchGender(m.group(3))
def c3253_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(2)) and ((morphex(dDA, (m.start(1), m.group(1)), ":M[1P].*:f", ":[GWme]") and morphex(dDA, (m.start(2), m.group(2)), ":m", ":[GWfe]")) or (morphex(dDA, (m.start(1), m.group(1)), ":M[1P].*:m", ":[GWfe]") and morphex(dDA, (m.start(2), m.group(2)), ":f", ":[GWme]"))) and not morph(dDA, prevword1(s[:m.start()]), ":(?:R|P|Q|Y|[123][sp])", False, False) and not look(s[:m.start()],r"\b(?:et|ou|de) +$")
def e3253_1 (s, m):
    return switchGender(m.group(2))
def c3261_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":A.*:p", ":(?:G|E|M1|s|i)")
def e3261_1 (s, m):
    return suggSing(m.group(1))
def c3265_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":A.*:[fp]", ":(?:G|E|M1|m:[si])")
def e3265_1 (s, m):
    return suggMasSing(m.group(1))
def c3269_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":A.*:[mp]", ":(?:G|E|M1|f:[si])")
def e3269_1 (s, m):
    return suggFemSing(m.group(1))
def c3273_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":A.*:[fs]", ":(?:G|E|M1|m:[pi])")
def e3273_1 (s, m):
    return suggMasPlur(m.group(1))
def c3277_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":A.*:[ms]", ":(?:G|E|M1|f:[pi])")
def e3277_1 (s, m):
    return suggFemPlur(m.group(1))
def c3283_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), "V0e", False)
def c3287_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|Y|[NAQ].*:p)", ":[GWsi]")
def e3287_1 (s, m):
    return suggSing(m.group(1))
def c3290_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|Y|[NAQ].*:p)", ":[GWsi]")
def e3290_1 (s, m):
    return suggSing(m.group(1))
def c3293_1 (s, sx, m, dDA, sCountry):
    return (morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|Y|[NAQ].*:p)", ":[GWsi]") or morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|[AQ].*:f)", ":[GWme]"))
def e3293_1 (s, m):
    return suggMasSing(m.group(1))
def c3296_1 (s, sx, m, dDA, sCountry):
    return (morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|Y|[NAQ].*:p)", ":[GWsi]") or morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|[AQ].*:m)", ":[GWfe]"))
def e3296_1 (s, m):
    return suggFemSing(m.group(1))
def c3299_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|Y|[NAQ].*:s)", ":[GWpi]")
def e3299_1 (s, m):
    return suggPlur(m.group(1))
def c3302_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(1)) and (morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|Y|[NAQ].*:s)", ":[GWpi]") or morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|[AQ].*:f)", ":[GWme]"))
def e3302_1 (s, m):
    return suggMasPlur(m.group(1))
def c3305_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)légion$", m.group(1)) and (morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|Y|[NAQ].*:s)", ":[GWpi]") or morphex(dDA, (m.start(1), m.group(1)), ":(?:[123][sp]|[AQ].*:m)", ":[GWfe]"))
def e3305_1 (s, m):
    return suggFemPlur(m.group(1))
def c3310_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[NAQ]", ":[QWGBMpi]") and not re.match(u"(?i)(?:légion|nombre|cause)$", m.group(1)) and not look(s[:m.start()],r"(?i)\bce que?\b")
def e3310_1 (s, m):
    return suggPlur(m.group(1))
def c3310_2 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:N|A|Q|W|G|3p)") and not look(s[:m.start()],r"(?i)\bce que?\b")
def e3310_2 (s, m):
    return suggVerbPpas(m.group(1), ":m:p")
def c3321_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:croire|considérer|montrer|penser|révéler|savoir|sentir|voir|vouloir) ", False) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[GWsi]")
def e3321_1 (s, m):
    return suggSing(m.group(2))
def c3325_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:croire|considérer|montrer|penser|révéler|savoir|sentir|voir|vouloir) ", False) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:p", ":[GWsi]")
def e3325_1 (s, m):
    return suggSing(m.group(2))
def c3329_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:croire|considérer|montrer|penser|révéler|savoir|sentir|voir|vouloir) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f", ":[GWme]")) and (not re.match(u"(?:celui-(?:ci|là)|lequel)$", m.group(1)) or not morph(dDA, prevword1(s[:m.start()]), ":R", False, False))
def e3329_1 (s, m):
    return suggMasSing(m.group(3))
def c3335_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:croire|considérer|montrer|penser|révéler|savoir|sentir|voir|vouloir) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m", ":[GWfe]")) and not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def e3335_1 (s, m):
    return suggFemSing(m.group(3))
def c3341_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:croire|considérer|montrer|penser|révéler|savoir|sentir|voir|vouloir) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:p", ":[GWsi]") or morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m", ":[GWfe]"))
def e3341_1 (s, m):
    return suggFemSing(m.group(3))
def c3346_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:croire|considérer|montrer|penser|révéler|savoir|sentir|voir|vouloir) ", False) and morphex(dDA, (m.start(2), m.group(2)), ":[NAQ].*:s", ":[GWpi]")
def e3346_1 (s, m):
    return suggPlur(m.group(2))
def c3350_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:croire|considérer|montrer|penser|révéler|savoir|sentir|voir|vouloir) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s", ":[GWpi]") or morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:f", ":[GWme]")) and (not re.match(u"(?:ceux-(?:ci|là)|lesquels)$", m.group(1)) or not morph(dDA, prevword1(s[:m.start()]), ":R", False, False))
def e3350_1 (s, m):
    return suggMasPlur(m.group(3))
def c3356_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), u">(?:croire|considérer|montrer|penser|révéler|savoir|sentir|voir|vouloir) ", False) and (morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:s", ":[GWpi]") or morphex(dDA, (m.start(3), m.group(3)), ":[NAQ].*:m", ":[GWfe]")) and (not re.match(u"(?:elles|celles-(?:ci|là)|lesquelles)$", m.group(1)) or not morph(dDA, prevword1(s[:m.start()]), ":R", False, False))
def e3356_1 (s, m):
    return suggFemPlur(m.group(3))
def c3368_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)(?:confiance|cours|envie|peine|prise|crainte|cure|affaire|hâte|force|recours)$", m.group(3)) and morph(dDA, (m.start(2), m.group(2)), ":V0a", False) and morphex(dDA, (m.start(3), m.group(3)), ":(?:[123][sp]|Q.*:[fp])", ":(?:G|W|Q.*:m:[si])")
def e3368_1 (s, m):
    return suggMasSing(m.group(3))
def c3374_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)(?:confiance|cours|envie|peine|prise|crainte|cure|affaire|hâte|force|recours)$", m.group(4)) and morph(dDA, (m.start(3), m.group(3)), ":V0a", False) and morphex(dDA, (m.start(4), m.group(4)), ":(?:[123][sp]|Q.*:[fp])", ":(?:G|W|Q.*:m:[si])")
def e3374_1 (s, m):
    return suggMasSing(m.group(4))
def c3380_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and morphex(dDA, (m.start(2), m.group(2)), ":V[0-3]..t.*:Q.*:s", ":[GWpi]") and not morph(dDA, nextword1(s, m.end()), ":V", False)
def e3380_1 (s, m):
    return suggPlur(m.group(2))
def c3385_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V0a", False) and morphex(dDA, (m.start(3), m.group(3)), ":V[0-3]..t_.*:Q.*:s", ":[GWpi]") and not look(s[:m.start()],r"\bque?\b")
def e3385_1 (s, m):
    return suggPlur(m.group(3))
def c3390_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and morphex(dDA, (m.start(2), m.group(2)), ":V[0-3]..t.*:Q.*:p", ":[GWsi]") and not morph(dDA, nextword1(s, m.end()), ":V", False)
def e3390_1 (s, m):
    return m.group(2)[:-1]
def c3395_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V0a", False) and morphex(dDA, (m.start(3), m.group(3)), ":V[0-3]..t_.*:Q.*:p", ":[GWsi]") and not look(s[:m.start()],r"\bque?\b") and not morph(dDA, nextword1(s, m.end()), ":V", False)
def e3395_1 (s, m):
    return m.group(3)[:-1]
def c3400_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":Q.*:(?:f|m:p)", ":m:[si]")
def e3400_1 (s, m):
    return suggMasSing(m.group(1))
def c3405_1 (s, sx, m, dDA, sCountry):
    return not re.match(u"(?i)(?:confiance|cours|envie|peine|prise|crainte|cure|affaire|hâte|force|recours)$", m.group(1)) and morphex(dDA, (m.start(1), m.group(1)), ":Q.*:(?:f|m:p)", ":m:[si]") and look(s[:m.start()],u"(?i)(?:après +$|sans +$|pour +$|que? +$|quand +$|, +$|^ *$)")
def e3405_1 (s, m):
    return suggMasSing(m.group(1))
def c3413_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":V0a", False) and not (re.match(u"(?:décidé|essayé|tenté)$", m.group(4)) and look(s[m.end():],u" +d(?:e |’)")) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ]", False) and morphex(dDA, (m.start(4), m.group(4)), ":V[0-3]..t.*:Q.*:s", ":[GWpi]") and not morph(dDA, nextword1(s, m.end()), ":(?:Y|Oo)", False)
def e3413_1 (s, m):
    return suggPlur(m.group(4), m.group(2))
def c3421_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":V0a", False) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:m", False) and (morphex(dDA, (m.start(4), m.group(4)), ":V[0-3]..t.*:Q.*:f", ":[GWme]") or morphex(dDA, (m.start(4), m.group(4)), ":V[0-3]..t.*:Q.*:p", ":[GWsi]"))
def e3421_1 (s, m):
    return suggMasSing(m.group(4))
def c3428_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":V0a", False) and not (re.match(u"(?:décidé|essayé|tenté)$", m.group(4)) and look(s[m.end():],u" +d(?:e |’)")) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:f", False) and (morphex(dDA, (m.start(4), m.group(4)), ":V[0-3]..t.*:Q.*:m", ":[GWfe]") or morphex(dDA, (m.start(4), m.group(4)), ":V[0-3]..t.*:Q.*:p", ":[GWsi]")) and not morph(dDA, nextword1(s, m.end()), ":(?:Y|Oo)|>que?", False)
def e3428_1 (s, m):
    return suggFemSing(m.group(4))
def c3437_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and (morphex(dDA, (m.start(2), m.group(2)), ":V[0-3]..t.*:Q.*:f", ":[GWme]") or morphex(dDA, (m.start(2), m.group(2)), ":V[0-3]..t.*:Q.*:p", ":[GWsi]"))
def e3437_1 (s, m):
    return suggMasSing(m.group(2))
def c3443_1 (s, sx, m, dDA, sCountry):
    return not re.match("(?:A|avions)$", m.group(1)) and morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and morph(dDA, (m.start(2), m.group(2)), ":V(?!.*:Q)")
def e3443_1 (s, m):
    return suggVerbPpas(m.group(2), ":m:s")
def c3448_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and (morph(dDA, (m.start(3), m.group(3)), ":Y") or re.match("(?:[mtsn]e|[nv]ous|leur|lui)$", m.group(3)))
def c3454_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, nextword1(s, m.end()), ":[NAQ].*:m", False)
def c3456_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False)
def c3460_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and morphex(dDA, (m.start(2), m.group(2)), ":(?:Y|2p|Q.*:[fp])", ":m:[si]") and m.group(2) != "prise" and not morph(dDA, prevword1(s[:m.start()]), ">(?:les|[nv]ous|en)|:[NAQ].*:[fp]", False) and not look(s[:m.start()],r"(?i)\bquel(?:le|)s?\b")
def e3460_1 (s, m):
    return suggMasSing(m.group(2))
def c3466_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V0a", False) and morphex(dDA, (m.start(3), m.group(3)), ":(?:Y|2p|Q.*:p)", ":[si]")
def e3466_1 (s, m):
    return suggMasSing(m.group(3))
def c3471_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and morphex(dDA, (m.start(2), m.group(2)), ":V[123]..t.* :Q.*:s", ":[GWpi]")
def e3471_1 (s, m):
    return suggPlur(m.group(2))
def c3477_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:G|Y|1p|3[sp])") and not look(s[m.end():],"^ +(?:je|tu|ils?|elles?|on|[vn]ous) ")
def e3477_1 (s, m):
    return suggVerb(m.group(1), ":1p")
def c3483_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:G|Y|2p|3[sp])") and not look(s[m.end():],"^ +(?:je|ils?|elles?|on|[vn]ous) ")
def e3483_1 (s, m):
    return suggVerb(m.group(1), ":2p")
def c3519_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[NAQ]", ":G")
def c3527_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V[13].*:Ip.*:2s", ":[GNA]")
def c3530_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V[13].*:Ip.*:2s", ":G")
def c3535_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[MOs]")
def c3538_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V[23].*:Ip.*:3s", ":[GNA]") and analyse(m.group(2)+"s", ":E:2s", False) and not re.match("(?i)doit", m.group(1)) and not (re.match("(?i)vient$", m.group(1)) and look(s[m.end():]," +l[ea]"))
def c3542_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V[23].*:Ip.*:3s", ":G") and analyse(m.group(2)+"s", ":E:2s", False)
def c3547_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V3.*:Ip.*:3s", ":[GNA]")
def c3550_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V3.*:Ip.*:3s", ":G")
def c3560_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":A", ":G") and not look(s[m.end():],r"\bsoit\b")
def c3571_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":E|>chez", False) and _oDict.isValid(m.group(1))
def c3577_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":E", ":(?:G|M[12])")
def c3582_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":E", ":(?:G|M[12])") and not morph(dDA, nextword1(s, m.end()), ":Y", False, False) and morph(dDA, prevword1(s[:m.start()]), ":Cc", False, True)
def c3587_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":E", ":(?:G|M[12])") and not morph(dDA, nextword1(s, m.end()), ":(?:N|A|Q|Y|B|3[sp])", False, False) and morph(dDA, prevword1(s[:m.start()]), ":Cc", False, True)
def c3592_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":E", ":(?:G|M[12])") and not morph(dDA, nextword1(s, m.end()), ":(?:N|A|Q|Y|MP)", False, False) and morph(dDA, prevword1(s[:m.start()]), ":Cc", False, True)
def c3600_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":E", ":(?:G|M[12])") and not morph(dDA, nextword1(s, m.end()), ":(?:Y|[123][sp])", False, False)
def c3605_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":E", False)
def c3610_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":E", False) and morphex(dDA, nextword1(s, m.end()), ":[RC]", ":[NAQ]", True)
def c3615_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":E", False) and morphex(dDA, nextword1(s, m.end()), ":[RC]", ":Y", True)
def c3621_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, nextword1(s, m.end()), ":Y", False, False)
def c3623_1 (s, sx, m, dDA, sCountry):
    return not prevword1(s[:m.start()]) and not morph(dDA, nextword1(s, m.end()), ":Y", False, False)
def c3648_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":R", False, True)
def c3649_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def c3651_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def c3653_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[123][sp]")
def c3654_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":[123]s", False, False)
def c3655_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":(?:[123]s|R)", False, False)
def c3656_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":(?:[123]p|R)", False, False)
def c3657_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, prevword1(s[:m.start()]), ":3p", False, False)
def c3658_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[123][sp]", False)
def c3659_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":(?:[NAQ].*:m:[si]|G|M)")
def c3660_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":(?:[NAQ].*:f:[si]|G|M)")
def c3661_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":(?:[NAQ].*:[si]|G|M)")
def c3663_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":(?:A|G|M|1p)")
def c3664_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":(?:A|G|M|2p)")
def c3666_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V", False)
def c3667_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(3), m.group(3)), ":V", False)
def c3668_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":2s", False) or look(s[:m.start()],"(?i)\\b(?:je|tu|on|ils?|elles?|nous) +$")
def c3669_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(2), m.group(2)), ":2s|>(ils?|elles?|on) ", False) or look(s[:m.start()],"(?i)\\b(?:je|tu|on|ils?|elles?|nous) +$")
def c3683_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":V", False)
def c3686_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":Y")
def c3692_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],r"(?i)\b(?:ce que?|tout) ")
def c3699_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V", False) and not (m.group(1).endswith("ez") and look(s[m.end():]," +vous"))
def c3702_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Q|2p)", False)
def c3705_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:aimer|aller|désirer|devoir|espérer|pouvoir|préférer|souhaiter|venir) ", False) and not morph(dDA, (m.start(1), m.group(1)), ":[GN]", False) and morph(dDA, (m.start(2), m.group(2)), ":V", False)
def c3709_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">devoir ", False) and morph(dDA, (m.start(2), m.group(2)), ":V", False) and not morph(dDA, prevword1(s[:m.start()]), ":D", False)
def c3712_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:cesser|décider|défendre|suggérer|commander|essayer|tenter|choisir|permettre|interdire) ", False) and morph(dDA, (m.start(2), m.group(2)), ":(?:Q|2p)", False)
def c3715_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Q|2p)", False)
def c3718_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ">valoir ", False) and morphex(dDA, (m.start(2), m.group(2)), ":(?:Q|2p)", ":[GM]")
def c3720_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V1", ":N") and not look(s[:m.start()],"> +$")
def c3721_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V1", ":N")
def c3730_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0e", False) and (morphex(dDA, (m.start(2), m.group(2)), ":Y", ":[NAQ]") or m.group(2) in aSHOULDBEVERB) and not re.match(u"(?i)(?:soit|été)$", m.group(1)) and not morph(dDA, prevword1(s[:m.start()]), ":Y|>ce", False, False) and not look(s[:m.start()],"(?i)ce (?:>|qu|que >) $") and not look_chk1(dDA, s[:m.start()], 0,u"(\w[\w-]+) +> $", ":Y") and not look_chk1(dDA, s[:m.start()], 0,u"^ +>? *(\w[\w-]+)", ":Y")
def c3735_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":V0a", False) and morph(dDA, (m.start(2), m.group(2)), ":Y", False)
def c3743_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":1s|>(?:en|y)", False)
def e3743_1 (s, m):
    return suggVerb(m.group(1), ":1s")
def c3746_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:1s|G)") and not (morph(dDA, (m.start(2), m.group(2)), ":[PQ]", False) and morph(dDA, prevword1(s[:m.start()]), ":V0.*:1s", False, False))
def e3746_1 (s, m):
    return suggVerb(m.group(2), ":1s")
def c3749_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:1s|G|1p)")
def e3749_1 (s, m):
    return suggVerb(m.group(2), ":1s")
def c3752_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:1s|G|1p)")
def e3752_1 (s, m):
    return suggVerb(m.group(2), ":1s")
def c3755_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:1s|G|1p|3p!)")
def e3755_1 (s, m):
    return suggVerb(m.group(2), ":1s")
def c3760_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:G|[ISK].*:2s)") and not (morph(dDA, (m.start(2), m.group(2)), ":[PQ]", False) and morph(dDA, prevword1(s[:m.start()]), ":V0.*:2s", False, False))
def e3760_1 (s, m):
    return suggVerb(m.group(2), ":2s")
def c3763_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:G|[ISK].*:2s)")
def e3763_1 (s, m):
    return suggVerb(m.group(2), ":2s")
def c3766_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:G|2p|3p!|[ISK].*:2s)")
def e3766_1 (s, m):
    return suggVerb(m.group(2), ":2s")
def c3771_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3s|P|G)") and not (morph(dDA, (m.start(2), m.group(2)), ":[PQ]", False) and morph(dDA, prevword1(s[:m.start()]), ":V0.*:3s", False, False))
def e3771_1 (s, m):
    return suggVerb(m.group(2), ":3s")
def c3774_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3s|P|G)")
def e3774_1 (s, m):
    return suggVerb(m.group(2), ":3s")
def c3778_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:N|A|3s|P|Q|G|V0e.*:3p)")
def e3778_1 (s, m):
    return suggVerb(m.group(2), ":3s")
def c3782_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3s|P|Q|G)")
def e3782_1 (s, m):
    return suggVerb(m.group(2), ":3s")
def c3786_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3s|P|Q|G|3p!)") and not morph(dDA, prevword1(s[:m.start()]), ":[VR]|>de", False, False) and not(m.group(1).endswith("out") and morph(dDA, (m.start(2), m.group(2)), ":Y", False))
def e3786_1 (s, m):
    return suggVerb(m.group(2), ":3s")
def c3790_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:3s|P|G|3p!)") and not morph(dDA, prevword1(s[:m.start()]), ":R|>(?:et|ou)", False, False) and not (morph(dDA, (m.start(1), m.group(1)), ":[PQ]", False) and morph(dDA, prevword1(s[:m.start()]), ":V0.*:3s", False, False))
def e3790_1 (s, m):
    return suggVerb(m.group(1), ":3s")
def c3794_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:3s|P|G|3p!)") and not morph(dDA, prevword1(s[:m.start()]), ":R|>(?:et|ou)", False, False)
def e3794_1 (s, m):
    return suggVerb(m.group(1), ":3s")
def c3798_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":3p", ":(?:G|3s)") and not prevword1(s[:m.start()])
def c3801_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":3s", ":(?:G|3p)") and not prevword1(s[:m.start()])
def e3805_1 (s, m):
    return m.group(1)[:-1]+"t"
def c3807_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3s|P|G)") and morphex(dDA, prevword1(s[:m.start()]), ":C", ":(?:Y|P|Q|[123][sp]|R)", True) and not( m.group(1).endswith("ien") and look(s[:m.start()],"> +$") and morph(dDA, (m.start(2), m.group(2)), ":Y", False) )
def e3807_1 (s, m):
    return suggVerb(m.group(2), ":3s")
def c3813_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":Y", False) and morph(dDA, (m.start(2), m.group(2)), ":V.\w+(?!.*:(?:3s|P|Q|Y|3p!))")
def e3813_1 (s, m):
    return suggVerb(m.group(2), ":3s")
def c3818_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":C", ":(?:Y|P)", True) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[si]", False) and morphex(dDA, (m.start(3), m.group(3)), ":V", ":(?:3s|P|Q|Y|3p!|G)") and not (look(s[:m.start()],"(?i)\\b(?:et|ou) +$") and morph(dDA, (m.start(3), m.group(3)), ":[1-3]p", False)) and not look(s[:m.start()],r"(?i)\bni .* ni\b")
def e3818_1 (s, m):
    return suggVerb(m.group(3), ":3s")
def c3822_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":C", ":(?:Y|P)", True) and morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[si]", False) and morphex(dDA, (m.start(3), m.group(3)), ":V", ":(?:3s|1p|P|Q|Y|3p!|G)") and not (look(s[:m.start()],"(?i)\\b(?:et|ou) +$") and morph(dDA, (m.start(3), m.group(3)), ":[123]p", False)) and not look(s[:m.start()],r"(?i)\bni .* ni\b")
def e3822_1 (s, m):
    return suggVerb(m.group(3), ":3s")
def c3828_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":C", ":(?:Y|P)", True) and isAmbiguousAndWrong(m.group(2), m.group(3), ":s", ":3s") and not (look(s[:m.start()],"(?i)\\b(?:et|ou) +$") and morph(dDA, (m.start(3), m.group(3)), ":(?:[123]p|p)", False)) and not look(s[:m.start()],r"(?i)\bni .* ni\b")
def e3828_1 (s, m):
    return suggVerb(m.group(3), ":3s")
def c3833_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":C", ":(?:Y|P)", True) and isVeryAmbiguousAndWrong(m.group(2), m.group(3), ":s", ":3s", not prevword1(s[:m.start()])) and not (look(s[:m.start()],"(?i)\\b(?:et|ou) +$") and morph(dDA, (m.start(3), m.group(3)), ":(?:[123]p|p)", False)) and not look(s[:m.start()],r"(?i)\bni .* ni\b")
def e3833_1 (s, m):
    return suggVerb(m.group(3), ":3s")
def c3839_1 (s, sx, m, dDA, sCountry):
    return ( morph(dDA, (m.start(0), m.group(0)), ":1s") or ( look(s[:m.start()],"> +$") and morph(dDA, (m.start(0), m.group(0)), ":1s", False) ) ) and not (m.group(0)[0:1].isupper() and look(s[:m.start()],r"\w")) and not look(s[:m.start()],u"(?i)\\b(?:j(?:e |’)|moi,? qui )")
def e3839_1 (s, m):
    return suggVerb(m.group(0), ":3s")
def c3843_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(0), m.group(0)), ":2s", ":(?:E|G|W|M|J|[13][sp]|2p)") and not m.group(0)[0:1].isupper() and not look(s[:m.start()],"^ *$") and ( not morph(dDA, (m.start(0), m.group(0)), ":[NAQ]", False) or look(s[:m.start()],"> +$") ) and not look(sx[:m.start()],u"(?i)\\bt(?:u |’|oi,? qui |oi seul )")
def e3843_1 (s, m):
    return suggVerb(m.group(0), ":3s")
def c3848_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(0), m.group(0)), ":2s", ":(?:G|W|M|J|[13][sp]|2p)") and not (m.group(0)[0:1].isupper() and look(s[:m.start()],r"\w")) and ( not morph(dDA, (m.start(0), m.group(0)), ":[NAQ]", False) or look(s[:m.start()],"> +$") ) and not look(sx[:m.start()],u"(?i)\\bt(?:u |’|oi,? qui |oi seul )")
def e3848_1 (s, m):
    return suggVerb(m.group(0), ":3s")
def c3853_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(0), m.group(0)), ":[12]s", ":(?:E|G|W|M|J|3[sp]|2p|1p)") and not (m.group(0)[0:1].isupper() and look(s[:m.start()],r"\w")) and ( not morph(dDA, (m.start(0), m.group(0)), ":[NAQ]", False) or look(s[:m.start()],"> +$") or ( re.match(u"(?i)étais$", m.group(0)) and not morph(dDA, prevword1(s[:m.start()]), ":[DA].*:p", False, True) ) ) and not look(sx[:m.start()],u"(?i)\\b(?:j(?:e |’)|moi,? qui |t(?:u |’|oi,? qui |oi seul ))")
def e3853_1 (s, m):
    return suggVerb(m.group(0), ":3s")
def c3858_1 (s, sx, m, dDA, sCountry):
    return not (m.group(0)[0:1].isupper() and look(s[:m.start()],r"\w")) and not look(sx[:m.start()],u"(?i)\\b(?:j(?:e |’)|moi,? qui |t(?:u |’|oi,? qui |oi seul ))")
def e3858_1 (s, m):
    return suggVerb(m.group(0), ":3s")
def c3861_1 (s, sx, m, dDA, sCountry):
    return not (m.group(0)[0:1].isupper() and look(s[:m.start()],r"\w")) and not look(sx[:m.start()],u"(?i)\\b(?:j(?:e |’)|moi,? qui |t(?:u |’|oi,? qui |oi seul ))")
def e3861_1 (s, m):
    return suggVerb(m.group(0), ":3s")
def c3866_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:1p|3[sp])") and not look(s[m.end():],"^ +(?:je|tu|ils?|elles?|on|[vn]ous)")
def e3866_1 (s, m):
    return suggVerb(m.group(1), ":1p")
def c3869_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":1p") and not look(s[m.end():],"^ +(?:je|tu|ils?|elles?|on|[vn]ous)")
def e3869_1 (s, m):
    return suggVerb(m.group(1), ":1p")
def c3872_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":1p") and not look(s[m.end():],"^ +(?:ils|elles)")
def e3872_1 (s, m):
    return suggVerb(m.group(1), ":1p")
def c3877_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:2p|3[sp])") and not look(s[m.end():],"^ +(?:je|ils?|elles?|on|[vn]ous)")
def e3877_1 (s, m):
    return suggVerb(m.group(1), ":2p")
def c3880_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":2p") and not look(s[m.end():],"^ +(?:je|ils?|elles?|on|[vn]ous)")
def e3880_1 (s, m):
    return suggVerb(m.group(1), ":2p")
def c3885_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(0), m.group(0)), ":V.*:1p", ":[EGMNAJ]") and not (m.group(0)[0:1].isupper() and look(s[:m.start()],r"\w")) and not look(s[:m.start()],u"(?i)\\b(?:nous|et moi) ")
def e3885_1 (s, m):
    return suggVerb(m.group(0), ":3p")
def c3889_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(0), m.group(0)), ":V.*:2p", ":[EGMNAJ]") and not (m.group(0)[0:1].isupper() and look(s[:m.start()],r"\w")) and not look(s[:m.start()],u"(?i)\\b(?:vous|et toi|toi et) ")
def c3895_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3p|P|Q|G)") and not (morph(dDA, (m.start(2), m.group(2)), ":[PQ]", False) and morph(dDA, prevword1(s[:m.start()]), ":V0.*:3p", False, False))
def e3895_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3898_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3p|P|Q|G)")
def e3898_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3902_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3p|P|Q|G)")
def e3902_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3906_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3p|P|Q|G)") and not morph(dDA, prevword1(s[:m.start()]), ":[VR]", False, False)
def e3906_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3910_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:3p|P|Q|G)") and not morph(dDA, prevword1(s[:m.start()]), ":R", False, False) and not (morph(dDA, (m.start(1), m.group(1)), ":[PQ]", False) and morph(dDA, prevword1(s[:m.start()]), ":V0.*:3p", False, False))
def e3910_1 (s, m):
    return suggVerb(m.group(1), ":3p")
def c3913_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V", ":(?:3p|P|Q|G)") and not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def e3913_1 (s, m):
    return suggVerb(m.group(1), ":3p")
def c3921_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],u"(?i)\\b(?:à|avec|sur|chez|par|dans) +$")
def c3925_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3p|P|Q|mg)") and not morph(dDA, prevword1(s[:m.start()]), ":[VR]|>de ", False, False)
def e3925_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3929_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:3p|P|Q|G)") and not morph(dDA, prevword1(s[:m.start()]), ":[VR]", False, False)
def e3929_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3933_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:G|N|A|3p|P|Q)") and not morph(dDA, prevword1(s[:m.start()]), ":[VR]", False, False)
def e3933_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3937_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]", False) and morphex(dDA, (m.start(3), m.group(3)), ":V", ":(?:[13]p|P|Q|Y|G)") and morphex(dDA, prevword1(s[:m.start()]), ":C", ":[YP]", True)
def e3937_1 (s, m):
    return suggVerb(m.group(3), ":3p")
def c3940_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(2), m.group(2)), ":[NAQ].*:[pi]", False) and morphex(dDA, (m.start(3), m.group(3)), ":V", ":(?:[13]p|P|Y|G)") and morphex(dDA, prevword1(s[:m.start()]), ":C", ":[YP]", True)
def e3940_1 (s, m):
    return suggVerb(m.group(3), ":3p")
def c3945_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[pi]", False) and morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:[13]p|P|G|Q.*:p)") and morph(dDA, nextword1(s, m.end()), ":(?:R|D.*:p)|>au ", False, True)
def e3945_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3948_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":[NAQ].*:[pi]", False) and morphex(dDA, (m.start(2), m.group(2)), ":V", ":(?:[13]p|P|G)")
def e3948_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3954_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":C", ":[YP]", True) and isAmbiguousAndWrong(m.group(2), m.group(3), ":p", ":3p")
def e3954_1 (s, m):
    return suggVerb(m.group(3), ":3p")
def c3958_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":C", ":[YP]", True) and isVeryAmbiguousAndWrong(m.group(1), m.group(2), ":p", ":3p", not prevword1(s[:m.start()]))
def e3958_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3962_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":C", ":[YP]", True) and isVeryAmbiguousAndWrong(m.group(1), m.group(2), ":m:p", ":3p", not prevword1(s[:m.start()]))
def e3962_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3966_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, prevword1(s[:m.start()]), ":C", ":[YP]", True) and isVeryAmbiguousAndWrong(m.group(1), m.group(2), ":f:p", ":3p", not prevword1(s[:m.start()]))
def e3966_1 (s, m):
    return suggVerb(m.group(2), ":3p")
def c3974_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V0e", ":3s")
def e3974_1 (s, m):
    return suggVerb(m.group(1), ":3s")
def c3978_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V0e.*:3s", ":3p")
def e3978_1 (s, m):
    return m.group(1)[:-1]
def c3983_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V0e", ":3p")
def e3983_1 (s, m):
    return suggVerb(m.group(1), ":3p")
def c3987_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":V0e.*:3p", ":3s")
def c3995_1 (s, sx, m, dDA, sCountry):
    return not look(s[:m.start()],"(?:et|ou|[dD][eu]|ni) +$") and morph(dDA, (m.start(1), m.group(1)), ":M", False) and morphex(dDA, (m.start(2), m.group(2)), ":[123][sp]", ":(?:G|3s|3p!|P|M|[AQ].*:[si])") and not morph(dDA, prevword1(s[:m.start()]), ":[VRD]", False, False) and not look(s[:m.start()],u"([A-ZÉÈ][\w-]+), +([A-ZÉÈ][\w-]+), +$")
def e3995_1 (s, m):
    return suggVerb(m.group(2), ":3s")
def c4002_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":M", False) and morph(dDA, (m.start(2), m.group(2)), ":M", False) and morphex(dDA, (m.start(3), m.group(3)), ":[123][sp]", ":(?:G|3p|P|Q.*:[pi])") and not morph(dDA, prevword1(s[:m.start()]), ":R", False, False)
def e4002_1 (s, m):
    return suggVerb(m.group(3), ":3p")
def c4012_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":(?:[12]s|3p)", ":(?:3s|G|W|3p!)")
def e4012_1 (s, m):
    return suggVerb(m.group(1), ":3s")
def c4017_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[123]s", ":(?:3p|G|W)")
def e4017_1 (s, m):
    return suggVerb(m.group(1), ":3p")
def c4022_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[12][sp]", ":(?:G|W|3[sp]|Y|P|Q)")
def c4027_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[12][sp]", ":(?:G|W|3[sp])")
def c4035_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V.*:1s", ":[GNW]") and not look(s[:m.start()],r"(?i)\bje +>? *$")
def c4038_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":V.*:1s", ":[GNW]") and not look(s[:m.start()],r"(?i)\bje +>? *$")
def c4041_1 (s, sx, m, dDA, sCountry):
    return not look(s[m.end():],"^ +(?:en|y|ne|>)") and morphex(dDA, (m.start(1), m.group(1)), ":V.*:2s", ":[GNW]") and not look(s[:m.start()],r"(?i)\b(?:je|tu) +>? *$")
def c4044_1 (s, sx, m, dDA, sCountry):
    return not look(s[m.end():],"^ +(?:en|y|ne|>)") and morphex(dDA, (m.start(1), m.group(1)), ":V.*:3s", ":[GNW]") and not look(s[:m.start()],r"(?i)\b(?:ce|il|elle|on) +>? *$")
def c4047_1 (s, sx, m, dDA, sCountry):
    return not look(s[m.end():],"^ +(?:en|y|ne|aussi|>)") and morphex(dDA, (m.start(1), m.group(1)), ":V.*:3s", ":[GNW]") and not look(s[:m.start()],r"(?i)\b(?:ce|il|elle|on) +>? *$")
def c4050_1 (s, sx, m, dDA, sCountry):
    return not look(s[m.end():],"^ +(?:en|y|ne|aussi|>)") and morphex(dDA, (m.start(1), m.group(1)), ":V.*:1p", ":[GNW]") and not morph(dDA, prevword1(s[:m.start()]), ":Os", False, False) and not morph(dDA, nextword1(s, m.end()), ":Y", False, False)
def c4054_1 (s, sx, m, dDA, sCountry):
    return not look(s[m.end():],"^ +(?:en|y|ne|aussi|>)") and not m.group(1).endswith("euillez") and morphex(dDA, (m.start(1), m.group(1)), ":V.*:2pl", ":[GNW]") and not morph(dDA, prevword1(s[:m.start()]), ":Os", False, False) and not morph(dDA, nextword1(s, m.end()), ":Y", False, False)
def c4058_1 (s, sx, m, dDA, sCountry):
    return not look(s[m.end():],"^ +(?:en|y|ne|aussi|>)") and morphex(dDA, (m.start(1), m.group(1)), ":V.*:3p", ":[GNW]") and not look(s[:m.start()],r"(?i)\b(?:ce|ils|elles) +>? *$")
def c4063_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":1[sśŝ]", False) and _oDict.isValid(m.group(1)) and not re.match("(?i)vite$", m.group(1))
def e4063_1 (s, m):
    return suggVerb(m.group(1), "1isg")
def c4065_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":[ISK].*:2s", False) and _oDict.isValid(m.group(1)) and not re.match("(?i)vite$", m.group(1))
def e4065_1 (s, m):
    return suggVerb(m.group(1), ":2s")
def c4067_1 (s, sx, m, dDA, sCountry):
    return m.group(1) != "t" and not morph(dDA, (m.start(1), m.group(1)), ":3s", False) and (not m.group(1).endswith(u"oilà") or m.group(2) != "il") and _oDict.isValid(m.group(1)) and not re.match("(?i)vite$", m.group(1))
def e4067_1 (s, m):
    return suggVerb(m.group(1), ":3s")
def c4069_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":3p", ":3s") and _oDict.isValid(m.group(1))
def c4071_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":(?:1p|2[sp])", False) and _oDict.isValid(m.group(1)) and not re.match("(?i)(vite|chez)$", m.group(1))
def c4073_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":2p", False) and _oDict.isValid(m.group(1)) and not re.match("(?i)(tes|vite)$", m.group(1)) and not _oDict.isValid(m.group(0))
def c4075_1 (s, sx, m, dDA, sCountry):
    return m.group(1) != "t" and not morph(dDA, (m.start(1), m.group(1)), ":3p", False) and _oDict.isValid(m.group(1))
def e4075_1 (s, m):
    return suggVerb(m.group(1), ":3p")
def c4078_1 (s, sx, m, dDA, sCountry):
    return not morph(dDA, (m.start(1), m.group(1)), ":V", False) and not re.match("(?i)vite$", m.group(1)) and _oDict.isValid(m.group(1)) and not ( m.group(0).endswith("il") and m.group(1).endswith(u"oilà") ) and not ( m.group(1) == "t" and m.group(0).endswith(("il", "elle", "on", "ils", "elles")) )
def c4087_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Os|M)", False) and morphex(dDA, (m.start(2), m.group(2)), ":[SK]", ":(?:G|V0|I)") and not prevword1(s[:m.start()])
def c4090_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":[SK]", ":(?:G|V0|I)") and not prevword1(s[:m.start()])
def c4094_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Os|M)", False) and morphex(dDA, (m.start(2), m.group(2)), ":S", ":[IG]")
def e4094_1 (s, m):
    return suggVerbMode(m.group(2), ":I", m.group(1))
def c4094_2 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Os|M)", False) and morph(dDA, (m.start(2), m.group(2)), ":K", False)
def e4094_2 (s, m):
    return suggVerbMode(m.group(2), ":If", m.group(1))
def c4101_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), u">(?:afin|pour|quoi|permettre|falloir|vouloir|ordonner|exiger|désirer|douter|suffire) ", False) and morph(dDA, (m.start(2), m.group(2)), ":(?:Os|M)", False) and not morph(dDA, (m.start(3), m.group(3)), ":[GYS]", False)
def e4101_1 (s, m):
    return suggVerbMode(m.group(3), ":S", m.group(2))
def c4106_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Os|M)", False) and not morph(dDA, (m.start(2), m.group(2)), ":[GYS]", False)
def e4106_1 (s, m):
    return suggVerbMode(m.group(2), ":S", m.group(1))
def c4111_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(2), m.group(2)), ":S", ":[GIK]") and not re.match("e(?:usse|û[mt]es|ût)", m.group(2))
def e4111_1 (s, m):
    return suggVerbMode(m.group(2), ":I", m.group(1))
def c4114_1 (s, sx, m, dDA, sCountry):
    return morphex(dDA, (m.start(1), m.group(1)), ":S", ":[GIK]") and m.group(1) != "eusse"
def e4114_1 (s, m):
    return suggVerbMode(m.group(1), ":I", "je")
def c4119_1 (s, sx, m, dDA, sCountry):
    return morph(dDA, (m.start(1), m.group(1)), ":(?:Os|M)", False) and morph(dDA, (m.start(2), m.group(2)), ":V.*:S")
def e4119_1 (s, m):
    return suggVerbMode(m.group(2), ":I", m.group(1))

