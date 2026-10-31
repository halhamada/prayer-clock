"""Arabic for a plain text renderer: joins letters into presentation forms and puts them in visual order.

SDL_ttf draws one glyph after another, so the joining and right-to-left order happen here. A small table instead
of arabic-reshaper + python-bidi keeps the device free of pip packages."""

import re

# Letters in the order of the Arabic Presentation Forms-B block, with how many forms each has there.
_LETTERS = (("ء", 1), ("آ", 2), ("أ", 2), ("ؤ", 2), ("إ", 2), ("ئ", 4), ("ا", 2), ("ب", 4), ("ة", 2), ("ت", 4),
            ("ث", 4), ("ج", 4), ("ح", 4), ("خ", 4), ("د", 2), ("ذ", 2), ("ر", 2), ("ز", 2), ("س", 4), ("ش", 4),
            ("ص", 4), ("ض", 4), ("ط", 4), ("ظ", 4), ("ع", 4), ("غ", 4), ("ف", 4), ("ق", 4), ("ك", 4), ("ل", 4),
            ("م", 4), ("ن", 4), ("ه", 4), ("و", 2), ("ى", 2), ("ي", 4))

_FORMS = {}
_code = 0xFE80
for _letter, _count in _LETTERS:
    _FORMS[_letter] = tuple(chr(_code + i) for i in range(_count))   # isolated, final, initial, medial
    _code += _count

_LAM_ALEF = {"آ": "ﻵ", "أ": "ﻷ", "إ": "ﻹ", "ا": "ﻻ"}   # isolated; final is the next code
_DIACRITICS = re.compile("[ً-ْٰـ]")
_LTR = re.compile(r"[0-9A-Za-z][0-9A-Za-z:./\- ]*[0-9A-Za-z]|[0-9A-Za-z]")


def _joins_next(ch):
    return len(_FORMS.get(ch, ())) == 4


def _joins_prev(ch):
    return len(_FORMS.get(ch, ())) >= 2


def shape(text):
    """text with its Arabic letters replaced by their joined forms, still in logical order."""
    text = _DIACRITICS.sub("", text)
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch not in _FORMS:
            out.append(ch)
            i += 1
            continue
        joined = i > 0 and _joins_next(text[i - 1]) and _joins_prev(ch)
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if ch == "ل" and nxt in _LAM_ALEF:
            out.append(chr(ord(_LAM_ALEF[nxt]) + (1 if joined else 0)))
            i += 2
            continue
        joins = _joins_next(ch) and _joins_prev(nxt)
        forms = _FORMS[ch]
        if joined and joins:
            out.append(forms[3])
        elif joined:
            out.append(forms[1])
        elif joins:
            out.append(forms[2])
        else:
            out.append(forms[0])
        i += 1
    return "".join(out)


def visual(text):
    """text, shaped, in left-to-right drawing order for a right-to-left line. Numbers and Latin stay readable."""
    shaped = shape(text)
    if not re.search("[\uFB50-\uFEFF]", shaped):
        return shaped
    pieces = []
    pos = 0
    for m in _LTR.finditer(shaped):
        pieces.append(_mirror(shaped[pos:m.start()])[::-1])
        pieces.append(m.group())
        pos = m.end()
    pieces.append(_mirror(shaped[pos:])[::-1])
    return "".join(reversed(pieces))


def _mirror(s):
    return s.translate({ord("("): ")", ord(")"): "("})
