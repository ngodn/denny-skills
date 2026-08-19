# Productivity

General workflow tools, not code-specific.

## User-invoked

Reachable only when you type them (Claude Code: `disable-model-invocation: true`; Codex: `policy.allow_implicit_invocation: false` in `agents/openai.yaml`).

- **[grill-me](./grill-me/SKILL.md)**: Get relentlessly interviewed about a plan or design until every branch of the design tree is resolved.
- **[handoff](./handoff/SKILL.md)**: Compact the current conversation into a handoff document so another agent can continue the work.
- **[teach](./teach/SKILL.md)**: Teach the user a new skill or concept over multiple sessions, using the current directory as a stateful teaching workspace.
- **[to-questionnaire](./to-questionnaire/SKILL.md)**: Turn a decision you can't answer alone into a Markdown questionnaire for the one person who can, filled in async, or together over a meeting.
- **[wait-what](./wait-what/SKILL.md)**: Fire this the moment a message doesn't land. The agent re-pitches it with the context you're missing, in plain English, using your `CONTEXT.md` vocabulary.

## Model-invoked

Model- or user-reachable (rich trigger phrasing so the model can reach for them).

- **[grilling](./grilling/SKILL.md)**: Interview the user relentlessly about a plan, decision, or idea until every branch of the design tree is resolved.
- **[writing-for-agents](./writing-for-agents/SKILL.md)**: Writing documents for agents: skills, AGENTS.md/CLAUDE.md, and any doc an agent reaches by a pointer.
- **[client-deliverables](./client-deliverables/SKILL.md)**: The editorial discipline for anything that leaves the building: customer-facing and internal stay separate files, scope facts are sourced, and the pre-send sweep.
- **[slide-decks](./slide-decks/SKILL.md)**: Produce a deck through an AI design tool or by editing the pptx directly, with the slide-spec rule that decides which of those two outputs you get.
- **[diagrams](./diagrams/SKILL.md)**: Architecture and network diagrams in mermaid: the render pipeline, the styling conventions that carry meaning, and when a table beats a picture.
- **[research-log](./research-log/SKILL.md)**: Keep a long, multi-session investigation from re-litigating settled ground, with a status doc and an index that records what was refuted and why.
