# Ship the skill set as a native Claude Code plugin; defer a native Codex plugin

These skills have always been installable via [skills.sh](https://skills.sh/ngodn/denny-skills) (`npx skills add ngodn/denny-skills`), which copies editable skill files into a user's project across Claude Code, Codex, and other Agent-Skills-standard harnesses. A recurring request is a **plug-and-play** distribution: subscribe to the set as a read-only, always-current bundle you don't edit, rather than a fork you own. That is exactly what native plugin systems provide.

We ship a native **Claude Code plugin** and, for now, **defer** a native **Codex plugin**. The split is forced by how each ecosystem's plugin manifest selects skills, against this repo's bucketed layout.

## The constraint: bucketed skills vs. single-path selection

Skills live in bucket folders under `skills/`. `engineering/` and `productivity/` are **promoted** (shipped); `misc/`, `personal/`, `in-progress/`, and `deprecated/` are **not**. A plugin must expose only the promoted set, which spans two of those bucket folders.

- **Claude Code**: `.claude-plugin/plugin.json` accepts `skills` as an **array of explicit skill-directory paths**. We list the promoted skills one by one, exclude everything else with zero ambiguity, and add `.claude-plugin/marketplace.json` so the repo is its own single-plugin marketplace. Verified end to end: `claude plugin validate . --strict` passes, and `marketplace add` → `install` resolves all promoted skills.

- **Codex**: `.codex-plugin/plugin.json` accepts `skills` only as a **single path string** (arrays are rejected with `missing or invalid plugin.json`), and Codex discovers `SKILL.md` files recursively under it. There is no way to name two bucket folders, or to curate a subset, from one path. Two escape hatches were tested and rejected:
  - Pointing at `./skills/` would also ship `deprecated/`, `in-progress/`, `personal/`, and `misc/`: retired, draft, and personal skills we deliberately don't promote.
  - A curated flat directory of **symlinks** into the buckets does not survive install: Codex copies the plugin tree into its cache and **drops symlinks**, so the skills arrive empty.

The only robust ways to give Codex a single promoted-only path are (a) **restructure** so `skills/` contains only promoted skills (moving the non-promoted buckets out: a large blast radius across `CLAUDE.md`, `scripts/link-skills.sh`, the bucket READMEs, and the local dev workflow that relies on `in-progress/` and `personal/`), or (b) **commit duplicate copies** of promoted skills into a flat directory (a sync burden and a second source of truth). Both are structural decisions, not something to bundle into shipping the Claude plugin. This is very likely the original, half-remembered reason a plugin wasn't shipped earlier: the manifest formats didn't cleanly express a curated subset of a bucketed repo.

## Decision

- Ship the **Claude Code plugin** now (`.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`), curated to the promoted set, as the headline v1.2 deliverable.
- Keep **skills.sh** as the universal installer. It already serves Codex and other harnesses today, so no Codex user is left without an install path.
- **Defer** the native Codex plugin until we decide between restructuring `skills/` to promoted-only vs. committing a generated flat copy. Revisit when Codex either supports a `skills` array / include-list or preserves symlinks on install.

## Invariants this creates

- Every promoted skill has an entry in `.claude-plugin/plugin.json`'s `skills` array (this already stood as a `CLAUDE.md` rule; it now also gates the plugin's contents).
- `.claude-plugin/plugin.json`'s `version` tracks `package.json`'s version. Bump both together on release. Claude uses the plugin `version` to decide when installed users see an update.

## Update, 2026-08-05

`denny-skills` was accepted into **Claude Code's official marketplace** (configured name `claude-plugins-official`, source repo `anthropics/claude-plugins-official`), which every Claude Code install has by default. `claude plugins install denny-skills` is now the documented route, and the `marketplace add` → `install` path above is superseded. The install wording lives in [.agents/install-block.md](../install-block.md).

The official listing points at this repo's git URL and reads `.claude-plugin/plugin.json` directly, so it does not depend on `.claude-plugin/marketplace.json`. That file is retained only as a fallback for installing the repo directly (an unreleased commit, or a fork).

Verified 2026-08-05, on Claude Code 2.1.222, against the live listing:

- `claude plugins install denny-skills` resolves with no marketplace added first, and reports `denny-skills@claude-plugins-official`.
- `claude plugin details denny-skills` then reports version 1.2.0 and loads the promoted skills.
- The listing's `source` is `{"source": "url", "url": "https://github.com/ngodn/denny-skills.git", "sha": …}`. The **sha is pinned**, so a release reaches installed users when that pin moves, not the moment we tag. At the time of writing the pin sits two commits behind `main`, which is why it lists 22 skills rather than the 24 in `plugin.json`.
- The in-session `/plugin install denny-skills` was **not** exercised. `/plugin` is unavailable in headless (`claude -p`) sessions. It runs the same resolver as the CLI, and the documented example form is `/plugin install <name>@claude-plugins-official`.

## Update, 2026-08-19 (fork)

This repo is now `ngodn/denny-skills`, a team-maintained fork. Everything above about the official marketplace listing and skills.sh describes the upstream repo and does not apply here: this fork is not listed anywhere. The default install route is a local clone plus `scripts/link-skills.sh` (Linux/macOS) or `scripts/link-skills.ps1` (Windows), and `.claude-plugin/marketplace.json` is retained so `/plugin marketplace add ngodn/denny-skills` works as an alternative. The plugin manifests are kept valid (`claude plugin validate . --strict`) so that route keeps working. The install wording lives in [.agents/install-block.md](../install-block.md).

## Update, 2026-08-19 (plugin withdrawn as an install route)

The plugin is no longer offered to users at all. Adding the marketplace works (verified against the public repo: `claude plugin marketplace add ngodn/denny-skills` resolves and lists `denny-skills`), but publishing it alongside the link scripts gives a reader two routes that install the same skills twice, and the scripts are the better one: they also install the global rules file, and they back up whatever they replace.

The manifests stay. `claude plugin validate . --strict` reads them, and that is what catches a skill added to a promoted bucket without a matching entry, or the reverse. Treat `.claude-plugin/` as a consistency check on the promoted set, not as a shipping vehicle. If the plugin is ever offered again, the wording goes in [.agents/install-block.md](../install-block.md) first.
