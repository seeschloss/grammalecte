#!python3
# -*- coding: UTF-8 -*-

import os
import traceback
import pkgutil

from . import str_transform as st


class IBDAWG:
    """INDEXABLE BINARY DIRECT ACYCLIC WORD GRAPH"""

    def __init__ (self, sDicName):
        self.by = pkgutil.get_data(__package__, "_dictionaries/" + sDicName)
        if not self.by:
            raise OSError("# Error. File not found or not loadable: "+sDicName)

        if self.by[0:7] != b"/pyfsa/":
            raise TypeError("# Error. Not a pyfsa binary dictionary. Header: {}".format(self.by[0:9]))
        if not(self.by[7:8] == b"1" or self.by[7:8] == b"2" or self.by[7:8] == b"3"):
            raise ValueError("# Error. Unknown dictionary version: {}".format(self.by[7:8]))
        try:
            header, info, values, bdic = self.by.split(b"\0\0\0\0", 3)
        except Exception:
            raise Exception

        self.sName = sDicName
        self.nVersion = int(self.by[7:8].decode("utf-8"))
        self.sHeader = header.decode("utf-8")
        self.lArcVal = values.decode("utf-8").split("\t")
        self.nArcVal = len(self.lArcVal)
        self.byDic = bdic

        l = info.decode("utf-8").split("/")
        self.sLang = l[0]
        self.nChar = int(l[1])
        self.nBytesArc = int(l[2])
        self.nBytesNodeAddress = int(l[3])
        self.nEntries = int(l[4])
        self.nNode = int(l[5])
        self.nArc = int(l[6])
        self.nAff = int(l[7])
        self.cStemming = l[8]
        if self.cStemming == "S":
            self.funcStemming = st.getStemFromSuffixCode
        elif self.cStemming == "A":
            self.funcStemming = st.getStemFromAffixCode
        else:
            self.funcStemming = st.noStemming
        self.nTag = self.nArcVal - self.nChar - self.nAff
        self.dChar = {}
        for i in range(1, self.nChar):
            self.dChar[self.lArcVal[i]] = i
            
        self._arcMask = (2 ** ((self.nBytesArc * 8) - 3)) - 1
        self._finalNodeMask = 1 << ((self.nBytesArc * 8) - 1)
        self._lastArcMask = 1 << ((self.nBytesArc * 8) - 2)
        self._addrBitMask = 1 << ((self.nBytesArc * 8) - 3)  # version 2

        self.nBytesOffset = 1 # version 3

        # Configuring DAWG functions according to nVersion
        if self.nVersion == 1:
            self.morph = self._morph1
            self.stem = self._stem1
            self._lookupArcNode = self._lookupArcNode1
            self._writeNodes = self._writeNodes1
        elif self.nVersion == 2:
            self.morph = self._morph2
            self.stem = self._stem2
            self._lookupArcNode = self._lookupArcNode2
            self._writeNodes = self._writeNodes2
        elif self.nVersion == 3:
            self.morph = self._morph3
            self.stem = self._stem3
            self._lookupArcNode = self._lookupArcNode3
            self._writeNodes = self._writeNodes3
        else:
            raise ValueError("  # Error: unknown code: {}".format(self.nVersion))

    def getInfo (self):
        return  "  Language: {0.sLang:>10}      Version: {0.nVersion:>2}      Stemming: {0.cStemming}FX\n" \
                "  Arcs values:  {0.nArcVal:>10,} = {0.nChar:>5,} characters,  {0.nAff:>6,} affixes,  {0.nTag:>6,} tags\n" \
                "  Dictionary: {0.nEntries:>12,} entries,    {0.nNode:>11,} nodes,   {0.nArc:>11,} arcs\n" \
                "  Address size: {0.nBytesNodeAddress:>1} bytes,  Arc size: {0.nBytesArc:>1} bytes\n".format(self)

    def writeModule (self, spfDst):
        with open(spfDst, 'w') as hDst:
            hDst.write("#!python3\n")
            hDst.write("# -*- coding: UTF-8 -*-\n")
            hDst.write("bdic = ")
            hDst.write(str(self.by))
            hDst.write("\n")
            hDst.close()

    def isValidToken (self, sToken):
        "checks if sToken is valid (if there is hyphens in sToken, sToken is split, each part is checked)"
        if self.isValid(sToken):
            return True
        if "-" in sToken:
            if sToken.count("-") > 4:
                return True
            return all(self.isValid(sWord)  for sWord in sToken.split("-"))
        return False

    def isValid (self, sWord):
        "checks if sWord is valid (different casing tested if the first letter is a capital)"
        if not sWord:
            return None
        if "’" in sWord: # ugly hack
            sWord = sWord.replace("’", "'")
        if self.lookup(sWord):
            return True
        if sWord[0:1].isupper():
            if len(sWord) > 1:
                if sWord.istitle():
                    return bool(self.lookup(sWord.lower()))
                if sWord.isupper():
                    return bool(self.lookup(sWord.lower()) or self.lookup(sWord.capitalize()))
            else:
                return bool(self.lookup(sWord.lower()))
        return False

    def lookup (self, sWord):
        "returns True if sWord in dictionary (strict verification)"
        iAddr = 0
        for c in sWord:
            if c not in self.dChar:
                return False
            iAddr = self._lookupArcNode(self.dChar[c], iAddr)
            if iAddr == None:
                return False
        return int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big') & self._finalNodeMask

    def getSugg (self, sWord, iAddr=0, sNewWord=""):
        "not finished"
        # RECURSIVE FUNCTION
        if not sWord:
            if int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big') & self._finalNodeMask:
                return [sNewWord]
            return []
        lSugg = []
        lArc = self._getSimilarArcs(sWord[0:1], iAddr)
        if lArc:
            for t in lArc:
                lSugg.extend(self._lookupAndSuggest(sWord[1:], t[1], sNewWord+t[0]))
        else:
            pass
        return lSugg

    def _getSimilarArcs (self, cChar, iAddr):
        lArc = []
        for c in st.dSimilarChars.get(cChar, cChar):
            jAddr = self._lookupArcNode(self.dChar[c], iAddr)
            if jAddr:
                lArc.append((c, iAddr))
        return lArc

    def getMorph (self, sWord):
        "retrieves morphologies list, different casing allowed"
        l = self.morph(sWord)
        if sWord[0:1].isupper():
            l.extend(self.morph(sWord.lower()))
            if sWord.isupper() and len(sWord) > 1:
                l.extend(self.morph(sWord.capitalize()))
        return l

    # def morph (self, sWord):
    #     is defined in __init__

    # VERSION 1
    def _morph1 (self, sWord):
        "returns morphologies of sWord"
        iAddr = 0
        for c in sWord:
            if c not in self.dChar:
                return []
            iAddr = self._lookupArcNode(self.dChar[c], iAddr)
            if iAddr == None:
                return []
        if (int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big') & self._finalNodeMask):
            l = []
            nRawArc = 0
            while not (nRawArc & self._lastArcMask):
                iEndArcAddr = iAddr + self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                if nArc >= self.nChar:
                    # This value is not a char, this is a stemming code 
                    sStem = ">" + self.funcStemming(sWord, self.lArcVal[nArc])
                    # Now , we go to the next node and retrieve all following arcs values, all of them are tags
                    iAddr2 = int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
                    nRawArc2 = 0
                    while not (nRawArc2 & self._lastArcMask):
                        iEndArcAddr2 = iAddr2 + self.nBytesArc
                        nRawArc2 = int.from_bytes(self.byDic[iAddr2:iEndArcAddr2], byteorder='big')
                        l.append(sStem + " " + self.lArcVal[nRawArc2 & self._arcMask])
                        iAddr2 = iEndArcAddr2+self.nBytesNodeAddress
                iAddr = iEndArcAddr+self.nBytesNodeAddress
            return l
        return []

    def _stem1 (self, sWord):
        "returns stems list of sWord"
        iAddr = 0
        for c in sWord:
            if c not in self.dChar:
                return []
            iAddr = self._lookupArcNode(self.dChar[c], iAddr)
            if iAddr == None:
                return []
        if (int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big') & self._finalNodeMask):
            l = []
            nRawArc = 0
            while not (nRawArc & self._lastArcMask):
                iEndArcAddr = iAddr + self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                if nArc >= self.nChar:
                    # This value is not a char, this is a stemming code 
                    l.append(self.funcStemming(sWord, self.lArcVal[nArc]))
                iAddr = iEndArcAddr+self.nBytesNodeAddress
            return l
        return []

    def _lookupArcNode1 (self, nVal, iAddr):
        "looks if nVal is an arc at the node at iAddr, if yes, returns address of next node else None"
        while True:
            iEndArcAddr = iAddr+self.nBytesArc
            nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
            if nVal == (nRawArc & self._arcMask):
                # the value we are looking for 
                # we return the address of the next node
                return int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
            else:
                # value not found
                if (nRawArc & self._lastArcMask):
                    return None
                iAddr = iEndArcAddr+self.nBytesNodeAddress

    def _writeNodes1 (self, spfDest):
        "for debugging only"
        print(" > Write binary nodes")
        with codecs.open(spfDest, 'w', 'utf-8') as hDst:
            iAddr = 0
            hDst.write("i{:_>10} -- #{:_>10}\n".format("0", iAddr))
            while iAddr < len(self.byDic):
                iEndArcAddr = iAddr+self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                hDst.write("  {:<20}  {:0>16}  i{:>10}   #{:_>10}\n".format(self.lArcVal[nArc], bin(nRawArc)[2:], "?", \
                                                                            int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], \
                                                                                           byteorder='big')))
                iAddr = iEndArcAddr+self.nBytesNodeAddress
                if (nRawArc & self._lastArcMask) and iAddr < len(self.byDic):
                    hDst.write("\ni{:_>10} -- #{:_>10}\n".format("?", iAddr))
            hDst.close()

    # VERSION 2
    def _morph2 (self, sWord):
        "returns morphologies of sWord"
        iAddr = 0
        for c in sWord:
            if c not in self.dChar:
                return []
            iAddr = self._lookupArcNode(self.dChar[c], iAddr)
            if iAddr == None:
                return []
        if (int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big') & self._finalNodeMask):
            l = []
            nRawArc = 0
            while not (nRawArc & self._lastArcMask):
                iEndArcAddr = iAddr + self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                if nArc >= self.nChar:
                    # This value is not a char, this is a stemming code 
                    sStem = ">" + self.funcStemming(sWord, self.lArcVal[nArc])
                    # Now , we go to the next node and retrieve all following arcs values, all of them are tags
                    if not (nRawArc & self._addrBitMask):
                        iAddr2 = int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
                    else:
                        # we go to the end of the node
                        iAddr2 = iEndArcAddr
                        while not (nRawArc & self._lastArcMask):
                            nRawArc = int.from_bytes(self.byDic[iAddr2:iAddr2+self.nBytesArc], byteorder='big')
                            iAddr2 += self.nBytesArc + self.nBytesNodeAddress
                    nRawArc2 = 0
                    while not (nRawArc2 & self._lastArcMask):
                        iEndArcAddr2 = iAddr2 + self.nBytesArc
                        nRawArc2 = int.from_bytes(self.byDic[iAddr2:iEndArcAddr2], byteorder='big')
                        l.append(sStem + " " + self.lArcVal[nRawArc2 & self._arcMask])
                        iAddr2 = iEndArcAddr2+self.nBytesNodeAddress  if not (nRawArc2 & self._addrBitMask) else iEndArcAddr2
                iAddr = iEndArcAddr+self.nBytesNodeAddress  if not (nRawArc & self._addrBitMask)  else iEndArcAddr
            return l
        return []

    def _stem2 (self, sWord):
        "returns stems list of sWord"
        iAddr = 0
        for c in sWord:
            if c not in self.dChar:
                return []
            iAddr = self._lookupArcNode(self.dChar[c], iAddr)
            if iAddr == None:
                return []
        if (int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big') & self._finalNodeMask):
            l = []
            nRawArc = 0
            while not (nRawArc & self._lastArcMask):
                iEndArcAddr = iAddr + self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                if nArc >= self.nChar:
                    # This value is not a char, this is a stemming code 
                    l.append(self.funcStemming(sWord, self.lArcVal[nArc]))
                    # Now , we go to the next node
                    if not (nRawArc & self._addrBitMask):
                        iAddr2 = int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
                    else:
                        # we go to the end of the node
                        iAddr2 = iEndArcAddr
                        while not (nRawArc & self._lastArcMask):
                            nRawArc = int.from_bytes(self.byDic[iAddr2:iAddr2+self.nBytesArc], byteorder='big')
                            iAddr2 += self.nBytesArc + self.nBytesNodeAddress
                iAddr = iEndArcAddr+self.nBytesNodeAddress  if not (nRawArc & self._addrBitMask)  else iEndArcAddr
            return l
        return []

    def _lookupArcNode2 (self, nVal, iAddr):
        "looks if nVal is an arc at the node at iAddr, if yes, returns address of next node else None"
        while True:
            iEndArcAddr = iAddr+self.nBytesArc
            nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
            if nVal == (nRawArc & self._arcMask):
                # the value we are looking for 
                if not (nRawArc & self._addrBitMask):
                    # we return the address of the next node
                    return int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
                else:
                    # we go to the end of the node
                    iAddr = iEndArcAddr
                    while not (nRawArc & self._lastArcMask):
                        nRawArc = int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big')
                        iAddr += self.nBytesArc + self.nBytesNodeAddress  if not (nRawArc & self._addrBitMask)  else self.nBytesArc
                    return iAddr
            else:
                # value not found
                if (nRawArc & self._lastArcMask):
                    return None
                iAddr = iEndArcAddr+self.nBytesNodeAddress  if not (nRawArc & self._addrBitMask)  else iEndArcAddr

    def _writeNodes2 (self, spfDest):
        "for debugging only"
        print(" > Write binary nodes")
        with codecs.open(spfDest, 'w', 'utf-8') as hDst:
            iAddr = 0
            hDst.write("i{:_>10} -- #{:_>10}\n".format("0", iAddr))
            while iAddr < len(self.byDic):
                iEndArcAddr = iAddr+self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                if not (nRawArc & self._addrBitMask):
                    iNextNodeAddr = int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
                    hDst.write("  {:<20}  {:0>16}  i{:>10}   #{:_>10}\n".format(self.lArcVal[nArc], bin(nRawArc)[2:], "?", iNextNodeAddr))
                    iAddr = iEndArcAddr+self.nBytesNodeAddress
                else:
                    hDst.write("  {:<20}  {:0>16}\n".format(self.lArcVal[nArc], bin(nRawArc)[2:]))
                    iAddr = iEndArcAddr
                if (nRawArc & self._lastArcMask):
                    hDst.write("\ni{:_>10} -- #{:_>10}\n".format("?", iAddr))
            hDst.close()

    # VERSION 3
    def _morph3 (self, sWord):
        "returns morphologies of sWord"
        iAddr = 0
        for c in sWord:
            if c not in self.dChar:
                return []
            iAddr = self._lookupArcNode(self.dChar[c], iAddr)
            if iAddr == None:
                return []
        if (int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big') & self._finalNodeMask):
            l = []
            nRawArc = 0
            iAddrNode = iAddr
            while not (nRawArc & self._lastArcMask):
                iEndArcAddr = iAddr + self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                if nArc >= self.nChar:
                    # This value is not a char, this is a stemming code 
                    sStem = ">" + self.funcStemming(sWord, self.lArcVal[nArc])
                    # Now , we go to the next node and retrieve all following arcs values, all of them are tags
                    if not (nRawArc & self._addrBitMask):
                        iAddr2 = int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
                    else:
                        iAddr2 = iAddrNode + int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesOffset], byteorder='big')
                    nRawArc2 = 0
                    while not (nRawArc2 & self._lastArcMask):
                        iEndArcAddr2 = iAddr2 + self.nBytesArc
                        nRawArc2 = int.from_bytes(self.byDic[iAddr2:iEndArcAddr2], byteorder='big')
                        l.append(sStem + " " + self.lArcVal[nRawArc2 & self._arcMask])
                        iAddr2 = iEndArcAddr2+self.nBytesNodeAddress  if not (nRawArc2 & self._addrBitMask) else iEndArcAddr2+self.nBytesOffset
                iAddr = iEndArcAddr+self.nBytesNodeAddress  if not (nRawArc & self._addrBitMask)  else iEndArcAddr+self.nBytesOffset
            return l
        return []

    def _stem3 (self, sWord):
        "returns stems list of sWord"
        iAddr = 0
        for c in sWord:
            if c not in self.dChar:
                return []
            iAddr = self._lookupArcNode(self.dChar[c], iAddr)
            if iAddr == None:
                return []
        if (int.from_bytes(self.byDic[iAddr:iAddr+self.nBytesArc], byteorder='big') & self._finalNodeMask):
            l = []
            nRawArc = 0
            iAddrNode = iAddr
            while not (nRawArc & self._lastArcMask):
                iEndArcAddr = iAddr + self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                if nArc >= self.nChar:
                    # This value is not a char, this is a stemming code 
                    l.append(self.funcStemming(sWord, self.lArcVal[nArc]))
                iAddr = iEndArcAddr+self.nBytesNodeAddress  if not (nRawArc & self._addrBitMask)  else iEndArcAddr+self.nBytesOffset
            return l
        return []

    def _lookupArcNode3 (self, nVal, iAddr):
        "looks if nVal is an arc at the node at iAddr, if yes, returns address of next node else None"
        iAddrNode = iAddr
        while True:
            iEndArcAddr = iAddr+self.nBytesArc
            nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
            if nVal == (nRawArc & self._arcMask):
                # the value we are looking for 
                if not (nRawArc & self._addrBitMask):
                    return int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
                else:
                    return iAddrNode + int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesOffset], byteorder='big')
            else:
                # value not found
                if (nRawArc & self._lastArcMask):
                    return None
                iAddr = iEndArcAddr+self.nBytesNodeAddress  if not (nRawArc & self._addrBitMask)  else iEndArcAddr+self.nBytesOffset

    def _writeNodes3 (self, spfDest):
        "for debugging only"
        print(" > Write binary nodes")
        with codecs.open(spfDest, 'w', 'utf-8') as hDst:
            iAddr = 0
            hDst.write("i{:_>10} -- #{:_>10}\n".format("0", iAddr))
            while iAddr < len(self.byDic):
                iEndArcAddr = iAddr+self.nBytesArc
                nRawArc = int.from_bytes(self.byDic[iAddr:iEndArcAddr], byteorder='big')
                nArc = nRawArc & self._arcMask
                if not (nRawArc & self._addrBitMask):
                    iNextNodeAddr = int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesNodeAddress], byteorder='big')
                    hDst.write("  {:<20}  {:0>16}  i{:>10}   #{:_>10}\n".format(self.lArcVal[nArc], bin(nRawArc)[2:], "?", iNextNodeAddr))
                    iAddr = iEndArcAddr+self.nBytesNodeAddress
                else:
                    iNextNodeAddr = int.from_bytes(self.byDic[iEndArcAddr:iEndArcAddr+self.nBytesOffset], byteorder='big')
                    hDst.write("  {:<20}  {:0>16}  i{:>10}   +{:_>10}\n".format(self.lArcVal[nArc], bin(nRawArc)[2:], "?", iNextNodeAddr))
                    iAddr = iEndArcAddr+self.nBytesOffset
                if (nRawArc & self._lastArcMask):
                    hDst.write("\ni{:_>10} -- #{:_>10}\n".format("?", iAddr))
            hDst.close()
