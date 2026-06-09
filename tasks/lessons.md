# Lessons Learned

A running log of mistakes, corrections, and patterns to avoid repeating.
Updated after every user correction.

---

<!-- Format:
## [short title]
**Mistake:** What went wrong.
**Rule:** What to do instead.
**Why:** The reason this matters.
-->

## Worktree agents need gh CLI in PATH
**Mistake:** Spawned 9 worktree agents expecting them to create PRs via `gh pr create`, but `gh` is only a Windows-native binary — not in Bash PATH inside worktrees. All agents reported `PR: none`.
**Rule:** Either install `gh` via `winget install GitHub.cli` first, or instruct agents to push the branch and provide the GitHub web URL for manual PR creation instead.
**Why:** Worktree agents run in a Linux-like Bash shell on Windows where Windows-native tools aren't on PATH.

## Global settings.json is the right place for worktree agent permissions
**Mistake:** Added permissions to project-level `.claude/settings.json` after agents were already spawned — they couldn't pick up the new settings mid-run.
**Rule:** Add tool permissions to `~/.claude/settings.json` (global) BEFORE spawning worktree agents. Project-level settings only help agents started after the file exists.
**Why:** Worktree agents inherit settings at spawn time; updating settings after launch has no effect on already-running agents.

## Parallel units that touch the same file cause merge conflicts
**Mistake:** Units 1, 2, 3 all independently created `models/api_key.py` and `schemas/api_key.py`. Units 5 and 6 both wrote to `routes/public.py`. This caused cascading merge conflicts across every PR.
**Rule:** When decomposing parallel work units, assign file ownership explicitly — one unit owns each file. If two units need the same file, make one depend on the other (sequential) or merge their work into one unit.
**Why:** Independent worktree agents can't coordinate file ownership, so overlapping file changes always produce conflicts that require manual resolution.

## ARRAY vs JSONB for list columns in SQLAlchemy
**Mistake:** Some agents used `Column(ARRAY(String))` while others used `Column(JSONB)` for the scopes field, causing conflicts.
**Rule:** Always use `JSONB` for array/list columns in this codebase. It's more flexible and consistent with all other array columns (e.g., `event_types`, `required_keywords`).
**Why:** JSONB is the established convention in this repo per CLAUDE.md.
