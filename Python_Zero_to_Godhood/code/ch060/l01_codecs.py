"""Listing 60.1 - UTF-8/16/32: the same text, different byte sizes, and the BOM.

A str is code points in memory (Chapter 56); a codec turns it into bytes for disk
or wire. The UTF codecs trade size differently by script:
  UTF-8  : 1 byte for ASCII, 2 for Latin/Greek/Cyrillic, 3 for most CJK, 4 for
           astral. ASCII-compatible, no byte-order issue. The web/disk default.
  UTF-16 : 2 bytes for the whole BMP (so SMALLER than UTF-8 for CJK), 4 for astral.
  UTF-32 : always 4 bytes/char. Simple but wasteful; rarely used on disk.
The BOM (byte-order mark) disambiguates UTF-16/32 endianness and marks UTF-8-sig
files. This listing shows the size trade and the BOM bytes.
"""


def main() -> None:
    samples = [
        ("ASCII", "hello world"),
        ("Latin (café)", "café société"),
        ("CJK (世界)", "世界你好世界你好"),
        ("emoji", "😀😃😄😁"),
    ]
    print("--- same text, three codecs, different byte counts ---")
    print(f"  {'text':14} {'chars':>5} {'utf-8':>6} {'utf-16':>7} {'utf-32':>7}")
    for name, s in samples:
        u8 = len(s.encode("utf-8"))
        u16 = len(s.encode("utf-16-le"))
        u32 = len(s.encode("utf-32-le"))
        print(f"  {name:14} {len(s):>5} {u8:>6} {u16:>7} {u32:>7}")
    print("  (UTF-8 wins for ASCII/Latin; UTF-16 wins for CJK; UTF-32 always 4/char)")

    print("--- the BOM: a byte-order / signature mark ---")
    print(f"  utf-8      : {'😀'.encode('utf-8').hex()}  (no BOM)")
    print(f"  utf-8-sig  : {'😀'.encode('utf-8-sig').hex()}  (EF BB BF prefix)")
    print(f"  utf-16     : {'A'.encode('utf-16').hex()}  (FF FE BOM, then LE data)")
    print(f"  utf-16-le  : {'A'.encode('utf-16-le').hex()}  (explicit endian, no BOM)")

    print("--- decoding utf-8-sig strips the BOM; utf-8 leaves it as a char ---")
    with_bom = "text".encode("utf-8-sig")
    as_sig = with_bom.decode("utf-8-sig")
    as_plain = with_bom.decode("utf-8")
    print(f"  decode as utf-8-sig : {as_sig!r} (len {len(as_sig)}, clean)")
    print(f"  decode as utf-8     : {as_plain!r} (len {len(as_plain)}, leading U+FEFF)")
    print(f"  first char is BOM   : {as_plain[0] == chr(0xFEFF)}")


if __name__ == "__main__":
    main()
