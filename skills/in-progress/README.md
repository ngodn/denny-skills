# In Progress

Beta. These skills are public on purpose: try them and tell the team what breaks. They're excluded from the top-level README until they graduate to a stable bucket, they get no docs pages, and they can change or disappear without warning.

The link scripts (`scripts/link-skills.sh`, `scripts/link-skills.ps1`) install these alongside everything else, so there is nothing extra to do to try one.

- **[loop-me](./loop-me/SKILL.md)**: Grill yourself into implementable workflow specs over multiple sessions, using the current directory as a stateful workspace. User-invoked.
- **[writing-beats](./writing-beats/SKILL.md)**: Shape an article as a journey of beats, choose-your-own-adventure style. Pick a starting beat, write only that beat, then pivot to the next, until the article reaches a natural end.
- **[writing-fragments](./writing-fragments/SKILL.md)**: Grilling session that mines you for fragments, heterogeneous nuggets of writing, and appends them to a single document as raw material for a future article.
- **[writing-shape](./writing-shape/SKILL.md)**: Take a markdown file of raw material and shape it into an article paragraph by paragraph, arguing format choices at each step.
- **[claude-handoff](./claude-handoff/SKILL.md)**: Hand the current conversation off to a fresh background agent that picks up the work immediately, seeded with a handoff summary via `claude --bg`. User-invoked.
- **[setup-ts-deep-modules](./setup-ts-deep-modules/SKILL.md)**: Wire dependency-cruiser into a TypeScript repo so each package is a deep module: implementation hidden in subfolders, reachable only through its entry-point files, tests exercising it through those. User-invoked.
- **[app-foundations](./app-foundations/SKILL.md)**: Rules, traps and review checklists for the foundations of an app and its backend: offline-first, frontend, API and backend logic, database and storage, auth and permissions, security and row-level security, rate limiting, caching, logging and audit, availability and recovery.
- **[offline-first-sync](./offline-first-sync/SKILL.md)**: Design offline writes that sync later: a command log with a transaction envelope, push/pull protocol, per-operation conflict rules, an exception workbench instead of overwrites, sync status UX, and offline and clock-skew tests.
- **[rust-mobile-core](./rust-mobile-core/SKILL.md)**: Share one Rust core between a server and Android or iOS through UniFFI: crate split, FFI surface design, keystore callbacks, encrypted SQLite in the core, cargo-ndk, Gradle and 16 KB page alignment.
