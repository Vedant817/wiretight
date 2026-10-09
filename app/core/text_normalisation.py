"""Invisible and homoglyph characters, handled once, for every identifier path.

FINAL.md §4.3 makes ``(vendor_id, normalised invoice no.)`` *the* duplicate
detection strategy, and makes a changed bank fingerprint *the* trigger for the
bank-change lock. Both are decided by a string comparison, so a character that
renders as nothing but compares as something is a hole in the product's central
claim.

Measured on this codebase before the fix (D-B20):

* ``"INV-2291"`` and ``"INV-2291\\u200b"`` (ZWSP) produced two different
  ``duplicate_lock.obligation_key`` values, so the same invoice paid twice;
* a soft hyphen, BOM, word joiner, ZWJ, and the bidi controls all split the bank
  fingerprint of an account that had not changed at all, producing a
  ``HOLD: BANK_CHANGE`` and a 72 h cooling-off on an unchanged supplier;
* the same characters reversed what a human sees in the queue, because
  ``U+202E`` reorders the remainder of the line on screen.

None of these are exotic. A zero-width space is what several mainstream PDF
exporters and copy-paste pipelines insert into long strings.

The rule here is deliberately narrow: **strip characters that carry no visible
glyph and exist to influence machine behaviour.** That is Unicode general
category ``Cf`` (format), zero-width, invisible operators and marks, plus
combining marks that attach to the preceding letter. It is *not* a homoglyph
fold: the Cyrillic letter U+0430 that looks like Latin "a" is a real letter in a
real name and transliterating it would merge two genuinely different suppliers.
Homoglyph detection belongs in vendor matching, where it can be reported, not in
normalisation, where it would be silent.
"""

from __future__ import annotations

import unicodedata

__all__ = [
    "FORMAT_CATEGORIES",
    "describe_invisible",
    "has_invisible",
    "strip_invisible",
    "to_ascii_key",
]

#: General categories that render as nothing but change the bytes.
#:
#: ``Cf`` format (ZWSP, ZWNJ/ZWJ, BOM, soft hyphen, word joiner, bidi controls),
#: ``Cc`` control (NUL, BEL, the C1 range), ``Zl``/``Zp`` line/paragraph
#: separators, and ``Mn``/``Mc`` combining marks, which attach to the preceding
#: character and therefore cannot change its identity.
FORMAT_CATEGORIES: frozenset[str] = frozenset({"Cf", "Cc", "Zl", "Zp", "Mn", "Mc"})

#: The bidi controls specifically, named because they are the ones that change
#: what a human *sees* rather than only what a machine compares. Written as
#: escapes: the literal characters are invisible in a diff and two of them are
#: indistinguishable when read, which is how a duplicate crept in once.
BIDI_CONTROLS: frozenset[str] = frozenset(
    {
        "‪",  # LRE  U+202A
        "‫",  # RLE  U+202B
        "‬",  # PDF  U+202C
        "‭",  # LRO  U+202D
        "‮",  # RLO  U+202E
        "⁦",  # LRI  U+2066
        "⁧",  # RLI  U+2067
        "⁨",  # FSI  U+2068
        "⁩",  # PDI  U+2069
        "‎",  # LRM  U+200E
        "‏",  # RLM  U+200F
        "؜",  # ALM  U+061C
    }
)

#: Confusables that are not invisible but are commonly substituted. Reported, not
#: stripped: folding these silently would merge two different suppliers. Cyrillic
#: "a" (U+0430) and Latin "a" (U+0061), fullwidth forms, and Cherokee-Latin
#: pairs are intentionally NOT folded here. Use ``app.core.vendors`` for that,
#: where a near-miss can be reported to a human instead of silently merged.


def is_invisible(char: str) -> bool:
    """Does ``char`` render as nothing, or only attach to its neighbour?"""
    return unicodedata.category(char) in FORMAT_CATEGORIES


def has_invisible(value: str) -> bool:
    """True if ``value`` carries any invisible or combining character.

    Used to *report* rather than to strip: a bill that arrives with a zero-width
    space is worth flagging, because nothing legitimate adds one.
    """
    return any(is_invisible(char) for char in value)


def strip_invisible(value: str) -> str:
    """Remove format, control and combining characters, then NFKC-normalise.

    NFKC comes first so that compatibility forms (fullwidth digits, ligatures)
    collapse to their canonical form, then the invisible characters are dropped,
    then NFKC again because dropping a combining mark can expose a new
    compatibility pair.
    """
    folded = unicodedata.normalize("NFKC", value)
    without = "".join(char for char in folded if not is_invisible(char))
    return unicodedata.normalize("NFKC", without)


def to_ascii_key(value: str) -> str:
    """A comparison key that folds case and invisible characters.

    This is the key used for **identity** questions: "is this the same invoice
    number?". It is deliberately lossy and is never stored or displayed.
    """
    return strip_invisible(value).strip().upper()


def describe_invisible(value: str) -> list[str]:
    """Name every invisible character in ``value``, for an audit entry.

    A count is not enough: an operator looking at "this bill had 1 hidden
    character" learns nothing, while "U+202E RIGHT-TO-LEFT OVERRIDE" tells them
    the text was arranged to be read backwards.
    """
    found: list[str] = []
    for char in value:
        if not is_invisible(char):
            continue
        try:
            name = unicodedata.name(char)
        except ValueError:  # pragma: no cover - unnamed control
            name = "unnamed"
        label = f"U+{ord(char):04X} {name}"
        if label not in found:
            found.append(label)
    return found


def bidi_present(value: str) -> bool:
    """True if any bidi control is present.

    Separate from :func:`has_invisible` because a bidi override is not a typo, it
    is an attempt to make one string display as another.
    """
    return any(char in BIDI_CONTROLS for char in value)
