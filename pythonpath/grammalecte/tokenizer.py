# Very simple tokenizer

import re
from collections import namedtuple


Token = namedtuple('Token', ['type', 'value', 'start', 'end'])


_PATTERNS = {
    "default":
        (
            r'(?P<HTML><\w+.*?>|</\w+ *>)',
            r'(?P<PSEUDOHTML>\[/?\w+\])',
            r'(?P<NUM>\d+(?:[.,]\d+))',
            r"(?P<WORD>\w+(?:[’'`-]\w+(?:[’'`-]\w+|)|))"
        ),
    "fr":
        (
            r'(?P<HTML><\w+.*?>|</\w+ *>)',
            r'(?P<PSEUDOHTML>\[/?\w+\])',
            r"(?P<ELPFX>(?:l|d|n|m|t|s|j|c|ç|lorsqu|puisqu|jusqu|quoiqu|qu)['’`])",
            r'(?P<NUM>\d+(?:[.,]\d+|))',
            r"(?P<WORD>\w+(?:[’'`-]\w+(?:[’'`-]\w+|)|))"
        )
}


class Tokenizer:

    def __init__ (self, sLang):
        self.sLang = sLang
        if sLang not in _PATTERNS:
            sLang = "default"
        self.zToken = re.compile( "(?i)" + '|'.join(sRegex for sRegex in _PATTERNS[sLang]) )

    def genTokens (self, sText):
        for m in self.zToken.finditer(sText):
            yield Token(m.lastgroup, m.group(), m.start(), m.end())
