# Project file schema

One YAML file per project in `projects/`, named `<id>.yml`. Validated by `scripts/build.py`;
anything invalid fails the build with a line-level message rather than rendering a broken
card.

Files starting with `_` are ignored (that's how `_TEMPLATE.yml` stays out of the dashboard).

Everything here is public. Read [PRIVACY.md](../PRIVACY.md) before writing a single field.

---

## Top level

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | yes | slug | `[a-z0-9-]+`, must equal the filename stem |
| `codename` | yes | string ≤40 | Display name. A codename — never the real client or product |
| `summary` | yes | string ≤200 | One generic sentence: what this project is for |
| `status` | yes | enum | `green` `amber` `red` `paused` `done` |
| `stage` | yes | enum | `discovery` `build` `review` `shipped` |
| `started` | yes | date | `YYYY-MM-DD` |
| `target` | no | date | `YYYY-MM-DD`. Omit if genuinely open-ended |
| `updated` | yes | date | When you last reviewed this file. Drives the stale badge |
| `plan` | yes | list | ≥1 milestone. See below |
| `next_action` | no | object | The single next concrete step |
| `blocked_on_me` | no | list | Decisions only you can make |
| `waiting_on` | no | list | Parked on someone or something external |
| `risks` | no | list | What could derail this |
| `links` | no | list | Genuinely public URLs only |
| `log` | no | list | ≤10 entries, newest first |

`status` is yours to set — it is not derived. The dashboard shows derived slippage
*alongside* it, so a green project with an overdue milestone is visibly inconsistent and
prompts you to fix one or the other.

## `plan[]` — the plan you're tracked against

| Field | Required | Type | Notes |
|---|---|---|---|
| `id` | yes | slug | Unique within the project |
| `title` | yes | string ≤80 | Generic milestone name |
| `status` | yes | enum | `done` `in_progress` `todo` `blocked` |
| `due` | no | date | `YYYY-MM-DD`. A past `due` that isn't `done` counts as slipping |
| `note` | no | string ≤160 | Optional one-liner |

Plan adherence on the dashboard is `done / total` milestones. Keep milestones chunky —
five to eight per project reads well; thirty does not.

## `next_action`

| Field | Required | Type |
|---|---|---|
| `title` | yes | string ≤120 |
| `due` | no | date |

## `blocked_on_me[]`

The queue the dashboard leads with. Only things **you** are the blocker for.

| Field | Required | Type | Notes |
|---|---|---|---|
| `title` | yes | string ≤120 | What is stuck |
| `decision` | no | string ≤200 | What you actually have to choose between |
| `since` | yes | date | Age is displayed and drives the sort — oldest first |

## `waiting_on[]`

| Field | Required | Type | Notes |
|---|---|---|---|
| `title` | yes | string ≤120 | |
| `who` | yes | string ≤60 | **A role, never a name.** `external — registrar`, `reviewer` |
| `since` | yes | date | |
| `chase_after` | no | date | Past this date the dashboard flags it for chasing |

## `risks[]`

| Field | Required | Type | Notes |
|---|---|---|---|
| `title` | yes | string ≤120 | |
| `severity` | yes | enum | `high` `medium` `low` |
| `mitigation` | no | string ≤200 | What would recover it |

## `links[]`

| Field | Required | Type | Notes |
|---|---|---|---|
| `label` | yes | string ≤40 | |
| `url` | yes | url | `https://` only, and only pages a stranger may see |

## `log[]`

| Field | Required | Type | Notes |
|---|---|---|---|
| `date` | yes | date | |
| `note` | yes | string ≤160 | Progress in outcome terms. Not a commit message |

Keep to 10 entries; trim the oldest. This is a changelog, not a journal.

---

## Derived by the build — do not hand-maintain

`adherence` (% milestones done) · `days_to_target` · `slipping[]` (overdue, not done) ·
`age_days` on every blocked and waiting item · `stale` (`updated` >7 days ago) ·
portfolio-level counts. All computed in `scripts/build.py` against the build date.
