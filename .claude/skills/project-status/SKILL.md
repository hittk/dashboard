---
name: project-status
description: Produce a sanitised status update for the public projects dashboard from what the current session actually did. Use when the user types /project-status, or asks to update the dashboard, log progress, or record where a project has got to. Emits YAML for projects/<id>.yml with all identifying detail stripped.
---

# Project status update

Turn the work of the current session into a status update for the user's projects
dashboard (`hittk/dashboard`), as YAML matching one file in its `projects/` directory.

**That repo is public.** Everything you emit will be world-readable, permanently. This
skill's entire job is to record the *shape* of the work while leaving out its
*substance*.

## What to do

1. **Identify the project.** The user usually passes a slug (`/project-status orion`). If
   not, infer one from the repository or ask. The `id` must match the target filename.
2. **Read the existing file if you can reach it** — the dashboard repo may be checked out
   locally, or you can fetch `projects/<id>.yml` from GitHub. Preserve `id`, `codename`,
   `started`, and existing milestone ids: this is an update, not a fresh write. If you
   cannot reach it, emit a complete file and tell the user to reconcile the fields you
   guessed.
3. **Review what this session actually did.** Files touched, decisions taken, things that
   got stuck. Map each onto a milestone in `plan` and update its `status`.
4. **Set the fields that people forget:**
   - `updated` — today's date, always.
   - `next_action` — the single next concrete step. If the session ended mid-thought,
     this is the most valuable field on the page.
   - `blocked_on_me` — anything that needs a decision from the user before work can
     continue. Include the actual choice in `decision`. Set `since` to when it arose.
   - `waiting_on` — anything parked on someone external. `who` is a **role**, never a
     name.
   - `log` — one entry, dated today, ≤160 chars, in outcome terms. Newest first, keep
     the list at ten by dropping the oldest.
5. **Set `status` honestly.** Green means on track. Two late milestones is not green. If
   you'd be marking it green while listing overdue work, say amber and explain why in the
   log line.
6. **Sanitise, then check again.** See below.
7. **Output the YAML in a single fenced block**, then a one-paragraph plain-language
   summary of what changed. If a detail was omitted for privacy, say so — the user may
   want to record it somewhere private.

## Sanitising — the part that matters

Strip every one of these, without exception:

- **Names** of clients, customers, employers, partners, unreleased products, and people.
  Use the project codename and role descriptions (`reviewer`, `external — supplier`).
- **Locations**: repository names and URLs, file paths, branch names, ticket ids,
  internal tool names.
- **Code**: snippets, function names, schemas, config, error messages, stack traces, log
  output.
- **Infrastructure**: hostnames, domains, IPs, ports, bucket or account identifiers.
- **Credentials**: tokens, keys, passwords, connection strings — anything, even expired,
  even fake-looking.
- **Commercial detail**: rates, revenue, contract terms, headcount.
- **Contact details** of any kind.

Rewrite rather than delete. "Fixed the OAuth refresh bug in `auth/session.ts` for
Northwind" becomes "Resolved a session-expiry defect". The milestone moved; that's the
information the dashboard needs.

Field limits, which also keep detail out: `summary` ≤200, milestone `title` ≤80,
`next_action.title` ≤120, `decision` ≤200, `log[].note` ≤160.

**If you are unsure whether something is safe to include, leave it out.** A vaguer
dashboard costs the user nothing. A leak is permanent.

## Output shape

```yaml
id: orion
codename: Orion
summary: One generic sentence describing what this project is for.
status: amber
stage: build
started: 2026-05-12
target: 2026-09-30
updated: 2026-07-27
plan:
  - id: m1
    title: Generic milestone name
    status: done
    due: 2026-06-20
  - id: m2
    title: The one in flight
    status: in_progress
    due: 2026-08-01
next_action:
  title: The single next concrete step
  due: 2026-07-31
blocked_on_me:
  - title: What is stuck
    decision: The choice that has to be made
    since: 2026-07-20
waiting_on:
  - title: What is parked
    who: external — platform team
    since: 2026-07-15
risks:
  - title: What could derail this
    severity: medium
    mitigation: What would recover it
log:
  - date: 2026-07-27
    note: What changed this session, in outcome terms.
```

Valid values — `status`: green, amber, red, paused, done · `stage`: discovery, build,
review, shipped · milestone `status`: done, in_progress, todo, blocked · `severity`:
high, medium, low. Omit optional sections entirely rather than emitting empty lists.

## If you can write to the dashboard repo

Only when the user asks. Write the file, run `make all` (privacy gate + validation) from
the dashboard repo root, and push to `main` — the site redeploys itself. If the privacy
gate fails, fix the file; never bypass the check.
