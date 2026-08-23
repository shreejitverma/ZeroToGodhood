# Build system for "Python: Zero to Godhood"
# Run from the book ROOT:  make -f build/Makefile all | pdf | epub | html
# Requires: pandoc 3.x, lualatex (TeX Live), Python 3, poppler (pdftoppm).

PANDOC  := pandoc
HL      := build/code.theme
PDF     := build/Python_Zero_to_Godhood.pdf
EPUB    := build/Python_Zero_to_Godhood.epub
HTML    := build/Python_Zero_to_Godhood.html
COVER   := build/cover.png

PDF_OPTS := --from=markdown+raw_attribute+fenced_code_attributes+pipe_tables \
            --top-level-division=chapter --syntax-highlighting=$(HL) \
            -V documentclass=scrbook -V classoption=11pt -V classoption=DIV=calc \
            -H build/preamble.tex --lua-filter=build/breakcode.lua \
            --pdf-engine=lualatex --pdf-engine-opt=-interaction=nonstopmode

WEB_META := --metadata title="Python: Zero to Godhood" \
            --metadata author="Shreejit Verma" --metadata lang=en

.PHONY: all pdf epub html clean

all: pdf epub html

# --verbose makes pandoc echo the full LuaLaTeX log; it is kept in build/build_full.log
# so overfull boxes and missing glyphs can be audited after the build.
pdf:
	python3 build/assemble.py
	$(PANDOC) build/book_body.md -o $(PDF) $(PDF_OPTS) --verbose > build/build_full.log 2>&1
	@echo "==> $(PDF)  (log: build/build_full.log)"

$(COVER): pdf
	pdftoppm -png -r 200 -f 1 -l 1 -singlefile $(PDF) build/cover_tmp
	mv build/cover_tmp.png $(COVER)

epub: $(COVER)
	python3 build/assemble_web.py
	$(PANDOC) build/book_web.md -o $(EPUB) \
	  --from=markdown+fenced_code_attributes+pipe_tables \
	  --syntax-highlighting=$(HL) --toc --toc-depth=1 --split-level=1 \
	  --epub-cover-image=$(COVER) --css build/epub.css $(WEB_META)
	@echo "==> $(EPUB)"

html:
	python3 build/assemble_web.py
	$(PANDOC) build/book_web.md -o $(HTML) \
	  --from=markdown+fenced_code_attributes+pipe_tables \
	  --syntax-highlighting=$(HL) --standalone --toc --toc-depth=2 \
	  --embed-resources --css build/html.css $(WEB_META)
	@echo "==> $(HTML)"

clean:
	rm -f $(PDF) $(EPUB) $(HTML) $(COVER) build/*_body.md build/book_web.md build/build_full.log build/manifest.tsv
