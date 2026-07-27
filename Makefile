.PHONY: help check build serve denylist all

help:
	@echo "make check     — run the privacy gate over projects/"
	@echo "make build     — validate project files and generate site/data.json"
	@echo "make serve     — build, then serve the dashboard at http://localhost:8000"
	@echo "make denylist  — hash .denylist.txt into scripts/denylist.sha256"
	@echo "make all       — check + build (what CI runs)"

check:
	@python3 scripts/privacy_check.py

build:
	@python3 scripts/build.py

serve: all
	@echo "Dashboard on http://localhost:8000 — Ctrl-C to stop"
	@python3 -m http.server 8000 --directory site

denylist:
	@python3 scripts/privacy_check.py --update-denylist

all: check build
