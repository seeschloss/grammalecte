#!python3

from textwrap import wrap


def generateParagraph (sParagraph, aGrammErrs, aSpellErrs, nWidth=100):
    "Returns a text with readable errors"
    if not sParagraph:
        return ""
    lGrammErrs = sorted(aGrammErrs, key=lambda d: d["nStart"])
    lSpellErrs = sorted(aSpellErrs, key=lambda t: t.start)
    lLines = wrap(sParagraph, nWidth, drop_whitespace=False)
    sText = ""
    nOffset = 0
    for sLine in lLines:
        sText += sLine + "\n"
        ln = len(sLine)
        sErrLine = ""
        nLineOffset = 0
        nGrammErr = 0
        nSpellErr = 0
        for dErr in lGrammErrs:
            nStart = dErr["nStart"] - nOffset
            if nStart < ln:
                nGrammErr += 1
                if nStart >= nLineOffset:
                    sErrLine += " " * (nStart - nLineOffset) + "^" *(dErr["nEnd"] - dErr["nStart"])
                    nLineOffset = len(sErrLine)
            else:
                break
        for tErr in lSpellErrs:
            nStart = tErr.start - nOffset
            if nStart < ln:
                nSpellErr += 1
                nEnd = tErr.end - nOffset
                if nEnd > len(sErrLine):
                    sErrLine += " " * (nEnd - len(sErrLine))
                sErrLine = sErrLine[:nStart] + "°" * (nEnd - nStart) + sErrLine[nEnd:]
            else:
                break
        if sErrLine:
            sText += sErrLine + "\n"
        if nGrammErr:
            for dErr in lGrammErrs[:nGrammErr]:
                sMsg, *others = getReadableError(dErr).split("\n")
                sText += "\n".join(wrap(sMsg, nWidth, subsequent_indent="  ")) + "\n"
                for arg in others:
                    sText += "\n".join(wrap(arg, nWidth, subsequent_indent="    ")) + "\n"
            sText += "\n"
            del lGrammErrs[0:nGrammErr]
        if nSpellErr:
            del lSpellErrs[0:nSpellErr]
        nOffset += ln
    return sText


def getReadableError (dErr):
    "Returns an error dErr as a readable error"
    try:
        s = u"* {nStart}:{nEnd}  # {sRuleId}  : ".format(**dErr)
        s += dErr.get("sMessage", "# error : message not found")
        if dErr.get("aSuggestions", None):
            s += "\n  > Suggestions : " + " | ".join(dErr.get("aSuggestions", "# error : suggestions not found"))
        if dErr.get("URL", None):
            s += "\n  > URL: " + dErr["URL"]
        return s
    except KeyError:
        return u"* Non-compliant error: {}".format(dErr)
