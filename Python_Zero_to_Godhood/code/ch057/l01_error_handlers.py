"""Listing 57.1 - encoding error handlers: what to do with bytes that do not fit.

Decoding bytes that are not valid in the codec (or encoding characters the codec
cannot represent) forces a choice, made by the errors= handler:
  strict           : raise (the default; fail loudly)
  replace          : substitute U+FFFD on decode / '?' on encode  (LOSSY)
  ignore           : drop the offending bytes/chars entirely       (LOSSY, silent)
  backslashreplace : escape them as \\xNN / \\uNNNN                  (reversible text)
  surrogateescape  : stash undecodable bytes in surrogate codepoints (LOSSLESS round-trip)
  xmlcharrefreplace: encode-only, as &#NNNN;                         (for XML/HTML)
surrogateescape is special: it is the only handler that round-trips undecodable
bytes losslessly, which is why Python uses it for filesystem paths and os.environ.
This listing shows each on invalid UTF-8 and on an unrepresentable character.
"""


def main() -> None:
    raw = b"caf\xe9 latte"     # 0xe9 is 'e-acute' in Latin-1, INVALID as UTF-8

    print("--- decode: bytes that are not valid UTF-8 ---")
    print(f"  strict           : raises UnicodeDecodeError (the default)")
    for h in ["replace", "ignore", "backslashreplace", "surrogateescape"]:
        print(f"  {h:16} : {raw.decode('utf-8', errors=h)!r}")

    print("--- surrogateescape round-trips the undecodable bytes losslessly ---")
    decoded = raw.decode("utf-8", errors="surrogateescape")
    reencoded = decoded.encode("utf-8", errors="surrogateescape")
    print(f"  decode then encode == original : {reencoded == raw}")
    print(f"  (this is why sys.getfilesystemencoding uses surrogateescape)")

    print("--- 'ignore' silently loses data (the dangerous one) ---")
    print(f"  b'caf\\xe9 latte'.decode(ignore) : {raw.decode('utf-8', errors='ignore')!r}")
    print(f"  the byte is gone, no error, no way to recover it")

    print("--- encode: a character the target codec cannot represent ---")
    s = "price: 5€"        # euro sign, not in Latin-1
    for h in ["replace", "ignore", "backslashreplace", "xmlcharrefreplace"]:
        print(f"  {h:18} : {s.encode('latin-1', errors=h)!r}")


if __name__ == "__main__":
    main()
