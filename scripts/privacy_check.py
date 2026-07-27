#!/usr/bin/env python3
"""Sanitisation gate for a public dashboard repo.

Scans project files for anything that shouldn't be published, and fails the build
before the deploy step if it finds any. See PRIVACY.md for the rules this enforces.

    python3 scripts/privacy_check.py              # scan projects/
    python3 scripts/privacy_check.py path ...     # scan specific files or dirs
    python3 scripts/privacy_check.py --update-denylist

Exit codes: 0 clean, 1 findings, 2 usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import pathlib
import re
import subprocess
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
DENYLIST_PLAIN = ROOT / ".denylist.txt"
DENYLIST_HASHED = ROOT / "scripts" / "denylist.sha256"
DEFAULT_TARGETS = [ROOT / "projects"]

# Longest phrase length (in words) a denylist entry may have.
MAX_NGRAM = 4


# --------------------------------------------------------------------------- rules

class Rule:
    def __init__(self, name, pattern, why, flags=0):
        self.name = name
        self.regex = re.compile(pattern, flags)
        self.why = why


RULES = [
    # Credentials. Any hit is treated as burned regardless of whether it looks real.
    Rule("github-token", r"\bgh[pousr]_[A-Za-z0-9]{16,}\b",
         "GitHub token"),
    Rule("github-pat", r"\bgithub_pat_[A-Za-z0-9_]{20,}\b",
         "GitHub fine-grained PAT"),
    Rule("anthropic-key", r"\bsk-ant-[A-Za-z0-9_\-]{16,}\b",
         "Anthropic API key"),
    Rule("openai-key", r"\bsk-(?!ant-)[A-Za-z0-9]{20,}\b",
         "API key"),
    Rule("aws-key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
         "AWS access key ID"),
    Rule("google-key", r"\bAIza[0-9A-Za-z_\-]{35}\b",
         "Google API key"),
    Rule("slack-token", r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b",
         "Slack token"),
    Rule("private-key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
         "private key block"),
    Rule("jwt", r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b",
         "JSON Web Token"),
    Rule("secret-assignment",
         r"\b(?:password|passwd|secret|api[_\-]?key|access[_\-]?token|auth[_\-]?token)"
         r"\s*[:=]\s*\S+",
         "credential assignment"),
    Rule("connection-string", r"\b[a-z][a-z0-9+.\-]*://[^\s/@]+:[^\s/@]+@",
         "connection string with embedded credentials"),

    # Location leaks — these identify machines, repos and people.
    Rule("unix-path", r"(?:^|[\s\"'(\[])(?:/Users/|/home/|/var/|/etc/|/opt/|/srv/)\S+",
         "filesystem path"),
    Rule("windows-path", r"\b[A-Za-z]:\\\\?[A-Za-z0-9._\-]+\\", "Windows path"),
    Rule("ssh-remote", r"\bgit@[A-Za-z0-9.\-]+:", "git SSH remote"),
    Rule("ssh-url", r"\bssh://\S+", "SSH URL"),
    Rule("ip-address", r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "IP address"),
    Rule("email", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
         "email address"),

    # Substance rather than shape.
    Rule("stack-trace", r'(?:Traceback \(most recent call last\)|^\s*at [\w$.]+\(|'
                        r'\bException in thread\b|\bNullPointerException\b)',
         "stack trace", re.MULTILINE),
]

# A `url:` value may hold a public https link — that's what links[] is for.
URL_ANYWHERE = re.compile(r"\bhttps?://\S+")
URL_LINE = re.compile(r"^\s*-?\s*url\s*:\s*https://[^\s]+\s*$")

# Token-shaped strings: long, no spaces, mixed alphabet. Catches secrets no rule names.
ENTROPY_CANDIDATE = re.compile(r"[A-Za-z0-9+/=_\-]{24,}")
ENTROPY_THRESHOLD = 3.4


def shannon_entropy(s: str) -> float:
    counts = Counter(s)
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


# ------------------------------------------------------------------------ denylist

def normalise(text: str) -> list[str]:
    """Lowercase, strip punctuation, split into words. Shared by hashing and matching
    so that 'Acme Industries.' and 'acme  industries' produce the same hash."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


def sha(phrase: str) -> str:
    return hashlib.sha256(phrase.encode("utf-8")).hexdigest()


