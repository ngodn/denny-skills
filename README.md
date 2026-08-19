# Denny Skills

Agent skills for real engineering, not vibe coding. This is the shared skill set for our team: install it once and every coding agent on the team works the same way, at the same speed, with the same habits.

Developing real applications is hard. Approaches like GSD, BMAD, and Spec-Kit try to help by owning the process. But while doing so, they take away your control and make bugs in the process hard to resolve.

These skills are designed to be small, easy to adapt, and composable. They work with any model. They're based on decades of engineering experience. Hack around with them. Propose changes. Enjoy.

The repo started as a fork of [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). We maintain it here; upstream is kept as a remote so improvements can be pulled in and merged when they land.

## Installation (2-minute setup)

One route: clone this repo and link the skills into your agent's skill directory. Every entry is a link back into the clone, so `git pull` is the whole update story. Works on Linux, macOS, and Windows, and on Claude Code, Codex, and any other Agent Skills-compatible harness.

### 1. Clone

```bash
git clone git@github.com:ngodn/denny-skills.git
cd denny-skills
```

### 2. Link the skills and install the global rules

One script does both: it links every skill into your agent's skill directory, and installs the team's global instructions file ([templates/CLAUDE.global.md](./templates/CLAUDE.global.md)) as `~/.claude/CLAUDE.md` (and `~/.codex/AGENTS.md` if you have Codex). That file is the other half of "same speed, same habits": writing style, when to ask, research-first, how to pick a language version, privilege escalation. It is copied, not linked, and the script never overwrites one you already have that differs; it tells you to merge instead. Machine-specific notes go in its last section, everything above is team-wide.

<details>
<summary><strong>Linux / macOS</strong></summary>

```bash
./scripts/link-skills.sh
```

Symlinks every skill into `~/.claude/skills` (Claude Code) and `~/.agents/skills` (Codex and others).

</details>

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
.\scripts\link-skills.ps1
```

If scripts are blocked on your machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\link-skills.ps1
```

Creates directory junctions into `%USERPROFILE%\.claude\skills` and `%USERPROFILE%\.agents\skills`. Junctions need no admin rights or Developer Mode.

</details>

<details>
<summary><strong>Claude Code plugin (alternative)</strong></summary>

The repo is also its own single-plugin marketplace, if you'd rather have a managed, read-only bundle:

```
/plugin marketplace add ngodn/denny-skills
/plugin install denny-skills@denny
```

Pick one route. Linking and the plugin together gives you every skill twice. The plugin route does not install the global rules file; copy it by hand (`cp -n templates/CLAUDE.global.md ~/.claude/CLAUDE.md`).

</details>

### 3. Update

```bash
git pull
```

Re-run the link script when a skill was added, removed, or renamed, or when the global rules template changed (it reports whether your copy is up to date).

### 4. Run `/setup-denny-skills`

In your agent, run it once per repo. It will:

- Ask you which issue tracker you want to use (GitHub, Linear, or local files)
- Ask you what labels you apply to tickets when you triage them (`/triage` uses labels)
- Ask you where you want to save any docs we create

### 5. Bam - you're ready to go.

## Keeping in sync with upstream

`origin` is this repo (`ngodn/denny-skills`). The original is wired up as `upstream`:

```bash
git remote add upstream git@github.com:mattpocock/skills.git   # once, if your clone lacks it
git fetch upstream
git merge upstream/main   # then resolve conflicts, keeping our names and install story
```

Our renames (`ask-denny`, `setup-denny-skills`, `denny-skills`) will conflict with upstream changes to the same files; resolve in favour of our names.

## Why These Skills Exist

These skills exist to fix common failure modes we see with Claude Code, Codex, and other coding agents.

### #1: The Agent Didn't Do What I Want

