"""Listing 223.1 - Python 2.0 (2000): the unicode type arrives, and starts a journey.

Python 2.0 added a separate `unicode` type alongside `str` (which was bytes).
This was the first move in a decade-long journey to fix ABC's first flaw
(Chapter 1: no proper text handling) at the deepest level: the confusion
between BYTES (what a file or socket carries) and TEXT (a sequence of
characters). Python 2's two-type-but-implicitly-converting model was a
half-fix that caused the infamous UnicodeDecodeError; Python 3.0 completed
the fix by making str=text and bytes=bytes with NO implicit conversion. This
listing shows the modern, CORRECT model (Python 3's) that 2.0 began reaching
for - Deep D owns the mechanism; this is the release that started it.
"""


def main() -> None:
    print("--- the modern model: str is TEXT, bytes is BYTES, and they differ ---")
    text = "caf" + chr(0x00E9)  # cafe + precomposed e-acute
    data = text.encode("utf-8")
    print(f"  str (text)  : {text!r} - {len(text)} code points")
    print(f"  bytes (data): {data!r} - {len(data)} bytes")
    print(f"  they are different types : {type(text) is not type(data)}")
    print("  a string is a sequence of CHARACTERS (code points); bytes is a")
    print("  sequence of OCTETS. one character can be several bytes (utf-8),")
    print("  which is exactly the distinction 2.0's unicode type introduced")

    print("--- encode/decode is the ONLY bridge, and it is explicit ---")
    print(f"  text.encode('utf-8')  : {text.encode('utf-8')!r}  (text -> bytes)")
    print(f"  data.decode('utf-8')  : {data.decode('utf-8')!r}  (bytes -> text)")
    print(f"  round trip is exact   : {data.decode('utf-8') == text}")
    print("  the encoding is NAMED at every crossing - Python 3's rule. 2.0")
    print("  had the two types but converted between them IMPLICITLY, which")
    print("  guessed an encoding and guessed wrong (the UnicodeDecodeError era)")

    print("--- why implicit conversion was the mistake ---")
    accented = "naïve".encode("latin-1")
    print(f"  'naïve' as latin-1 bytes : {accented!r}")
    try:
        accented.decode("utf-8")                 # wrong encoding: EXPLICIT error
    except UnicodeDecodeError as exc:
        print(f"  decoding as utf-8 raises : UnicodeDecodeError")
    print(f"  decoding as latin-1 works: {accented.decode('latin-1')!r}")
    print("  the SAME bytes mean different text under different encodings, so")
    print("  there is no 'the' encoding to guess. Python 2 guessed (ascii) and")
    print("  exploded on any non-ascii; Python 3 REFUSES to guess - you name it")

    print("--- one character, several representations ---")
    for ch, name in ((chr(65), "A (ascii)"), (chr(233), "e-acute"),
                     (chr(0x1F600), "emoji")):
        utf8 = ch.encode("utf-8")
        print(f"  {name:<12} : 1 char, {len(utf8)} utf-8 bytes ({utf8.hex()})")
    print("  a char is one code point; its BYTE length depends on the")
    print("  encoding. conflating the two (char == byte) is the ascii-era")
    print("  assumption 2.0 began to dismantle and 3.0 finished (Deep D)")

    print("--- the constraint answered, across a decade ---")
    print("  ABC could not do proper text (Chapter 1). 2.0 added unicode as a")
    print("  SECOND type - a half-fix that still converted implicitly. 3.0")
    print("  made str=text, bytes=bytes, conversion explicit - the full fix.")
    print("  this is the timeline at its slowest and most deliberate: a flaw")
    print("  named in 1989, half-fixed in 2000, fully fixed in 2008 (Deep D)")


if __name__ == "__main__":
    main()
