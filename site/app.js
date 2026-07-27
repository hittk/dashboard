/* Projects dashboard.
   Renders site/data.json, which scripts/build.py generates from projects/*.yml.
   All date arithmetic happens at build time — this file only formats and lays out.
   Everything is built with textContent, so project text is never parsed as markup. */

'use strict';

const STATUS_LABEL = {
  green:  'On track',
  amber:  'At risk',
  red:    'Off track',
  paused: 'Paused',
  done:   'Done',
};

const MILESTONE_MARK = {
  done:        { glyph: '✓', label: 'Done' },
  in_progress: { glyph: '▶', label: 'In progress' },
  todo:        { glyph: '○', label: 'To do' },
  blocked:     { glyph: '✕', label: 'Blocked' },
};

const SEVERITY_LABEL = { high: 'High', medium: 'Medium', low: 'Low' };

// ------------------------------------------------------------------ utilities

function el(tag, opts = {}, children = []) {
  const node = document.createElement(tag);
  if (opts.class) node.className = opts.class;
  if (opts.text != null) node.textContent = opts.text;
  for (const [k, v] of Object.entries(opts.attrs || {})) {
    if (v != null) node.setAttribute(k, v);
  }
  for (const child of [].concat(children)) {
    if (child) node.append(child);
  }
  return node;
}

function plural(n, word, suffix = 's') {
  return `${n} ${word}${n === 1 ? '' : suffix}`;
}

function fmtDate(iso) {
  if (!iso) return '';
  const d = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(d.valueOf())) return iso;
  return d.toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
  });
}

function fmtAge(days) {
  if (days <= 0) return 'today';
  if (days < 14) return plural(days, 'day');
  if (days < 60) return `${Math.floor(days / 7)} weeks`;
  return `${Math.floor(days / 30)} months`;
}

/** Codename chip that deep-links to the project card. */
function chip(project) {
  return el('a', {
    class: 'chip',
    text: project.codename,
    attrs: { href: `#${project.id}`, title: `Go to ${project.codename}` },
  });
}

function item({ project, title, detail, side, sideStrong }) {
  const node = el('div', { class: 'item' }, [
    el('span', { class: 'item__title' }, [project ? chip(project) : null,
                                          document.createTextNode(title)]),
  ]);
  if (side) {
    node.append(el('span', { class: `item__side age${sideStrong ? ' age--old' : ''}` },
                   [document.createTextNode(side)]));
  }
  if (detail) node.append(el('span', { class: 'item__detail', text: detail }));
  return node;
}

function fill(listName, nodes, emptyText) {
  const host = document.querySelector(`[data-list="${listName}"]`);
  host.replaceChildren(
    ...(nodes.length ? nodes : [el('p', { class: 'empty', text: emptyText })]),
  );
}

// -------------------------------------------------------------- action queue

function renderQueue(projects) {
  // Blocked on me — the reason this page leads where it does. Oldest first.
  const blocked = projects
    .flatMap(p => p.blocked_on_me.map(b => ({ p, b })))
    .sort((a, b) => b.b.age_days - a.b.age_days)
    .map(({ p, b }) => item({
      project: p,
      title: b.title,
      detail: b.decision ? `Decision: ${b.decision}` : null,
      side: `${fmtAge(b.age_days)} waiting`,
      sideStrong: b.age_days >= 14,
    }));
  fill('blocked', blocked, 'Nothing is blocked on you. Enjoy it.');

  // One next step per project that is still moving.
  const next = projects
    .filter(p => p.is_active && p.next_action)
    .map(p => {
      const overdue = p.next_action.due && p.next_action.due < DATA.meta.today;
      return item({
        project: p,
        title: p.next_action.title,
        side: p.next_action.due
          ? `${overdue ? 'was due ' : 'due '}${fmtDate(p.next_action.due)}`
          : null,
        sideStrong: overdue,
      });
    });
  fill('next', next, 'No next actions recorded. If a project is active, it needs one.');

  // Slipping milestones first (fact), then risks (judgement).
  const slipping = projects
    .flatMap(p => p.slipping.map(m => ({ p, m })))
    .sort((a, b) => b.m.days_overdue - a.m.days_overdue)
    .map(({ p, m }) => item({
      project: p,
      title: m.title,
      detail: `Milestone due ${fmtDate(m.due)}, still ${
        (MILESTONE_MARK[m.status] || {}).label?.toLowerCase() || m.status}.`,
      side: `${fmtAge(m.days_overdue)} late`,
      sideStrong: m.days_overdue >= 14,
    }));

  const risks = projects
    .flatMap(p => p.risks.filter(r => r.severity !== 'low').map(r => ({ p, r })))
    .sort((a, b) => (a.r.severity === 'high' ? -1 : 1) - (b.r.severity === 'high' ? -1 : 1))
    .map(({ p, r }) => item({
      project: p,
      title: r.title,
      detail: r.mitigation ? `Mitigation: ${r.mitigation}` : null,
      side: `${SEVERITY_LABEL[r.severity]} risk`,
      sideStrong: r.severity === 'high',
    }));

  fill('risks', slipping.concat(risks), 'Nothing overdue and no live risks.');

  // Parked elsewhere — visible so it gets chased rather than forgotten.
  const waiting = projects
    .flatMap(p => p.waiting_on.map(w => ({ p, w })))
    .sort((a, b) => (b.w.chase - a.w.chase) || (b.w.age_days - a.w.age_days))
    .map(({ p, w }) => item({
      project: p,
      title: w.title,
      detail: `With ${w.who}${w.chase ? ' — due a chase' : ''}.`,
      side: `${fmtAge(w.age_days)} waiting`,
      sideStrong: w.chase,
    }));
  fill('waiting', waiting, 'Not waiting on anyone.');
}

