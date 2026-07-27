# Privacy rules for this repo

**This repo is public. Everything committed here is world-readable, permanently, and is
already cached elsewhere by the time you notice a mistake.** Treat every commit as a
publication.

The dashboard is deliberately built to be useful *without* private detail. It tracks
**codenames, progress and decisions** — not the work itself.

## The rule

> Record the **shape** of the work, never its **substance**.

"Migrate the data layer" is fine. Which client, which database, which repo, which table —
not fine. If a line would tell a stranger something they couldn't already learn from your
public GitHub profile, it doesn't go in.

## Never commit

| Category | Examples |
|---|---|
| Identities | Client, customer, employer or partner names; unreleased product names |
| People | Anyone's name. Use a role: `external — registrar`, `reviewer`, `client contact` |
| Locations | Repo URLs or names, file paths (`/Users/…`, `/home/…`, `C:\…`), `git@…` remotes |
| Code | Source snippets, config, schemas, stack traces, error messages, log output |
| Infrastructure | Hostnames, internal domains, IP addresses, ports, bucket or project IDs |
| Credentials | Tokens, keys, passwords, connection strings, `.env` values — **anything**, even expired |
| Commercial | Rates, fees, revenue, contract terms, deal status, headcount |
| Contact | Email addresses, phone numbers, handles |

## Always fine

Codenames · milestone titles in generic language · statuses and dates · your own decisions
and what's blocking them · risk descriptions in outcome terms · links to genuinely public
pages.

## How this is enforced

Four layers, so a slip has to get past all of them:

1. **Schema limits.** Free text is capped (summary 200 chars, log notes 160). There is
   nowhere to paste a stack trace into.
2. **`scripts/privacy_check.py`.** Scans `projects/**` for credential shapes, paths, URLs,
   IPs, emails, high-entropy strings, and your own private terms. Run by
   `make check` and on every push.
3. **CI gate.** The deploy workflow runs the check *before* the build. A hit fails the run
   and nothing reaches Pages.
4. **GitHub push protection.** Blocks recognised secrets at `git push`. Enable it in
   *Settings → Code security* (see README).

## Your private denylist

Layers 1–3 can't know that "Northwind" is a client name. So you tell them — without putting
the word in the repo.

```bash
echo "northwind" >> .denylist.txt     # gitignored, stays on your machine
echo "acme industries" >> .denylist.txt
make denylist                          # writes SHA-256 hashes to scripts/denylist.sha256
```

`privacy_check.py` hashes every word and 2–4 word phrase in your project files and compares
against those hashes. It can block a term it cannot read, and the committed file reveals
nothing. Matching is case-insensitive and whitespace-normalised.

Rebuild the hash file whenever you add a term; commit `scripts/denylist.sha256` and never
`.denylist.txt`.

## If something private gets committed

Assume it is public the moment it is pushed.

1. **Rotate first.** Any credential is burned — replace it before anything else.
2. Remove the content and push the fix, so the live site stops serving it.
3. History still has it. Rewriting history (`git filter-repo`) does not purge forks, clones,
   caches or the GitHub API. For anything genuinely sensitive, contact GitHub Support to
   request cache purging — and treat the information as disclosed regardless.
4. Add the term to `.denylist.txt` and run `make denylist` so it can't recur.
