# Keeping the dashboard true

A status dashboard is only worth opening if it's accurate. This is the small amount of
routine that keeps it that way, and the tooling that removes most of the effort.

---

## The weekly review — ten minutes

Open the dashboard and work top to bottom. The page is deliberately ordered so this
takes one pass.

1. **Blocked on me.** Everything here is stopped because of you. Clear it, or write down
   what you're waiting for and move it to `waiting_on`. An item over two weeks old is
   flagged bold — that's a decision you're avoiding, not a decision that's hard.
2. **Next action, per project.** Every active project needs exactly one. If you can't
   name it, the project is either finished, paused, or not really understood — set
   `status: paused` and say so rather than leaving it drifting in green.
3. **Risks & slipping.** For each overdue milestone: move the date, cut the scope, or
   change the project's status. Do not leave a green project with a milestone three
   weeks late — the dashboard shows both, and the contradiction is the point.
4. **Stale badges.** Anything not updated in 7 days. Either update it or accept that it's
   dormant and mark it paused.
5. **Bump `updated`** on every file you touched, and push.

## Updating from inside a project session

Most status updates should come from the session that did the work — it already knows
what happened. The `/project-status` skill turns that into a sanitised YAML block.

### One-time setup

The skill lives at `.claude/skills/project-status/SKILL.md` in this repo, which makes it
available in sessions on *this* repo only. To use it from any project:

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/.claude/skills/project-status" ~/.claude/skills/project-status
```

(Copy instead of symlink if you'd rather it not change under you.)

### Using it

In a Claude Code session in any project repo, after a chunk of work:

```
/project-status orion
```

It summarises what the session did, maps it onto the project's milestones, strips
anything identifying, and prints a YAML block. Paste that over the matching file in
`projects/`, or point the session at a clone of this repo and let it write and push.

### If the skill isn't available

Paste this into any session instead:

> Summarise what we did in this session as a status update for my public projects
> dashboard. Output **only** a YAML block matching this shape:
>
> ```yaml
> id: <slug>
> codename: <Codename>
> summary: <one generic sentence, max 200 chars>
> status: green|amber|red|paused|done
> stage: discovery|build|review|shipped
> started: YYYY-MM-DD
> target: YYYY-MM-DD
> updated: <today>
> plan:
>   - { id: m1, title: <generic milestone>, status: done|in_progress|todo|blocked, due: YYYY-MM-DD }
> next_action: { title: <the single next step>, due: YYYY-MM-DD }
> blocked_on_me:
>   - { title: <what's stuck>, decision: <the choice I have to make>, since: YYYY-MM-DD }
> waiting_on:
>   - { title: <what>, who: <a role, never a name>, since: YYYY-MM-DD }
> risks:
>   - { title: <what could derail this>, severity: high|medium|low, mitigation: <what recovers it> }
> log:
>   - { date: <today>, note: <what changed, max 160 chars> }
> ```
>
> This goes in a **public** repo. Record the shape of the work, never its substance.
> Absolutely no client, employer, product or people's names; no repo names, file paths,
> URLs, hostnames, IPs or code; no credentials of any kind; no commercial figures. Use a
> codename for the project and roles for people. If you are unsure whether a detail is
> safe, leave it out — the dashboard only needs progress, not particulars.

## Conventions worth holding to

**Codenames are permanent.** Once `Atlas` means a particular project, it always does.
Renaming breaks your own recall and the deep links.

**Chunky milestones.** Five to eight per project. Thirty milestones is a task list, and
adherence stops meaning anything.

**The log is a changelog, not a journal.** One line per meaningful change, in outcome
terms. Ten entries maximum — trim the oldest.

**Set status honestly.** Green means on track. If two milestones are late, it isn't
green, and a dashboard that flatters you is worse than no dashboard.

**When a project finishes**, set `status: done` and leave the file. It drops out of the
active counts, keeps its history, and stops nagging you.
