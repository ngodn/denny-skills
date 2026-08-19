# Engineering

Skills for daily code work.

## User-invoked

Reachable only when you type them (Claude Code: `disable-model-invocation: true`; Codex: `policy.allow_implicit_invocation: false` in `agents/openai.yaml`).

- **[ask-denny](./ask-denny/SKILL.md)**: Ask which skill or flow fits your situation. A router over the user-invoked skills in this repo.
- **[grill-with-docs](./grill-with-docs/SKILL.md)**: Grilling session that also builds your project's domain model, sharpening terminology and updating `CONTEXT.md` and ADRs inline.
- **[triage](./triage/SKILL.md)**: Move issues through a state machine of triage roles.
- **[improve-codebase-architecture](./improve-codebase-architecture/SKILL.md)**: Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick.
- **[setup-denny-skills](./setup-denny-skills/SKILL.md)**: Configure this repo for the engineering skills (issue tracker, triage labels, domain doc layout). Run once per repo.
- **[to-spec](./to-spec/SKILL.md)**: Turn the current conversation into a spec and publish it to the issue tracker.
- **[to-tickets](./to-tickets/SKILL.md)**: Break any plan, spec, or conversation into a set of tracer-bullet tickets, each declaring its blocking edges: text in a local file, or native blocking links on a real tracker.
- **[implement](./implement/SKILL.md)**: Build the work described by a spec or set of tickets, driving `/tdd` at pre-agreed seams and closing out with `/code-review` before committing.
- **[wayfinder](./wayfinder/SKILL.md)**: Plan a huge chunk of work, more than one agent session can hold, as a shared map of decision tickets on the issue tracker, resolved one at a time until the way to the destination is clear.

## Model-invoked

Model- or user-reachable (rich trigger phrasing so the model can reach for them).

- **[prototype](./prototype/SKILL.md)**: Build a throwaway prototype to answer a design question: a single shareable HTML file for state/logic, or several toggleable UI variations.
- **[diagnosing-bugs](./diagnosing-bugs/SKILL.md)**: Disciplined diagnosis loop for hard bugs and performance regressions: build a feedback loop that goes red on this bug → minimise → hypothesise → instrument → fix → regression-test.
- **[research](./research/SKILL.md)**: Investigate a question against high-trust primary sources and capture the findings as a cited Markdown file in the repo, run as a background agent.
- **[tdd](./tdd/SKILL.md)**: Test-driven development with a red-green-refactor loop. Builds features or fixes bugs one vertical slice at a time.
- **[domain-modeling](./domain-modeling/SKILL.md)**: Actively build and sharpen a project's domain model: challenge terms, stress-test with scenarios, update `CONTEXT.md` and ADRs inline.
- **[codebase-design](./codebase-design/SKILL.md)**: Shared discipline and vocabulary for designing deep modules: small interfaces, clean seams, testable through the interface.
- **[acid-transactions](./acid-transactions/SKILL.md)**: Reference and review checklist for transactional integrity: the four ACID promises, the anomalies, isolation levels per engine, locking and the atomic guarded UPDATE, and what replaces ACID across services (saga, outbox, idempotency).
- **[code-review](./code-review/SKILL.md)**: Two-axis review of the diff since a fixed point: **Standards** (does it follow the repo's coding standards, plus a Fowler smell baseline?) and **Spec** (does it faithfully implement the originating issue/spec?), run as parallel sub-agents.
- **[resolving-merge-conflicts](./resolving-merge-conflicts/SKILL.md)**: Work through an in-progress git merge or rebase conflict hunk by hunk, resolving by intent traced to each side's primary source, then finish the operation, never `--abort`.
- **[wizard](./wizard/SKILL.md)**: Generate an interactive bash wizard that walks a human through steps only they can perform: provisioning infrastructure, setting up credentials or CI secrets, walking an unfamiliar third-party dashboard, or running a one-off migration or cutover.
- **[office-docs](./office-docs/SKILL.md)**: Generate Word, Excel and PowerPoint deliverables in Python: the generator package shape, python-docx and openpyxl patterns, and validating the data before anything is written.
- **[releasing](./releasing/SKILL.md)**: Cut a release: commit and changelog conventions, the version-bump checklist, and building a portable Linux binary that runs somewhere other than the machine that built it.
- **[verifying-claims](./verifying-claims/SKILL.md)**: Don't state it until you can show it: ground-truth sources, self-verifying tests, negative controls, and the two checks any written claim has to pass.
- **[testing-hypotheses](./testing-hypotheses/SKILL.md)**: Decide whether an effect is real: permutation and holdout controls, the small-sample traps that invert at scale, and a verdict vocabulary that keeps settled questions closed.
- **[device42](./device42/SKILL.md)**: Working reference for Device42 discovery and querying: per-protocol pre-check behaviour, port and privilege requirements, SNMP traps, and DOQL quirks.
- **[cmdb-sync](./cmdb-sync/SKILL.md)**: Design an idempotent, resumable sync from an external inventory into a CMDB: identity over keys, reference resolution, relocation, and classify-and-route.
- **[jsm-assets](./jsm-assets/SKILL.md)**: Working reference for Jira Service Management Assets as a data platform: the hard limits, the AQL and REST gotchas, and the visibility model the docs get wrong.
- **[forge-apps](./forge-apps/SKILL.md)**: Build an Atlassian Forge app that does real work: the runtime limits, why async has no user context, storage that isn't the KV store, and the impersonation nuance.
