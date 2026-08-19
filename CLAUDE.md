Skills are organized into bucket folders under `skills/`:

- `engineering/`: daily code work
- `productivity/`: daily non-code workflow tools
- `misc/`: kept around but rarely used, not promoted
- `in-progress/`: beta: public on purpose, feedback wanted, not shipped in the plugin
- `deprecated/`: no longer used

Every skill in `engineering/` or `productivity/` (the **promoted** buckets) must have a reference in the top-level `README.md` and an entry in `.claude-plugin/plugin.json`'s `skills` array (the Claude Code plugin ships exactly the promoted set). Skills in `misc/`, `in-progress/`, and `deprecated/` must not appear in either.

Install commands are copied verbatim from [.agents/install-block.md](./.agents/install-block.md). The default route is a local clone plus `scripts/link-skills.sh` (Linux/macOS) or `scripts/link-skills.ps1` (Windows). `.claude-plugin/marketplace.json` makes the repo its own single-plugin marketplace as an alternative route. Run `claude plugin validate . --strict` after touching either manifest. Why a Claude plugin but not (yet) a Codex one lives in [.agents/adr/0002-ship-as-a-claude-code-plugin.md](./.agents/adr/0002-ship-as-a-claude-code-plugin.md).

This repo is a fork of `mattpocock/skills`, kept as the `upstream` git remote; `origin` is `ngodn/denny-skills`. When merging upstream, keep our names (`ask-denny`, `setup-denny-skills`, `denny-skills`) and our install story.

Each skill entry in the top-level `README.md` must link the skill name to its `SKILL.md`.

Each bucket folder has a `README.md` that lists every skill in the bucket with a one-line description, with the skill name linked to its `SKILL.md`. The promoted buckets' `README.md`s and the top-level `README.md` group entries into **User-invoked** and **Model-invoked**; non-promoted bucket `README.md`s (`misc/`, `in-progress/`) use a flat list.

Skills in `engineering/` and `productivity/` also have a human-facing docs page at `docs/<bucket>/<skill-name>.md` (the docs tree mirrors those two bucket folders under `skills/`). The pages are read from the repo itself (GitHub or a local clone), so links inside them are repo-relative. When you add, rename, or change the behaviour of a skill in `engineering/` or `productivity/`, create or re-sync its docs page following [.agents/writing-docs.md](./.agents/writing-docs.md). A finished page carries four sections (**What it does**, **When to reach for it**, **Common questions**, **It's working if**), and `writing-docs.md` holds the template, the section order, and where to hunt for the questions. Skills in the non-promoted buckets (`misc/`, `in-progress/`, `deprecated/`) get **no** docs page.

Every `SKILL.md` is either user-invoked (`disable-model-invocation: true` plus `policy.allow_implicit_invocation: false` in `agents/openai.yaml`, reachable only by the human) or model-invoked (model- or user-reachable). See [.agents/invocation.md](./.agents/invocation.md).

[`ask-denny`](./skills/engineering/ask-denny/SKILL.md) is the router that maps every user-reachable skill and how they relate. The same trigger that re-syncs a docs page applies to it: whenever you add, rename, remove, or change how a user-reachable skill fits the flows, re-read `ask-denny`'s `SKILL.md` and update it so the map stays accurate. A new skill it never mentions, or a stale one it still routes to, is a router that lies.

[templates/CLAUDE.global.md](./templates/CLAUDE.global.md) is the team's shareable global instructions file; the link scripts copy it to `~/.claude/CLAUDE.md` (and `~/.codex/AGENTS.md` for Codex) without overwriting a differing copy. It holds team-wide working rules, written to adapt to whatever OS, version manager, and tools the machine has; machine-specific notes belong only in its last section. Keep it free of em dashes and personal paths. When a rule there points at a skill (as the ACID entry does), keep the two in sync.

Scratch work for whatever task is in flight goes in `.scratchpad/`, which is gitignored. It regularly holds material mined from other repositories or chat history, and this repo has a public remote, so nothing in there is safe to publish without a human reading it first. `backup/` is gitignored for the same reason: it holds copies of the installing user's own machine config.

To (re)link every skill into the local harness skill directories (`~/.claude/skills`, `~/.agents/skills`), run `scripts/link-skills.sh` (Linux/macOS) or `scripts/link-skills.ps1` (Windows). Each entry is a link into this repo, so a `git pull` keeps installed skills current; re-run the script after adding, removing, or renaming a skill. Anything the installer replaces (a real skill directory someone wrote themselves, a differing global rules file) is copied into `backup/<timestamp>/` first and the path is printed on success. `--list-backups` shows what is there and `--restore <id>` puts one back.
