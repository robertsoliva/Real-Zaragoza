# Skill: contribute-text

## Purpose

Governs every write to this repo — whether creating a new wiki page, editing an existing one, updating `next-actions.md`, or touching any root file. The skill keeps content disciplined, the log append complete, and the index current before any commit is made.

> **Transport boundary:** never inline a `git` command until Step 5 (Commit). All content work happens first. This boundary exists so the transport layer (git) can later be swapped for a knowledge-graph API without touching the discipline.

---

## Step 1 — Classify & route

Determine the target surface before writing anything:

| Request type | Target surface | Template |
|---|---|---|
| New wiki topic | `wiki/<topic>.md` | `.claude/templates/wiki-page.md` |
| Edit existing wiki page | `wiki/<existing>.md` | (in-place; update status date) |
| Backlog / task / idea | `next-actions.md` (root) | none — follow existing format |
| Club convention or meta | `.claude/CLAUDE.md` | (in-place) |
| Other root file | root or as indicated | none |

Rules:
- One topic per wiki file. If a request touches two independent topics, route each to its own file.
- If a topic doesn't have a page yet, create one — don't append it to a catch-all.
- Never edit `README.md` (frozen — see `.claude/CLAUDE.md`).

---

## Step 2 — Apply format

### New wiki page

Copy `.claude/templates/wiki-page.md`, fill every section. Follow the CLAUDE.md conventions:
- Status line with today's date.
- Every factual claim must be traceable; uncertain items go in **Open items**, not stated as fact.
- Prefer Spanish-language sources for Aragonese/club-specific news; write content in English.
- End with a `## Sources` section of markdown links.

### Existing wiki page

- Update the `last updated` date in the `> **Status:**` line.
- Edit in place — do not append stale info next to new info; replace it.
- If a cross-reference needs updating, fix it in the same pass.

### Cross-references

Always use repo-relative paths — never absolute filesystem paths:
- Wiki page → wiki page: `./other-page.md`
- Root file → wiki: `wiki/other-page.md`
- `.claude/` → wiki: `../wiki/other-page.md`

---

## Step 3 — Update `wiki/index.md`

After any wiki change (new page or edit), open `wiki/index.md` and:
- Add new pages under the correct section with a one-line description.
- Bump the **Last updated** column for any touched page to `YYYY-MM` (current month).

---

## Step 4 — Append to `wiki/log.md`

Append exactly one line per change set to `wiki/log.md` using the format from `.claude/templates/log-entry.md`:

```
[YYYY-MM-DD]||One-line-summary with evidence
```

Log the substance: what changed and why (a fact updated, a new page, a transfer confirmed). Not "edited squad.md" — "Francho Serrano departure confirmed in squad.md (source: official club announcement 2026-06-XX)."

---

## Step 5 — Pre-commit checklist

Before running any `git` command, verify all of the following:

- [ ] Wiki edit present and correctly formatted (status date updated in the `> **Status:**` line).
- [ ] `wiki/index.md` updated: correct **Last updated** date for every touched page; new pages added.
- [ ] `wiki/log.md` has a new appended entry for this change set.
- [ ] All cross-references use repo-relative paths (no `file://` or `/Users/...` paths anywhere).

If any check fails, fix it before proceeding to git.

---

## Step 6 — Commit

### Branch naming

```
{type}/Zaragoza-{n}-short-description
```

Types: `feat`, `fix`, `maintenance`, `docs`  
`n` = next available sequence number — check existing local branches and recent commit messages to find it.

### Commit message

```
{type}(Zaragoza-{n}): Description
```

### Pull request

- Assign to **robertsoliva**.
- Title matches the commit message subject.
- Body: what changed, why, which sources were consulted.
- **Never push without explicit go-ahead from robertsoliva in the current conversation — a prior approval does not carry over.**
