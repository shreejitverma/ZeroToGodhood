"""Listing 201.1 - binary-to-text: sending bytes through channels built for text.

Deep D separated text from bytes; this chapter is the bridge for the channels
that only carry text - JSON documents, URLs, email, HTML, log lines. A
binary-to-text codec maps arbitrary bytes into a safe character subset and
back, and every design in base64/binascii is a trade between expansion ratio,
alphabet safety, and human readability. The listing shows the family on ONE
payload, the alphabet collision that motivates urlsafe_b64, the padding
contract, and the volume's running example paying off: Chapter 109's RECORD
hashes were urlsafe-base64 all along.
"""

import base64
import binascii

PAYLOAD = bytes(range(0, 251, 10)) + b"\xfb\xff>>?"


def main() -> None:
    print("--- one payload, four codecs, three trades ---")
    print(f"  payload ({len(PAYLOAD)} bytes) : {PAYLOAD!r}")
    for name, encoded in (
        ("hex (base16)", binascii.hexlify(PAYLOAD)),
        ("base32", base64.b32encode(PAYLOAD)),
        ("base64", base64.b64encode(PAYLOAD)),
        ("base85", base64.b85encode(PAYLOAD)),
    ):
        ratio = len(encoded) / len(PAYLOAD)
        print(f"  {name:<13} {ratio:4.2f}x  {encoded.decode()[:44]}...")
    print("  hex doubles but survives anywhere and is diffable by eye;")
    print("  base64 is the 4/3 workhorse; base85 squeezes to 5/4 with a")
    print("  spikier alphabet; base32 spends 8/5 to stay case-insensitive")
    print("  (filesystems, DNS). the codec is a CHANNEL statement")

    print("--- the alphabet collision, and the urlsafe fix ---")
    tricky = b"\xfb\xef\xbe"
    standard = base64.b64encode(tricky)
    urlsafe = base64.urlsafe_b64encode(tricky)
    print(f"  standard b64 : {standard!r}   ('+' and '/' live in the alphabet)")
    print(f"  urlsafe  b64 : {urlsafe!r}   ('-' and '_' instead)")
    print("  '+' means space in form-encoding and '/' is the path separator:")
    print("  standard base64 inside a URL corrupts SILENTLY on the way")
    print("  through one innocent unquote. same 64 symbols, different treaty")

    print("--- padding: the contract everyone trims ---")
    for raw in (b"M", b"Ma", b"Man"):
        print(f"  b64({raw!r:<7}) = {base64.b64encode(raw).decode()!r}")
    trimmed = "TWE"                       # 'Ma' with padding stripped
    padded = trimmed + "=" * (-len(trimmed) % 4)
    print(f"  decode of trimmed {trimmed!r} after re-padding : "
          f"{base64.b64decode(padded)!r}")
    print("  '=' pads groups to 4; length mod 4 recovers it, which is why")
    print("  JWTs and Chapter 109's RECORD strip it - and why every decoder")
    print("  of trimmed input re-pads with '=' * (-len % 4) first")

    print("--- validation is opt-in, and the default is forgiving ---")
    noisy = b"TW\n Fu"                    # 'Man' with whitespace injected
    print(f"  b64decode(noisy)             : {base64.b64decode(noisy)!r}")
    try:
        base64.b64decode(b"T@Fu", validate=True)
    except binascii.Error as exc:
        print(f"  validate=True on 'T@Fu'      : Error({exc})")
    print("  the default DISCARDS characters outside the alphabet (newlines")
    print("  from MIME wrapping); validate=True rejects them - the right")
    print("  setting whenever the input is a boundary, not a mail body")

    print("--- the volume's thread, tied ---")
    digest = b"\x1e4\xea\xcb"             # any binary digest prefix
    record_style = base64.urlsafe_b64encode(digest).rstrip(b"=")
    print(f"  urlsafe, trimmed : {record_style.decode()!r}")
    print("  Chapter 109's RECORD, Chapter 114's lockfiles, JWTs, and content")
    print("  addresses everywhere: binary digests riding text channels via")
    print("  exactly this codec, exactly this trim")


if __name__ == "__main__":
    main()
