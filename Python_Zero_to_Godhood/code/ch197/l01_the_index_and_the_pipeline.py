"""Listing 197.1 - the index, the trust chain, and the volume as one pipeline.

Deep N closes by assembling its chapters into the thing they describe: a
working installer. A local index in PEP 503's shape (a directory of names, a
page of filename anchors with hash fragments) is built from wheels this
volume created; then one function runs the full client pipeline OFFLINE:

    discover (the index page)      -> Chapter 116
    normalise the requested name   -> PEP 503, this listing
    filter candidates by tag       -> Chapter 110's selector
    verify content by hash         -> Chapter 114's anchor
    extract onto the path          -> Chapter 109's install

Every stage is a prior chapter's listing, imported and composed - the
volume's mechanisms literally are an installer. The closing block prints the
execution-surface audit: exactly where "installing" can run code, which is
the supply-chain map the prose completes.
"""

import hashlib
import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ch190.l01_anatomy_of_an_installed_package import build_wheel  # noqa: E402
from ch191.l01_the_tag_system import (acceptable_score,  # noqa: E402
                                      this_interpreter_tag)
from ch192.l01_the_build_contract import (MODULE, PYPROJECT,  # noqa: E402
                                          build_wheel as build_contract_wheel)


def normalise(name: str) -> str:
    """PEP 503: case-insensitive; runs of -, _, . are equivalent."""
    return re.sub(r"[-_.]+", "-", name).lower()


def build_index(index_root: Path, wheels: list[Path]) -> None:
    for wheel in wheels:
        name = normalise(wheel.name.split("-")[0])
        page_dir = index_root / name
        page_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
        anchor = (f'<a href="../../pool/{wheel.name}'
                  f'#sha256={digest}">{wheel.name}</a>')
        page = page_dir / "index.html"
        existing = page.read_text() if page.exists() else ""
        page.write_text(existing + anchor + "\n")


def install(requested: str, index_root: Path, pool: Path, site: Path) -> list[str]:
    log = []
    name = normalise(requested)
    log.append(f"normalise {requested!r:<16} -> {name!r}")
    page = index_root / name / "index.html"
    anchors = re.findall(r'href="[^"#]*/([^"#]+)#sha256=([0-9a-f]{64})"',
                         page.read_text())
    log.append(f"discover  {len(anchors)} candidate file(s) on the page")
    mine = this_interpreter_tag()
    best, best_score, expected_hash = None, 0, None
    for filename, digest in anchors:
        _, _, python, abi, _ = filename.removesuffix(".whl").split("-")
        score = acceptable_score(python, abi, mine)
        if score > best_score:
            best, best_score, expected_hash = filename, score, digest
    log.append(f"filter    tag-compatible best: {best}")
    data = (pool / best).read_bytes()
    verified = hashlib.sha256(data).hexdigest() == expected_hash
    log.append(f"verify    sha256 matches index fragment : {verified}")
    if verified:
        with zipfile.ZipFile(pool / best) as zf:
            zf.extractall(site)
        log.append("extract   installed (Chapter 109's operation)")
    return log


def main() -> None:
    print("--- name normalisation: one namespace, many spellings ---")
    for spelling in ("My.Package", "my-package", "MY__PACKAGE"):
        print(f"  {spelling:<14} -> {normalise(spelling)}")
    print("  PEP 503 folds case and runs of separators, so these are ONE")
    print("  project - and a squatter cannot register a spelling variant")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        pool = work / "pool"
        pool.mkdir()
        source = work / "src"
        source.mkdir()
        (source / "pyproject.toml").write_text(PYPROJECT)
        (source / "contractpkg.py").write_text(MODULE)
        wheels = [build_wheel(pool),
                  pool / build_contract_wheel(pool, _source=source)]
        index_root = work / "simple"
        build_index(index_root, wheels)

        print("--- the index: a directory of names, a page of hashed links ---")
        page = (index_root / "tinypkg" / "index.html").read_text().strip()
        shown = re.sub(r"sha256=[0-9a-f]{16}[0-9a-f]+", "sha256=<64 hex>", page)
        print(f"  /simple/tinypkg/ : {shown}")
        print("  filenames carry the tags (Chapter 110), fragments carry the")
        print("  hashes (Chapter 114): the whole contract fits in an anchor")

        print("--- the pipeline, composed from this volume's chapters ---")
        site = work / "site"
        site.mkdir()
        for line in install("TinyPkg", index_root, pool, site):
            print(f"  {line}")
        sys.path.insert(0, str(site))
        try:
            import tinypkg
            print(f"  import tinypkg; answer() : {tinypkg.answer()}")
        finally:
            sys.path.remove(str(site))
            sys.modules.pop("tinypkg", None)
        print("  discover, normalise, filter, verify, extract: five chapters,")
        print("  one function, zero network - an installer is nothing else")

        print("--- where installing can run code: the surfaces ---")
        print("  wheel extract        : never (Chapter 109's asymmetry)")
        print("  sdist build          : always - the backend is code (Ch 111)")
        print("  .pth import lines    : at every startup after (Chapter 113)")
        print("  entry-point scripts  : at first use, as you (Chapter 109)")
        print("  the map says where review effort goes: prefer wheels, lock")
        print("  and hash everything (Ch 114), audit .pth (Ch 113), and treat")
        print("  an sdist build as running the publisher's code - because it is")


if __name__ == "__main__":
    main()
