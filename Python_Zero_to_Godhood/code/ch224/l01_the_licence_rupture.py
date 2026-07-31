"""Listing 224.1 - the licence rupture (2000-2001): CNRI, BeOpen, and the PSF.

Between Python 1.5.2 and 2.1, Python's LICENCE and OWNERSHIP were in turmoil.
Guido moved from CWI to CNRI (1995), which released 1.6 under a licence whose
choice-of-law clause was GPL-INCOMPATIBLE. He then moved to BeOpen (2.0 under
yet another licence), then Digital Creations. The Python Software Foundation
(PSF) was formed in 2001 to OWN Python and its licence permanently, and the
PSF License (GPL-compatible, permissive) has governed every release since.
This is why the volume is called 'The Licence Rupture': a language's legal
foundation nearly fractured. The modern consequence - the PSF licence and a
foundation that owns the language - ships in the interpreter. Verified today.
"""

import sys


def main() -> None:
    print("--- the licence ships in the interpreter (sys.copyright) ---")
    text = sys.copyright
    print("  sys.copyright names the stewards (years elided, they drift):")
    for entity in ("Python Software Foundation", "BeOpen.com",
                   "Corporation for National Research Initiatives",
                   "Stichting Mathematisch Centrum"):
        print(f"    present : {entity in text}  {entity}")
    print("  the copyright chain IS the history: PSF, then BeOpen, then CNRI,")
    print("  then CWI (Stichting Mathematisch Centrum) - each entity that")
    print("  stewarded Python, in reverse order")

    print("--- the rupture, as the copyright chain records it ---")
    stewards = [
        ("CWI (Amsterdam)", "1991-1995", "Guido's original institution"),
        ("CNRI (USA)", "1995-2000", "1.6 licence was GPL-INCOMPATIBLE"),
        ("BeOpen.com", "2000", "2.0 under the BeOpen license"),
        ("PSF", "2001-now", "formed to OWN Python permanently"),
    ]
    for name, era, note in stewards:
        print(f"  {name:<16} {era:<10} {note}")
    print("  four owners in a decade - the instability the PSF was created to")
    print("  end. a language whose licence keeps changing cannot be trusted")
    print("  by the enterprises and distros that must ship it")

    print("--- why the licence mattered: GPL compatibility ---")
    print("  the CNRI 1.6 licence had a Virginia choice-of-law clause that")
    print("  made it INCOMPATIBLE with the GPL - meaning GPL software could")
    print("  not legally include Python. for a language whose whole value is")
    print("  being embedded and combined (Chapter 1: extensibility), a licence")
    print("  that forbade combination with the era's dominant free licence was")
    print("  an existential problem, not a legal footnote")

    print("--- the resolution: a foundation that owns the language ---")
    print(f"  today Python is owned by the PSF, a non-profit, under a")
    print(f"  permissive GPL-compatible licence (the PSFL). the license and")
    print(f"  governance are STABLE - which is exactly what a language needs")
    print(f"  to be adopted by everyone from hobbyists to banks to distros.")
    print("  the rupture taught that a language's LEGAL foundation is")
    print("  infrastructure, as load-bearing as its object model")

    print("--- the constraint answered ---")
    print("  2000-2001 faced a crisis the language's early informality created:")
    print("  no clear owner, a licence that changed with each employer, one")
    print("  version GPL-incompatible. the PSF answered it by giving Python a")
    print("  permanent, neutral owner and a stable licence - governance as a")
    print("  prerequisite for the ecosystem everything after 2.1 was built on")


if __name__ == "__main__":
    main()
