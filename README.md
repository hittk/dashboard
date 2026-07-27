# Projects dashboard

One page showing every project in flight, how it's tracking against its plan, and —
first, before anything else — **what's waiting on me**.

**Live: https://hittk.github.io/dashboard**

This repo is public, so the dashboard is sanitised by design: codenames, milestones,
statuses and dates, never client detail, code or credentials. That isn't a convention
to remember — a [privacy gate](scripts/privacy_check.py) runs before every deploy and
fails the build if anything slips through. Read [PRIVACY.md](PRIVACY.md) once before you
add real projects.

---

## First-time setup

Three steps, about three minutes, all in the repo's **Settings**:

1. **Pages → Build and deployment → Source: _GitHub Actions_.**
   Not "Deploy from a branch" — the workflow publishes the artifact directly.
2. **Code security → enable _Secret scanning_ and _Push protection_.**
   Free on public repos. Blocks recognised credentials at `git push`, before the
   privacy gate ever has to catch them.
3. **Merge to `main`.** The deploy workflow runs and the site goes live.

Then replace the examples: delete `projects/atlas.yml`, `projects/beacon.yml` and
`projects/cinder.yml`, and copy `projects/_TEMPLATE.yml` once per real project.

## Adding or updating a project

Each project is one YAML file in [`projects/`](projects/), named `<id>.yml`. Fields are
documented in [`schema/project.schema.md`](schema/project.schema.md); the template has
every one of them with comments.

```bash
cp projects/_TEMPLATE.yml projects/orion.yml
$EDITOR projects/orion.yml
make serve            # privacy gate + build + preview on localhost:8000
git commit -am "Add Orion" && git push
```

Push to `main` and the site updates itself. Anything invalid — a bad status value, a
milestone with no id, a date that isn't a date — fails the build with the file and field
named, rather than rendering a broken card.

**Don't hand-maintain progress numbers.** Adherence, days remaining, item ages, slippage
and stale badges are all computed at build time from the dates you've written. A daily
scheduled rebuild keeps them current even in a week you don't touch the repo. (GitHub
disables scheduled workflows on a repo after 60 days without commits — a single push
re-enables it.)

## Commands

| Command | What it does |
|---|---|
| `make serve` | Gate, build, and preview on <http://localhost:8000> |
| `make check` | Privacy gate only |
| `make build` | Validate project files and write `site/data.json` |
| `make denylist` | Hash `.denylist.txt` into `scripts/denylist.sha256` |
| `make all` | Gate + build — exactly what CI runs |

Requires Python 3.9+ and PyYAML (`pip install pyyaml`). Nothing else — no npm, no
node_modules, no build tooling for the page itself.

## Keeping it current

The failure mode for a dashboard like this is drift: it's accurate for a fortnight, then
quietly becomes fiction. Two things counter that.

**The stale badge.** Any project whose `updated` date is more than 7 days old is marked
stale on its card, so a neglected project looks neglected instead of looking fine.

**`/project-status`.** A skill that runs inside *any* Claude Code session, in any of your
project repos. It reads what that session actually did and emits a sanitised YAML update
for the matching project file here. Setup and the weekly ritual are in
[docs/WORKFLOW.md](docs/WORKFLOW.md).

## How it's put together

```
projects/*.yml          the only thing you edit day to day
scripts/build.py        validates, computes every derived number, writes site/data.json
scripts/privacy_check.py the gate — credentials, paths, URLs, IPs, your hashed denylist
site/                   index.html + styles.css + app.js, hand-written, zero dependencies
.github/workflows/      deploy on main; validate everywhere else
```

The site fetches one generated `data.json` and renders it. No date arithmetic happens in
the browser, so what you see is always as of the last build — shown in the footer.

Accessibility is deliberate, not incidental: status is carried by shape and a written
label as well as hue (red and green are ~4 ΔE apart under deuteranopia, so colour alone
would fail), it works from 320px up, it follows your system light/dark with a manual
override, and it's navigable by keyboard.

## Troubleshooting

**Deploy fails at "Privacy gate".** Something in `projects/` tripped a rule; the log
names the file, line and rule. If it's a credential, rotate it before fixing the file.

**Deploy fails at "Validate and build".** A project file doesn't match the schema. The
log names the field. Reproduce locally with `make build`.

**Site loads but says "Could not load data.json".** You're opening `index.html` from the
filesystem. Use `make serve`.

**Pages 404s after a green deploy.** Settings → Pages → Source isn't set to
_GitHub Actions_ yet.
