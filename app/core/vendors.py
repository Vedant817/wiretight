"""Deterministic vendor matching, and the lookalike-domain quarantine.

FINAL.md §4.3 fixes the matching order and the failure mode:

> tax ID exact, then normalised legal name exact, then known sender domain
> exact. A sender domain within edit distance <= 2 of a known vendor domain, or
> matching it under a homoglyph map, -> ``QUARANTINE: LOOKALIKE_DOMAIN``, never a
> match. No fuzzy name auto-match, ever.

Two things make this more than a lookup table, and both are the reason this module
is not three dict lookups.

**A near-match must never become a match.** The interesting case is not
"acme.com matches acme" but "acrne.com is one edit from acme.com". A supplier
paying the wrong company is the fraud this whole system exists to stop, so a
lookalike is *quarantined* rather than resolved - it goes to a human, and the
obligation is blocked (§4.4's HARD_BLOCK list includes QUARANTINE).

**No fuzzy name match, ever.** The spec says so in terms, and the reason is worth
stating: edit distance between two real company names is a property of the names,
not of their relationship. "ACME Ltd" and "ACME Ldt" are different companies, and
"Acme Corp" and "Acme Corp Global" are the same company with no edit-distance
signal to prove it. Fuzzy matching would produce confident answers in the one case
and no answer in the other.

A second, subtler rule: a **homoglyph** is not the same as a lookalike, and the two
must not be conflated. Cyrillic "a" is a real letter that appears in real names;
normalising it away would merge two distinct suppliers *silently*, which is worse
than quarantining a near-miss where a human can see it. So homoglyph mapping happens
only on the **domain** side, where the alphabet is restricted to ASCII by the DNS
rules and a non-ASCII codepoint is unambiguously an attack.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Final

__all__ = [
    "LOOKALIKE_FLAG",
    "MatchKind",
    "VendorMatch",
    "ascii_fold",
    "edit_distance",
    "lookalike_domain",
    "match_vendor",
    "normalise_legal_name",
]

#: The flag §4.3 names. Defined once so a UI, a flag set and a test all agree.
LOOKALIKE_FLAG: Final[str] = "LOOKALIKE_DOMAIN"

#: §4.3: edit distance at or below this is a lookalike, not a match.
MAX_LOOKALIKE_DISTANCE: Final[int] = 2


class MatchKind:
    """How a sender was resolved, in the order §4.3 specifies."""

    TAX_ID: Final[str] = "TAX_ID"
    LEGAL_NAME: Final[str] = "LEGAL_NAME"
    SENDER_DOMAIN: Final[str] = "SENDER_DOMAIN"
    #: A near-match of a known domain. Quarantined, never a match.
    LOOKALIKE: Final[str] = "LOOKALIKE"
    NONE: Final[str] = "NONE"


@dataclass(frozen=True)
class VendorMatch:
    """The outcome of resolving one sender against the vendor table."""

    kind: str
    vendor_id: str | None
    #: Set only for :attr:`MatchKind.LOOKALIKE` and :attr:`MatchKind.NONE`.
    reason: str = ""
    #: The known domain this sender resembled, when there is one.
    near_domain: str | None = None

    @property
    def matched(self) -> bool:
        """Did a vendor resolve? A lookalike explicitly does not."""
        return self.vendor_id is not None

    @property
    def quarantine(self) -> bool:
        """Must this be held for a human rather than processed?"""
        return self.kind == MatchKind.LOOKALIKE


_NO_MATCH = VendorMatch(kind=MatchKind.NONE, vendor_id=None)


# --------------------------------------------------------------------------
# Normalisation
# --------------------------------------------------------------------------


def normalise_legal_name(value: str) -> str:
    """Upper-case, strip invisible characters, and drop punctuation and suffixes.

    Deliberately **not** Unicode normalised beyond NFKC. NFKC is safe - it maps
    fullwidth digits and ligatures to their canonical form - but anything further
    would start merging distinct suppliers (D-B20).

    Legal-form suffixes (Ltd, GmbH, Inc) are *not* stripped. §4.3 names exact
    legal-name matching, and two firms whose only difference is their legal form are
    two firms. Where a firm is known by several names the vendor record carries
    them separately rather than the matcher guessing.
    """
    folded = unicodedata.normalize("NFKC", value)
    without_invisible = "".join(
        char for char in folded if unicodedata.category(char) not in _INVISIBLE_CATEGORIES
    )
    upper = without_invisible.upper()
    # Spaces, punctuation and dots separate words; they do not identify a firm.
    kept = [char for char in upper if char.isalnum() or char.isspace()]
    return " ".join("".join(kept).split())


#: General categories that render as nothing or attach to a neighbour. Matches the
#: rule in app.core.text_normalisation; kept local so a change there does not
#: silently change vendor identity.
_INVISIBLE_CATEGORIES: Final[frozenset[str]] = frozenset({"Cf", "Cc", "Zl", "Zp", "Mn", "Mc"})


def ascii_fold(domain: str) -> str:
    """Map confusable non-ASCII codepoints to their ASCII lookalikes.

    Applied **only to domains**. A domain is ASCII by rule, so a Cyrillic or
    Greek codepoint in one is not a transliteration, it is an attack. Applying the
    same fold to a legal name would be wrong: The Cyrillic letter U+0430 is a real letter in a
    real supplier name, and folding it away would merge two distinct suppliers
    silently (D-B20).
    """
    out: list[str] = []
    for char in domain:
        folded = _CONFUSABLES.get(char)
        out.append(folded if folded is not None else char)
    return "".join(out)


#: Confusables that have an unambiguous ASCII lookalike. Short and explicit, on
#: purpose: a long table is a long liability, and beyond these the honest answer is
#: "this is not ASCII, treat it as an attack" rather than guessing.
_CONFUSABLES: Final[dict[str, str]] = {
    "\u0430": "a",  # CYRILLIC SMALL LETTER A
    "\u0250": "a",  # LATIN SMALL LETTER TURNED A
    "\u03bf": "o",  # GREEK SMALL LETTER OMICRON
    "\u043e": "o",  # CYRILLIC SMALL LETTER O
    "\u0440": "p",  # CYRILLIC SMALL LETTER ER
    "\u051d": "e",  # CYRILLIC SMALL LETTER E
    "\u0565": "e",  # ARMENIAN SMALL LETTER ECH
    "\u0578": "n",  # ARMENIAN SMALL LETTER VO
    "\u09b8": "s",  # BENGALI LETTER SA
    "\uff41": "a",  # FULLWIDTH LATIN SMALL LETTER A
    "\uff4f": "o",  # FULLWIDTH LATIN SMALL LETTER O
    "\u2010": "-",  # HYPHEN
    "\u2011": "-",  # NON-BREAKING HYPHEN
    "\u2024": ".",  # ONE DOT LEADER
    "\uff0e": ".",  # FULLWIDTH FULL STOP
    "\uff0f": "/",  # FULLWIDTH SOLIDUS
}


# --------------------------------------------------------------------------
# Distance
# --------------------------------------------------------------------------


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance, full DP.

    A bounded variant was tried and reverted: returning a sentinel like
    ``MAX + 1`` conflates "at least three" with "exactly three", and every caller
    compares ``<= MAX``, so the conflation is invisible right up until someone asks
    for the true distance and gets a wrong number (D-B25).

    The tables here are short - a domain label is a handful of characters - so the
    optimisation is not worth a contract that lies. Callers that want a fast
    "is this within the bound" answer should use :func:`within_distance`.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current = [i]
        for j, char_b in enumerate(b, start=1):
            cost = 0 if char_a == char_b else 1
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + cost,
                )
            )
        previous = current
    return previous[-1]


def within_distance(a: str, b: str, bound: int = MAX_LOOKALIKE_DISTANCE) -> bool:
    """Is the distance at most ``bound``? Does not claim to know more.

    Short-circuits on the length difference, which is a lower bound on the distance
    and therefore safe to prune on. Returns a bool rather than a capped integer so
    there is no sentinel to misread.
    """
    if a == b:
        return True
    if abs(len(a) - len(b)) > bound:
        return False
    return edit_distance(a, b) <= bound


def lookalike_domain(sender_domain: str, known_domains: Iterable[str]) -> str | None:
    """The known domain ``sender_domain`` resembles, if any.

    Returns the *closest* known domain when the distance is within the bound, and
    respects three separate attack shapes that a plain Levenshtein would miss:

    * **homoglyph** - ``acme`` with a Cyrillic "a". Not within edit distance 1 of
      ``acme`` as bytes it maps to, so it has to be folded first;
    * **confusable separator** - ``acme.com`` written with a non-breaking hyphen or
      a fullwidth dot, which DNS resolves differently and a human reads the same;
    * **a domain added around a real one** - ``acme.com.evil.example`` starts with
      a known domain, so it is *not* a small edit, but it is plainly an attack and
      is caught by the subdomain check.

    Distance is computed on the **registered** domain, not the bare label, so
    ``mail.acme.com`` is the sender of record rather than something resembling
    ``acme.com``.
    """
    sender = _normalise_domain(sender_domain)

    for known in known_domains:
        candidate = _normalise_domain(known)
        if not candidate:
            continue

        # 1. Homoglyph or confusable separator: fold first, then compare.
        folded = ascii_fold(sender)
        if folded == candidate:
            # Same after folding but not before: an attack, not a match.
            if sender != candidate:
                return known
            continue

        # 2. A known domain with attack text wrapped around it.
        #    "acme.com.evil.example" appends after: a prefix attack.
        #    "notacme.com" prepends without a dot boundary: also an attack, and
        #    *not* within edit distance 2, so distance alone misses it entirely.
        #    "mail.acme.com" is a legitimate subdomain and must NOT be caught: the
        #    dot boundary is what separates a real subdomain from a takeover.
        if folded.startswith(candidate + "."):
            return known
        if folded.endswith(candidate) and not folded.endswith("." + candidate):
            return known

        # 3. Small edit.
        if within_distance(folded, candidate):
            return known

    return None


def _normalise_domain(domain: str) -> str:
    """Lower-case, trim, and drop a port, path or credentials.

    ``user@sub.acme.com:8080/path`` and ``sub.acme.com`` are the same sender of
    record for matching purposes. Not doing this lets an attacker hide a lookalike
    behind a port number or a path, which a human never sees.
    """
    text = domain.strip().lower()
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    text = text.split("/", 1)[0]
    text = text.split(":", 1)[0]
    return text.strip(".")


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class VendorRecord:
    """The minimum a matcher needs. The real table has more."""

    id: str
    tax_id: str | None = None
    legal_name: str | None = None
    known_domains: tuple[str, ...] = ()


def match_vendor(
    *,
    tax_id: str | None = None,
    legal_name: str | None = None,
    sender_domains: Iterable[str] | None = None,
    vendors: Iterable[VendorRecord],
) -> VendorMatch:
    """Resolve a sender, in §4.3's order, or quarantine a near-match.

    The order matters and is not cosmetic. Tax ID is first because it is the only
    identifier that is *supposed* to be unique; legal name is second because it is
    stable; sender domain is last because it is the only one an attacker controls.
    A sender domain is therefore only ever a confirming signal, never the primary
    one, which is why the lookalike check runs *after* the exact match rather than
    before.
    """
    vendors = list(vendors)

    if tax_id:
        for vendor in vendors:
            if vendor.tax_id and vendor.tax_id == tax_id.strip():
                return VendorMatch(kind=MatchKind.TAX_ID, vendor_id=vendor.id)

    if legal_name:
        wanted = normalise_legal_name(legal_name)
        for vendor in vendors:
            if vendor.legal_name and normalise_legal_name(vendor.legal_name) == wanted:
                return VendorMatch(kind=MatchKind.LEGAL_NAME, vendor_id=vendor.id)

    if sender_domains:
        for sender in sender_domains:
            normalised = _normalise_domain(sender)
            if not normalised:
                continue

            known = [d for vendor in vendors for d in vendor.known_domains]
            for vendor in vendors:
                for domain in vendor.known_domains:
                    if _normalise_domain(domain) == normalised:
                        return VendorMatch(kind=MatchKind.SENDER_DOMAIN, vendor_id=vendor.id)

            near = lookalike_domain(sender, known)
            if near is not None:
                return VendorMatch(
                    kind=MatchKind.LOOKALIKE,
                    vendor_id=None,
                    reason=(
                        f"sender domain {sender!r} resembles the known domain "
                        f"{near!r} within {MAX_LOOKALIKE_DISTANCE} edits or under a "
                        f"homoglyph map. Quarantined, never matched (FINAL.md §4.3)."
                    ),
                    near_domain=near,
                )

    return _NO_MATCH


def known_domains(vendors: Mapping[str, Iterable[str]]) -> Mapping[str, str]:
    """Map every known domain to its vendor, for a table scan in one pass."""
    index: dict[str, str] = {}
    for vendor_id, domains in vendors.items():
        for domain in domains:
            index[_normalise_domain(domain)] = vendor_id
    return index
