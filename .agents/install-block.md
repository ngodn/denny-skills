# The canonical install block

One install story, one wording. `README.md`, `.changeset/*`, and every page under `docs/` must say **this** and nothing else. Change it here first, then propagate.

The install route is a **local clone plus link script**. There is no marketplace listing and no skills.sh registry entry for this repo: the team clones `ngodn/denny-skills` and links the skills into each harness's skill directory. Every entry is a link back into the clone, so `git pull` is the whole update story.

## All harnesses, all OSes

<canonical-block name="clone">

```bash
git clone git@github.com:ngodn/denny-skills.git
cd denny-skills
```

</canonical-block>

<canonical-block name="link-unix">

```bash
./scripts/link-skills.sh
```

</canonical-block>

<canonical-block name="link-windows">

```powershell
.\scripts\link-skills.ps1
```

</canonical-block>

Both scripts write into `~/.claude/skills` (Claude Code) and `~/.agents/skills` (Codex and other Agent Skills-compatible harnesses). Linux and macOS get symlinks; Windows gets directory junctions, which need no admin rights or Developer Mode. Re-run after a skill is added, removed, or renamed; a plain `git pull` covers every other change.

## The global rules file

<canonical-block name="global-rules">

```bash
cp -n templates/CLAUDE.global.md ~/.claude/CLAUDE.md
```

</canonical-block>

`templates/CLAUDE.global.md` is the team's global instructions file (writing style, ask when in doubt, research first, language and version, privilege escalation, reading past sessions). **The link scripts install it** as `~/.claude/CLAUDE.md` (and `~/.codex/AGENTS.md` when `~/.codex` exists), copied rather than linked because the last section is machine-specific, and never overwriting a copy that differs. The manual `cp -n` above is only for the plugin route, which does not run the scripts.

## Claude Code plugin (alternative, not the default)

`.claude-plugin/marketplace.json` makes the repo its own single-plugin marketplace:

<canonical-block name="claude-code-plugin">

```
/plugin marketplace add ngodn/denny-skills
/plugin install denny-skills@denny
```

</canonical-block>

It gives a managed, read-only bundle. Linking and the plugin together leave the user with every skill twice: always say "pick one".

## Not the install story

`docs/` pages carry no install commands at all; they link back to `README.md` where one is needed. The upstream repo's routes (Claude Code official marketplace, skills.sh) belong to `mattpocock/skills`, not to this fork. Why the plugin exists but is not the default lives in [adr/0002-ship-as-a-claude-code-plugin.md](./adr/0002-ship-as-a-claude-code-plugin.md).
