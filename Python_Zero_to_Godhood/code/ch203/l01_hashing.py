"""Listing 203.1 - hashlib: content identity, the avalanche, and blake2's extras.

The volume has been SPENDING digests for five chapters - RECORD hashes,
lockfile pins, entropy chains - and this is the chapter that mints them. A
cryptographic hash maps any bytes to a fixed-size digest such that collisions
and preimages are computationally out of reach; everything else (content
addressing, integrity, dedup keys) is corollary. The listing shows the
interface's three shapes (one-shot, incremental, file), measures the
avalanche property as a bit-count, and tours blake2's built-in extras -
keying and personalisation - that quietly replace whole constructions.
"""

import hashlib
import io

DOC = b"amount=1500;currency=EUR;beneficiary=ACME"


def bit_difference(a: bytes, b: bytes) -> float:
    diff = sum((x ^ y).bit_count() for x, y in zip(a, b))
    return diff / (len(a) * 8)


def main() -> None:
    print("--- one document, the standard digests ---")
    for name in ("md5", "sha1", "sha256", "sha3_256", "blake2b"):
        h = hashlib.new(name, DOC)
        print(f"  {name:<9} {h.digest_size * 8:>4} bits  "
              f"{h.hexdigest()[:32]}...")
    print("  same input, fixed sizes, hex spellings of Chapter 120. md5 and")
    print("  sha1 are BROKEN for collision resistance - fine as checksums,")
    print("  disqualified wherever an adversary chooses inputs (Chapter 116's")
    print("  whole trust chain rests on that distinction)")

    print("--- the avalanche, counted ---")
    tampered = DOC.replace(b"1500", b"1501")
    a = hashlib.sha256(DOC).digest()
    b = hashlib.sha256(tampered).digest()
    print(f"  change one digit of the amount; differing digest bits : "
          f"{bit_difference(a, b):.1%}")
    print("  ~half of all 256 bits flip for a one-character edit: digests")
    print("  carry NO locality, which is why they can stand for content")
    print("  (Chapter 114's tamper test) and why they are useless as")
    print("  similarity measures (Chapter 118's difflib is that tool)")

    print("--- three interfaces, one digest ---")
    one_shot = hashlib.sha256(DOC).hexdigest()
    inc = hashlib.sha256()
    for i in range(0, len(DOC), 7):
        inc.update(DOC[i:i + 7])
    with io.BytesIO(DOC) as fh:
        filed = hashlib.file_digest(fh, "sha256").hexdigest()
    print(f"  one-shot == incremental == file_digest : "
          f"{one_shot == inc.hexdigest() == filed}")
    print("  update() carries state (Chapter 91's streaming shape), so")
    print("  gigabyte files hash in fixed memory; file_digest (3.11+) wraps")
    print("  the chunk loop everyone wrote by hand, buffer-sized correctly")

    print("--- blake2: the digest with the batteries ---")
    keyed = hashlib.blake2b(DOC, key=b"api-secret", digest_size=16)
    unkeyed = hashlib.blake2b(DOC, digest_size=16)
    print(f"  keyed digest    : {keyed.hexdigest()}")
    print(f"  unkeyed differs : {keyed.hexdigest() != unkeyed.hexdigest()}")
    invoice_id = hashlib.blake2b(DOC, person=b"invoice-v1", digest_size=8)
    receipt_id = hashlib.blake2b(DOC, person=b"receipt-v1", digest_size=8)
    print(f"  person='invoice-v1' : {invoice_id.hexdigest()}")
    print(f"  person='receipt-v1' : {receipt_id.hexdigest()}")
    print("  key= makes blake2 a MAC by construction (Chapter 80 built HMAC")
    print("  for hashes that lack this); person= separates DOMAINS, so the")
    print("  same bytes yield unrelated ids in different subsystems - the")
    print("  fix for cross-protocol digest collisions, built into the API")

    print("--- what a digest is not ---")
    print("  not encryption (nothing comes back out), not a password store")
    print("  (fast hashes invite brute force; Chapter 124's KDFs are the")
    print("  tool), and not unique-by-magic: it is unique because 2^128+ is")
    print("  larger than everything you will ever hash, and only while the")
    print("  algorithm stays unbroken - which is why names appear in Chapter")
    print("  114's lockfiles: hashes are versioned artifacts too")


if __name__ == "__main__":
    main()
