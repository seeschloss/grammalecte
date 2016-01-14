#!/usr/bin/env python3

import sys
import os.path
import argparse

import grammalecte.fr as gce
import grammalecte.fr.lexicographe as lxg
import grammalecte.fr.textformatter as tf
import grammalecte.text as txt
import grammalecte.tokenizer as tzr
from grammalecte.echo import echo


def _getText (sInputText):
    if sys.stdin.isatty():
        sys.stderr.write(sInputText)
        sys.stderr.flush()

    try:
        sText = sys.stdin.readline()
    except EOFError:
        return ""

    if sys.platform == "win32":
        # Apparently, the console transforms «’» in «'».
        # So we reverse it to avoid many unuseful warnings.
        sText = sText.replace("'", "’")

    return sText


def parser (sText, oTokenizer, oDict, bDebug=False, aIgnoredRules=()):
    aGrammErrs = gce.parse(sText, "FR", bDebug)
    aSpellErrs = []

    if bDebug:
        print(aGrammErrs)

    if len(aIgnoredRules):
        lGrammErrs = list(aGrammErrs)
        for dGrammErr in aGrammErrs:
            if dGrammErr['sRuleId'] in aIgnoredRules:
                lGrammErrs.remove(dGrammErr)

        aGrammErrs = tuple(lGrammErrs)

    for tToken in oTokenizer.genTokens(sText):
        if tToken.type == "WORD" and not oDict.isValidToken(tToken.value):
            aSpellErrs.append(tToken)

    if not aGrammErrs and not aSpellErrs:
        return False
    else:
        return [aGrammErrs, aSpellErrs]

def showResult (sText, res, bAutocorrect=False):
    aGrammErrs = res[0]
    aSpellErrs = res[1]

    if bAutocorrect:
        sResult = sText
        aGrammErrs = sorted(aGrammErrs, key=lambda dGrammErr: -dGrammErr['nEnd'])
        for dGrammErr in aGrammErrs:
            if len(dGrammErr['aSuggestions']):
                sSuggestion = dGrammErr['aSuggestions'][0]
                sResult = sResult[0:dGrammErr['nStart']] + sSuggestion + sResult[dGrammErr['nEnd']:]
    else:
        sResult = txt.generateParagraph(sText, aGrammErrs, aSpellErrs)

    sys.stdout.write(sResult)

def main ():
    xParser = argparse.ArgumentParser()
    xParser.add_argument("-d", "--debug", help="display text transformation and disambiguation", action="store_true")
    xParser.add_argument("-p", "--parse", help="parse and display sentence structure", action="store_true")
    xParser.add_argument("-v", "--validate", help="validate text only", action="store_true")
    xParser.add_argument("-a", "--autocorrect", help="try to correct automatically", action="store_true")
    xParser.add_argument("-i", "--ignore-rule", help="ignore this rule (can be used more than once)", action="append", default=[])
    xParser.add_argument("-tf", "--textformatter", help="auto-format text", action="store_true")
    xArgs = xParser.parse_args()

    gce.load()
    gce.setOptions({"html": True})
    oDict = gce.getDictionary()
    oTokenizer = tzr.Tokenizer("fr")
    oLexGraphe = lxg.Lexicographe(oDict)

    if xArgs.textformatter:
        oTF = tf.TextFormatter()

    sInputText = "> "
    sText = _getText(sInputText)

    errors = False

    while sText:
        if xArgs.parse:
            for sWord in sText.split():
                if sWord:
                    echo("* {}".format(sWord))
                    for sMorph in oDict.getMorph(sWord):
                        echo("  {:<32} {}".format(sMorph, oLexGraphe.formatTags(sMorph)))
        else:
            if xArgs.textformatter:
                sText = oTF.formatText(sText)
                sys.stdout.write(sText)

            res = parser(sText, oTokenizer, oDict, bDebug=xArgs.debug, aIgnoredRules=xArgs.ignore_rule)

            if xArgs.validate:
                if res:
                    errors = True
            else:
                if res:
                    showResult(sText, res, xArgs.autocorrect)
                    errors = True
                else:
                    echo("No error found")

        sText = _getText(sInputText)

    if errors:
        sys.exit(1)


def coding ():
    import sys, locale, os
    print(sys.stdout.encoding)
    print(sys.stdout.isatty())
    print(locale.getpreferredencoding())
    print(sys.getfilesystemencoding())


if __name__ == '__main__':
    main()