def load_denylist() -> set[str]:
    if not DENYLIST_HASHED.exists():
        return set()
    return {
        line.strip()
        for line in DENYLIST_HASHED.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def update_denylist() -> int:
    """Hash the plaintext terms in .denylist.txt so CI can match terms it cannot read."""
    if not DENYLIST_PLAIN.exists():
        print(f"No {DENYLIST_PLAIN.name} found. Create it (it is gitignored) with one "
              f"private term per line, then re-run.", file=sys.stderr)
        return 2

    hashes = set()
    skipped = 0
    for line in DENYLIST_PLAIN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        words = normalise(line)
        if not words:
            continue
        if len(words) > MAX_NGRAM:
            # Longer phrases can never match, since we only hash n-grams up to MAX_NGRAM.
            print(f"  skipped (over {MAX_NGRAM} words, use a shorter distinctive part): "
                  f"{len(words)} words", file=sys.stderr)
            skipped += 1
            continue
        hashes.add(sha(" ".join(words)))

    DENYLIST_HASHED.write_text(
        "# SHA-256 of private terms from .denylist.txt (gitignored).\n"
        "# Generated by `make denylist`. Safe to commit — the terms are not recoverable\n"
        "# from these hashes by anyone who doesn't already know them.\n"
        + "".join(f"{h}\n" for h in sorted(hashes)),
        encoding="utf-8",
    )
    print(f"Wrote {len(hashes)} hashed term(s) to {DENYLIST_HASHED.relative_to(ROOT)}"
          + (f" ({skipped} skipped)" if skipped else ""))
    return 0


def denylist_hits(text: str, denylist: set[str]) -> set[str]:
    """Hash every 1..MAX_NGRAM word window and look for a match. We report that a term
    matched, never which — the whole point is that the term stays out of the repo."""
    if not denylist:
        return set()
    words = normalise(text)
    hits = set()
    for size in range(1, MAX_NGRAM + 1):
        for i in range(len(words) - size + 1):
            h = sha(" ".join(words[i:i + size]))
            if h in denylist:
                hits.add(h)
    return hits


# -------------------------------------------------------------------------- scanning

class Finding:
    def __init__(self, path, line_no, rule, detail):
        self.path = path
        self.line_no = line_no
        self.rule = rule
        self.detail = detail


def display_path(p: pathlib.Path) -> str:
    """Repo-relative where possible — a path outside the repo (a file passed explicitly)
    must still print, not raise."""
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def redact(match: str) -> str:
    """Show enough to locate the problem, never enough to republish it here."""
    match = match.strip()
    if len(match) <= 12:
        return match
    return f"{match[:6]}…{match[-3:]} ({len(match)} chars)"


def scan_file(path: pathlib.Path, denylist: set[str]) -> list[Finding]:
    findings = []
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return [Finding(path, 0, "unreadable", str(exc))]

    for line_no, line in enumerate(text.splitlines(), start=1):
        for rule in RULES:
            for m in rule.regex.finditer(line):
                findings.append(Finding(path, line_no, rule.name,
                                        f"{rule.why}: {redact(m.group(0))}"))

        for m in URL_ANYWHERE.finditer(line):
            if URL_LINE.match(line):
                continue  # a links[] entry, which is allowed to be a public https URL
            findings.append(Finding(
                path, line_no, "url",
                f"URL outside a links[] url: field: {redact(m.group(0))}"))

        for m in ENTROPY_CANDIDATE.finditer(line):
            tok = m.group(0)
            if not (any(c.isdigit() for c in tok) and any(c.isalpha() for c in tok)):
                continue
            if shannon_entropy(tok) >= ENTROPY_THRESHOLD:
                findings.append(Finding(
                    path, line_no, "high-entropy",
                    f"token-shaped string, possible secret: {redact(tok)}"))

    for _ in denylist_hits(text, denylist):
        findings.append(Finding(
            path, 0, "denylist",
            "a term from your private denylist appears in this file"))

    return findings


def collect(targets: list[pathlib.Path]) -> list[pathlib.Path]:
    files = []
    for t in targets:
        if t.is_dir():
            files.extend(sorted(p for p in t.rglob("*")
                                if p.is_file() and p.suffix in {".yml", ".yaml"}))
        elif t.is_file():
            files.append(t)
        else:
            print(f"warning: no such path: {t}", file=sys.stderr)
    return files


def denylist_plaintext_tracked() -> bool:
    """The plaintext denylist must never be committed — it is the one file that would
    hand a reader the exact terms we're protecting."""
    try:
        out = subprocess.run(["git", "ls-files", "--error-unmatch", ".denylist.txt"],
                             cwd=ROOT, capture_output=True, text=True, timeout=10)
        return out.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*", type=pathlib.Path,
                    help="files or directories to scan (default: projects/)")
    ap.add_argument("--update-denylist", action="store_true",
                    help="hash .denylist.txt into scripts/denylist.sha256 and exit")
    args = ap.parse_args()

    if args.update_denylist:
        return update_denylist()

    denylist = load_denylist()
    files = collect(args.targets or DEFAULT_TARGETS)
    if not files:
        print("privacy: nothing to scan", file=sys.stderr)
        return 2

    findings = []
    if denylist_plaintext_tracked():
        findings.append(Finding(pathlib.Path(".denylist.txt"), 0, "denylist-plaintext",
                                "the plaintext denylist is tracked by git — "
                                "`git rm --cached .denylist.txt` immediately"))

    for f in files:
        findings.extend(scan_file(f, denylist))

    scanned = f"{len(files)} file(s), {len(denylist)} denylist term(s)"
    if not findings:
        print(f"privacy: clean — {scanned}")
        return 0

    print(f"privacy: {len(findings)} finding(s) — {scanned}\n", file=sys.stderr)
    for f in findings:
        loc = display_path(f.path)
        if f.line_no:
            loc += f":{f.line_no}"
        print(f"  {loc}  [{f.rule}] {f.detail}", file=sys.stderr)
    print("\nNothing will be deployed. See PRIVACY.md. If a credential is involved, "
          "rotate it before doing anything else.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