> "No-one knows exactly what they want"
>
> David Thomas & Andrew Hunt, [The Pragmatic Programmer](https://www.amazon.co.uk/Pragmatic-Programmer-Anniversary-Journey-Mastery/dp/B0833F1T3V)

**The Problem**. The most common failure mode in software development is misalignment. You think the dev knows what you want. Then you see what they've built - and you realize it didn't understand you at all.

This is just the same in the AI age. There is a communication gap between you and the agent. The fix for this is a **grilling session** - getting the agent to ask you detailed questions about what you're building.

**The Fix** is to use:

- [`/grill-me`](./skills/productivity/grill-me/SKILL.md) - for non-code uses
- [`/grill-with-docs`](./skills/engineering/grill-with-docs/SKILL.md) - same as [`/grill-me`](./skills/productivity/grill-me/SKILL.md), but adds more goodies (see below)

These are the most-used skills in the set. They help you align with the agent before you get started, and think deeply about the change you're making. Use them _every_ time you want to make a change.

### #2: The Agent Is Way Too Verbose

> With a ubiquitous language, conversations among developers and expressions of the code are all derived from the same domain model.
>
> Eric Evans, [Domain-Driven-Design](https://www.amazon.co.uk/Domain-Driven-Design-Tackling-Complexity-Software/dp/0321125215)

**The Problem**: At the start of a project, devs and the people they're building the software for (the domain experts) are usually speaking different languages.

The same tension shows up with agents. Agents are usually dropped into a project and asked to figure out the jargon as they go. So they use 20 words where 1 will do.

**The Fix** for this is a shared language. It's a document that helps agents decode the jargon used in the project.

<details>
<summary>
Example
</summary>

Here's an example from a course-video-manager project. Which one is easier to read?

- **BEFORE**: "There's a problem when a lesson inside a section of a course is made 'real' (i.e. given a spot in the file system)"
- **AFTER**: "There's a problem with the materialization cascade"

This concision pays off session after session.

</details>

This is built into [`/grill-with-docs`](./skills/engineering/grill-with-docs/SKILL.md). It's a grilling session, but that helps you build a shared language with the AI, and document hard-to-explain decisions in ADR's.

It's hard to explain how powerful this is. It might be the single coolest technique in this repo. Try it, and see.

> [!TIP]
> A shared language has many other benefits than reducing verbosity:
>
> - **Variables, functions and files are named consistently**, using the shared language
> - As a result, the **codebase is easier to navigate** for the agent
> - The agent also **spends fewer tokens on thinking**, because it has access to a more concise language

### #3: The Code Doesn't Work

> "Always take small, deliberate steps. The rate of feedback is your speed limit. Never take on a task that’s too big."
>
> David Thomas & Andrew Hunt, [The Pragmatic Programmer](https://www.amazon.co.uk/Pragmatic-Programmer-Anniversary-Journey-Mastery/dp/B0833F1T3V)

**The Problem**: Let's say that you and the agent are aligned on what to build. What happens when the agent _still_ produces crap?

It's time to look at your feedback loops. Without feedback on how the code it produces actually runs, the agent will be flying blind.

**The Fix**: You need the usual tranche of feedback loops: static types, browser access, and automated tests.

For automated tests, a red-green-refactor loop is critical. This is where the agent writes a failing test first, then fixes the test. This helps give the agent a consistent level of feedback that results in far better code.

The **[`/tdd`](./skills/engineering/tdd/SKILL.md) skill** slots into any project. It encourages red-green-refactor and gives the agent plenty of guidance on what makes good and bad tests.

For debugging, the **[`/diagnosing-bugs`](./skills/engineering/diagnosing-bugs/SKILL.md)** skill that wraps best debugging practices into a disciplined loop, gated phase by phase.

### #4: We Built A Ball Of Mud

> "Invest in the design of the system _every day_."
>
> Kent Beck, [Extreme Programming Explained](https://www.amazon.co.uk/Extreme-Programming-Explained-Embrace-Change/dp/0321278658)

> "The best modules are deep. They allow a lot of functionality to be accessed through a simple interface."
>
> John Ousterhout, [A Philosophy Of Software Design](https://www.amazon.co.uk/Philosophy-Software-Design-2nd/dp/173210221X)

**The Problem**: Most apps built with agents are complex and hard to change. Because agents can radically speed up coding, they also accelerate software entropy. Codebases get more complex at an unprecedented rate.

**The Fix** for this is a radical new approach to AI-powered development: caring about the design of the code.

This is built in to every layer of these skills:

- [`/to-spec`](./skills/engineering/to-spec/SKILL.md) quizzes you about which modules you're touching before creating a spec

And crucially, [`/improve-codebase-architecture`](./skills/engineering/improve-codebase-architecture/SKILL.md) surveys a codebase for deepening opportunities and hands you the candidates. Run it on your codebase once every few days. It is a survey, not a rescue: on a genuinely old codebase it will find real candidates, but it won't untangle the mud for you.

### Summary

Software engineering fundamentals matter more than ever. These skills condense those fundamentals into repeatable practices, so the whole team ships better apps at the same pace. Enjoy.

## Reference

These split on one axis: who can invoke them. **User-invoked** skills are reachable only when you type them (e.g. `/grill-me`); their job is to orchestrate. **Model-invoked** skills can be invoked by you _or_ reached for automatically by the agent when the task fits; they hold the reusable discipline. A user-invoked skill may invoke model-invoked skills, but never another user-invoked one.

### Engineering

Skills for daily code work.

**User-invoked**

- **[ask-denny](./skills/engineering/ask-denny/SKILL.md)**: Ask which skill or flow fits your situation. A router over the user-invoked skills in this repo.
- **[grill-with-docs](./skills/engineering/grill-with-docs/SKILL.md)**: Grilling session that also builds your project's domain model, sharpening terminology and updating `CONTEXT.md` and ADRs inline.
- **[triage](./skills/engineering/triage/SKILL.md)**: Move issues through a state machine of triage roles.
- **[improve-codebase-architecture](./skills/engineering/improve-codebase-architecture/SKILL.md)**: Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.
- **[setup-denny-skills](./skills/engineering/setup-denny-skills/SKILL.md)**: Configure this repo for the engineering skills (issue tracker, triage labels, domain doc layout). Run once per repo before using the other engineering skills.
- **[to-spec](./skills/engineering/to-spec/SKILL.md)**: Turn the current conversation into a spec and publish it to the issue tracker. No interview. Just synthesizes what you've already discussed.
- **[to-tickets](./skills/engineering/to-tickets/SKILL.md)**: Break any plan, spec, or conversation into a set of tracer-bullet tickets, each declaring its blocking edges: written as text in a local file, or as native blocking links on a real tracker.
- **[implement](./skills/engineering/implement/SKILL.md)**: Build the work described by a spec or set of tickets, driving `/tdd` at pre-agreed seams and closing out with `/code-review` before committing.
- **[wayfinder](./skills/engineering/wayfinder/SKILL.md)**: Plan a huge chunk of work, more than one agent session can hold, as a shared map of decision tickets on the issue tracker: resolve them one at a time until the way to the destination is clear.

**Model-invoked**

- **[office-docs](./skills/engineering/office-docs/SKILL.md)**: Generate Word, Excel and PowerPoint deliverables in Python: the generator package shape, python-docx and openpyxl patterns, and validating the data before anything is written.
- **[releasing](./skills/engineering/releasing/SKILL.md)**: Cut a release: commit and changelog conventions, the version-bump checklist, and building a portable Linux binary that runs somewhere other than the machine that built it.
- **[verifying-claims](./skills/engineering/verifying-claims/SKILL.md)**: Don't state it until you can show it: ground-truth sources, self-verifying tests, negative controls, and the two checks any written claim has to pass.
- **[testing-hypotheses](./skills/engineering/testing-hypotheses/SKILL.md)**: Decide whether an effect is real: permutation and holdout controls, the small-sample traps that invert at scale, and a verdict vocabulary that keeps settled questions closed.
- **[device42](./skills/engineering/device42/SKILL.md)**: Working reference for Device42 discovery and querying: per-protocol pre-check behaviour, port and privilege requirements, SNMP traps, and DOQL quirks.
- **[cmdb-sync](./skills/engineering/cmdb-sync/SKILL.md)**: Design an idempotent, resumable sync from an external inventory into a CMDB: identity over keys, reference resolution, relocation, and classify-and-route.
- **[jsm-assets](./skills/engineering/jsm-assets/SKILL.md)**: Working reference for Jira Service Management Assets as a data platform: the hard limits, the AQL and REST gotchas, and the visibility model the docs get wrong.
- **[forge-apps](./skills/engineering/forge-apps/SKILL.md)**: Build an Atlassian Forge app that does real work: the runtime limits, why async has no user context, storage that isn't the KV store, and the impersonation nuance.
- **[prototype](./skills/engineering/prototype/SKILL.md)**: Build a throwaway prototype to answer a design question: a single shareable HTML file for state/logic questions, or several radically different UI variations toggleable from one route.
- **[diagnosing-bugs](./skills/engineering/diagnosing-bugs/SKILL.md)**: Disciplined diagnosis loop for hard bugs and performance regressions: build a feedback loop that goes red on this bug → minimise → hypothesise → instrument → fix → regression-test.
- **[research](./skills/engineering/research/SKILL.md)**: Investigate a question against high-trust primary sources and capture the findings as a cited Markdown file in the repo, run as a background agent.
- **[tdd](./skills/engineering/tdd/SKILL.md)**: Test-driven development with a red-green-refactor loop. Builds features or fixes bugs one vertical slice at a time.
- **[domain-modeling](./skills/engineering/domain-modeling/SKILL.md)**: Actively build and sharpen a project's domain model: challenge terms against the glossary, stress-test with edge-case scenarios, and update `CONTEXT.md` and ADRs inline.
- **[codebase-design](./skills/engineering/codebase-design/SKILL.md)**: Shared discipline and vocabulary for designing deep modules: a lot of behaviour behind a small interface, placed at a clean seam, testable through that interface.
- **[acid-transactions](./skills/engineering/acid-transactions/SKILL.md)**: Reference and review checklist for transactional integrity: the four ACID promises, the anomalies, isolation levels per engine, locking and the atomic guarded UPDATE, and what replaces ACID across services (saga, outbox, idempotency).
- **[code-review](./skills/engineering/code-review/SKILL.md)**: Two-axis review of the diff since a fixed point: **Standards** (does it follow the repo's coding standards, plus a Fowler smell baseline?) and **Spec** (does it faithfully implement the originating issue/spec?), run as parallel sub-agents so neither pollutes the other.
- **[resolving-merge-conflicts](./skills/engineering/resolving-merge-conflicts/SKILL.md)**: Work through an in-progress git merge or rebase conflict hunk by hunk, resolving by intent traced to each side's primary source, then finish the operation. Never `--abort`.
- **[wizard](./skills/engineering/wizard/SKILL.md)**: Generate an interactive bash wizard that walks a human through steps only they can perform: provisioning infrastructure, setting up credentials or CI secrets, walking an unfamiliar third-party dashboard, or running a one-off migration or cutover.

### Productivity

General workflow tools, not code-specific.

**User-invoked**

- **[grill-me](./skills/productivity/grill-me/SKILL.md)**: Get relentlessly interviewed about a plan or design until every branch of the design tree is resolved.
- **[handoff](./skills/productivity/handoff/SKILL.md)**: Compact the current conversation into a handoff document so another agent can continue the work.
- **[teach](./skills/productivity/teach/SKILL.md)**: Teach the user a new skill or concept over multiple sessions, using the current directory as a stateful teaching workspace.
- **[to-questionnaire](./skills/productivity/to-questionnaire/SKILL.md)**: Turn a decision you can't answer alone into a Markdown questionnaire for the one person who can: filled in async, or together over a meeting. It grills you about the send (who it's for, what you need back), not the subject.
- **[wait-what](./skills/productivity/wait-what/SKILL.md)**: Fire this the moment a message doesn't land. The agent re-pitches it with the context you're missing, in plain English, using your `CONTEXT.md` vocabulary.

**Model-invoked**

- **[client-deliverables](./skills/productivity/client-deliverables/SKILL.md)**: The editorial discipline for anything that leaves the building: customer-facing and internal stay separate files, scope facts are sourced, and the pre-send sweep.
- **[slide-decks](./skills/productivity/slide-decks/SKILL.md)**: Produce a deck through an AI design tool or by editing the pptx directly, with the slide-spec rule that decides which of those two outputs you get.
- **[diagrams](./skills/productivity/diagrams/SKILL.md)**: Architecture and network diagrams in mermaid: the render pipeline, the styling conventions that carry meaning, and when a table beats a picture.
- **[research-log](./skills/productivity/research-log/SKILL.md)**: Keep a long, multi-session investigation from re-litigating settled ground, with a status doc and an index that records what was refuted and why.
- **[grilling](./skills/productivity/grilling/SKILL.md)**: Interview the user relentlessly about a plan, decision, or idea until every branch of the design tree is resolved. The reusable interview primitive behind `grill-me`, `grill-with-docs`, `triage`, `wayfinder` and `improve-codebase-architecture`.
- **[writing-for-agents](./skills/productivity/writing-for-agents/SKILL.md)**: Writing documents for agents: skills, AGENTS.md/CLAUDE.md, and any doc an agent reaches by a pointer.
