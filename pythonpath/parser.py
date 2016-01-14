#!python3

import sys
import os.path
import argparse

import grammalecte.fr as gce
import grammalecte.fr.lexicographe as lxg
import grammalecte.fr.textformatter as tf
import grammalecte.text as txt
import grammalecte.tokenizer as tzr
from grammalecte.echo import echo


_EXAMPLE = "Quoi ? Racontes ! Racontes-moi ! Bon sangg, parles ! Oui. Il y a des menteur partout. " \
           "Je suit sidéré par la brutales arrogance de cette homme-là. Quelle salopard ! Un escrocs de la pire espece. " \
           "Quant sera t’il châtiés pour ses mensonge ?             Merde ! J’en aie marre."


def _getText (sInputText):
    sText = input(sInputText)
    if sText == "*":
        return _EXAMPLE
    if sys.platform == "win32":
        # Apparently, the console transforms «’» in «'».
        # So we reverse it to avoid many unuseful warnings.
        sText = sText.replace("'", "’")
    return sText


def parser (sText, oTokenizer, oDict, nWidth=100, bDebug=False, bEmptyIfNoErrors=False):
    aGrammErrs = gce.parse(sText, "FR", bDebug)
    aSpellErrs = []
    for tToken in oTokenizer.genTokens(sText):
        if tToken.type == "WORD" and not oDict.isValidToken(tToken.value):
            aSpellErrs.append(tToken)
    if bEmptyIfNoErrors and not aGrammErrs and not aSpellErrs:
        return ""
    return txt.generateParagraph(sText, aGrammErrs, aSpellErrs, nWidth)


def main ():
    xParser = argparse.ArgumentParser()
    xParser.add_argument("-f", "--file", help="parse file (UTF-8 required!) [on Windows, -f is similar to -ff]", type=str)
    xParser.add_argument("-ff", "--file_to_file", help="parse file (UTF-8 required!) and create a result file (*.res.txt)", type=str)
    xParser.add_argument("-d", "--debug", help="display text transformation and disambiguation", action="store_true")
    xParser.add_argument("-w", "--width", help="width in characters (40 < width < 200; default: 100)", type=int, choices=range(40,201,10), default=100)
    xParser.add_argument("-tf", "--textformatter", help="auto-format text", action="store_true")
    xArgs = xParser.parse_args()

    if sys.platform == "win32" and xArgs.file:
        xArgs.file_to_file = xArgs.file
        xArgs.file = None

    gce.load()
    gce.setOptions({"html": True})
    echo("Grammalecte v{}".format(gce.version))
    oDict = gce.getDictionary()
    oTokenizer = tzr.Tokenizer("fr")
    oLexGraphe = lxg.Lexicographe(oDict)
    if xArgs.textformatter:
        oTF = tf.TextFormatter()

    if xArgs.file:
        if os.path.isfile(xArgs.file):
            with open(xArgs.file, "r", encoding="utf-8") as hSrc:
                for sText in hSrc:
                    if xArgs.textformatter:
                        sText = oTF.formatText(sText)
                    echo(parser(sText, oTokenizer, oDict, nWidth=xArgs.width, bDebug=xArgs.debug))
        else:
            print("# Error: file not found.")
    elif xArgs.file_to_file:
        if os.path.isfile(xArgs.file_to_file):
            with open(xArgs.file_to_file, "r", encoding="utf-8") as hSrc, \
                 open(xArgs.file_to_file[:xArgs.file_to_file.rfind(".")]+".res.txt", "w", encoding="utf-8") as hDst:
                for i, sText in enumerate(hSrc, 1):
                    if xArgs.textformatter:
                        sText = oTF.formatText(sText)
                    hDst.write(parser(sText, oTokenizer, oDict, nWidth=xArgs.width, bDebug=xArgs.debug))
                    print("§ %d\r" % i, end="", flush=True)
        else:
            print("# Error: file not found.")
    else:
        sInputText = "\n~==========~ Écrivez votre texte [Entrée pour quitter] ~==========~\n"
        sText = _getText(sInputText)
        while sText:
            if sText.startswith("?"):
                for sWord in sText[1:].split():
                    if sWord:
                        echo("* {}".format(sWord))
                        for sMorph in oDict.getMorph(sWord):
                            echo("  {:<32} {}".format(sMorph, oLexGraphe.formatTags(sMorph)))
            elif sText == "rl":
                # reload (todo)
                pass
            else:
                if xArgs.textformatter:
                    sText = oTF.formatText(sText)
                res = parser(sText, oTokenizer, oDict, nWidth=xArgs.width, bDebug=xArgs.debug, bEmptyIfNoErrors=True)
                echo("\n"+res  if res  else "\nNo error found.")
            sText = _getText(sInputText)


def coding ():
    import sys, locale, os
    print(sys.stdout.encoding)
    print(sys.stdout.isatty())
    print(locale.getpreferredencoding())
    print(sys.getfilesystemencoding())


if __name__ == '__main__':
    main()
