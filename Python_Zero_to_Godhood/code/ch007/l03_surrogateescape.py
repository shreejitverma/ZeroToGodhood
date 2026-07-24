"""Listing 7.3 - surrogateescape round-trips arbitrary bytes through a str
losslessly.

str.encode / bytes.decode take an error handler for malformed data: strict
(raise), ignore, replace, backslashreplace, and surrogateescape. The last is how
Python survives the Unix filesystem: POSIX paths are arbitrary byte sequences,
not guaranteed valid UTF-8. Each undecodable byte b is mapped to a lone
surrogate U+DC00 + b on decode and back to b on encode, so the bytes survive a
trip through str.
"""

raw = b"bad_\xff_path.txt"

decoded = raw.decode("utf-8", "surrogateescape")
reencoded = decoded.encode("utf-8", "surrogateescape")

print("--- an undecodable byte survives a round trip through str ---")
print("  original bytes     :", raw)
print("  round-trips exactly:", reencoded == raw)
print("  0xFF became lone surrogate U+DCFF:", "\udcff" in decoded)

print()
print("--- strict would have raised instead ---")
try:
    raw.decode("utf-8")               # default strict handler
except UnicodeDecodeError as exc:
    print("  strict decode ->", type(exc).__name__ + ":", str(exc)[:60])

print()
print("This is exactly how os.fsencode/os.fsdecode and sys.argv handle")
print("filenames. Always pass encoding= explicitly to open/encode/decode;")
print("relying on the locale default is the cause of 'works on my machine,")
print("UnicodeDecodeError in the container'.")