// --------------------------------------------------------------------- cards

function flag(text, kind) {
  return el('span', { class: `flag flag--${kind}`, text });
}

function planList(project) {
  const list = el('ul', { class: 'plan' });
  for (const m of project.plan) {
    const mark = MILESTONE_MARK[m.status] || { glyph: '·', label: m.status };
    const li = el('li', { attrs: { 'data-ms': m.status } }, [
      el('span', { class: 'plan__mark', text: mark.glyph,
                   attrs: { title: mark.label, 'aria-label': mark.label, role: 'img' } }),
      el('span', { class: 'plan__title', text: m.title }),
      m.due
        ? el('span', {
            class: `plan__due${m.overdue ? ' plan__due--over' : ''}`,
            text: m.overdue ? `${fmtDate(m.due)} · late` : fmtDate(m.due),
          })
        : el('span', { class: 'plan__due', text: '—' }),
    ]);
    if (m.note) li.append(el('span', { class: 'plan__note', text: m.note }));
    list.append(li);
  }
  return list;
}

function miniSection(title, entries) {
  if (!entries.length) return null;
  const list = el('ul', { class: 'mini' });
  for (const [strong, rest] of entries) {
    list.append(el('li', {}, [
      el('strong', { text: strong }),
      rest ? el('span', { text: ` — ${rest}` }) : null,
    ]));
  }
  return el('div', {}, [el('h4', { text: title }), list]);
}

function cardBody(project) {
  const body = el('div', {}, [
    el('h4', { text: `Plan — ${project.milestones_done} of ${project.milestones_total} done` }),
    planList(project),
  ]);

  // Node.append() stringifies null, so absent sections must be filtered out, not passed.
  body.append(...[
    miniSection('Blocked on me', project.blocked_on_me.map(
      b => [b.title, [b.decision, `waiting ${fmtAge(b.age_days)}`].filter(Boolean).join(' · ')])),
    miniSection('Waiting on', project.waiting_on.map(
      w => [w.title, `${w.who} · ${fmtAge(w.age_days)}${w.chase ? ' · chase' : ''}`])),
    miniSection('Risks', project.risks.map(
      r => [r.title, [`${SEVERITY_LABEL[r.severity]} severity`, r.mitigation].filter(Boolean).join(' · ')])),
  ].filter(Boolean));

  if (project.links.length) {
    const list = el('ul', { class: 'mini' });
    for (const l of project.links) {
      list.append(el('li', {}, [
        el('a', { text: l.label, attrs: { href: l.url, rel: 'noopener noreferrer' } }),
      ]));
    }
    body.append(el('div', {}, [el('h4', { text: 'Links' }), list]));
  }

  if (project.log.length) {
    const list = el('ul', { class: 'log' });
    for (const entry of project.log) {
      list.append(el('li', {}, [
        el('time', { text: fmtDate(entry.date), attrs: { datetime: entry.date } }),
        document.createTextNode(entry.note),
      ]));
    }
    body.append(el('div', {}, [el('h4', { text: 'Recent log' }), list]));
  }

  return body;
}

function renderCards(projects) {
  const tpl = document.getElementById('tpl-card');
  const host = document.getElementById('cards');
  const cards = projects.map(p => {
    const node = tpl.content.cloneNode(true).firstElementChild;
    node.id = p.id;
    node.dataset.active = String(p.is_active);
    node.dataset.attention = String(p.needs_attention);
    if (p.needs_attention) node.classList.add('card--attention');

    node.querySelector('[data-name]').textContent = p.codename;

    const pill = node.querySelector('[data-status]');
    pill.classList.add(`pill--${p.status}`);
    pill.textContent = STATUS_LABEL[p.status] || p.status;

    node.querySelector('[data-summary]').textContent = p.summary;

    const meta = node.querySelector('[data-meta]');
    const bits = [p.stage[0].toUpperCase() + p.stage.slice(1)];
    if (p.target) {
      bits.push(p.target_overdue
        ? `target ${fmtDate(p.target)} — passed`
        : `target ${fmtDate(p.target)} · ${fmtAge(p.days_to_target)} left`);
    } else {
      bits.push('no target date');
    }
    bits.push(p.days_since_update === 0
      ? 'updated today'
      : `updated ${fmtAge(p.days_since_update)} ago`);
    meta.replaceChildren(...bits.map(t => el('span', { text: t })));

    const pct = p.adherence;
    node.querySelector('[data-fill]').style.width = `${pct}%`;
    node.querySelector('[data-adherence]').textContent =
      `${pct}% · ${p.milestones_done}/${p.milestones_total}`;
    const meter = node.querySelector('[data-meter]');
    meter.setAttribute('role', 'img');
    meter.setAttribute('aria-label',
      `Plan adherence ${pct}%: ${p.milestones_done} of ${p.milestones_total} milestones done`);

    const flags = node.querySelector('[data-flags]');
    if (p.blocked_on_me.length) {
      flags.append(flag(`${p.blocked_on_me.length} blocked on you`, 'block'));
    }
    if (p.slipping.length) flags.append(flag(`${p.slipping.length} slipping`, 'slip'));
    if (p.stale) flags.append(flag(`stale ${fmtAge(p.days_since_update)}`, 'stale'));

    node.querySelector('[data-body]').replaceChildren(cardBody(p));
    return node;
  });
  host.replaceChildren(...cards);
}

// ---------------------------------------------------------- head, tiles, chrome

function renderHead(meta, projects) {
  const c = meta.counts;
  document.getElementById('subtitle').textContent =
    `${plural(c.projects, 'project')}, ${c.active} active · as of ${fmtDate(meta.today)}`;

  const tiles = [
    { value: c.active, label: 'Active projects', href: '#projects', alert: false },
    { value: c.blocked_on_me, label: 'Blocked on you', href: '#blocked', alert: c.blocked_on_me > 0 },
    { value: c.slipping, label: 'Milestones slipping', href: '#risks', alert: c.slipping > 0 },
    { value: c.waiting_on, label: 'Waiting on others', href: '#waiting', alert: false },
  ].map(t => el('a', {
    class: `tile${t.alert ? ' tile--alert' : ''}`,
    attrs: { href: t.href },
  }, [
    el('span', { class: 'tile__value', text: String(t.value) }),
    el('span', { class: 'tile__label', text: t.label }),
  ]));

  document.getElementById('tiles').replaceChildren(...tiles);

  const built = new Date(meta.generated);
  document.getElementById('built').textContent =
    `Built ${built.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })}` +
    ` from ${plural(projects.length, 'project file')}. A project is flagged stale after` +
    ` ${meta.stale_after_days} days without an update.`;
}

function wireFilters() {
  const buttons = [...document.querySelectorAll('.filter')];
  buttons.forEach(btn => btn.addEventListener('click', () => {
    buttons.forEach(b => {
      const on = b === btn;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-pressed', String(on));
    });
    const mode = btn.dataset.filter;
    for (const card of document.querySelectorAll('[data-card]')) {
      card.hidden = !(mode === 'all'
        || (mode === 'active' && card.dataset.active === 'true')
        || (mode === 'attention' && card.dataset.attention === 'true'));
    }
  }));
}

/** Three states: follow the OS, force light, force dark. Persisted locally. */
function wireTheme() {
  const order = ['', 'light', 'dark'];
  const label = { '': 'Theme: follow system', light: 'Theme: light', dark: 'Theme: dark' };
  const btn = document.getElementById('theme-toggle');

  const apply = value => {
    document.documentElement.dataset.theme = value;  // CSS swaps the icon to match
    btn.setAttribute('aria-label', `${label[value]}. Click to change.`);
    btn.title = label[value];
  };

  let current = '';
  try { current = localStorage.getItem('theme') || ''; } catch { /* private mode */ }
  apply(order.includes(current) ? current : '');

  btn.addEventListener('click', () => {
    const next = order[(order.indexOf(document.documentElement.dataset.theme) + 1) % 3];
    apply(next);
    try { localStorage.setItem('theme', next); } catch { /* ignore */ }
  });
}

/** A #codename link should open that card, not just scroll past a collapsed one. */
function openFromHash() {
  const id = decodeURIComponent(location.hash.slice(1));
  if (!id) return;
  const card = document.getElementById(id);
  if (card && card.tagName === 'DETAILS') {
    card.open = true;
    card.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
}

// ----------------------------------------------------------------------- boot

let DATA = null;

async function main() {
  try {
    const res = await fetch('data.json', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`data.json returned ${res.status}`);
    DATA = await res.json();
  } catch (err) {
    document.querySelector('main').replaceChildren(el('p', { class: 'notice' }, [
      document.createTextNode(
        'Could not load data.json. If you are viewing this from the filesystem, ' +
        'serve it instead: '),
      el('code', { text: 'make serve' }),
      document.createTextNode(` (${err.message})`),
    ]));
    document.getElementById('subtitle').textContent = 'Data unavailable';
    return;
  }

  renderHead(DATA.meta, DATA.projects);
  renderQueue(DATA.projects);
  renderCards(DATA.projects);
  wireFilters();
  openFromHash();
  window.addEventListener('hashchange', openFromHash);
}

wireTheme();
main();
