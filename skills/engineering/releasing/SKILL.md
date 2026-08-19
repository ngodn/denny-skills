---
name: releasing
description: Reference and checklist for cutting a release. Use when the user is writing a commit message, drafting release notes, naming or tagging a release, bumping a version across a workspace, building a portable Linux binary for distribution, or writing a deployment template that ships to users.
---

# Releasing

Cutting a release produces three artifacts that get judged separately: the commit history, the release notes, and the thing you hand to users. Keep them separate. Engineering rationale belongs in the commit body and the docs, never in the release notes, and the release notes speak to the user about to run the software, not to the engineer who wrote it.

## Commit messages

- Subject line under about 50 characters, imperative mood, capitalised, no trailing period: `Bump version to 1.0.2`, `Fix bitrate collapse on reconnect`.
- Add a body only when it says something the subject doesn't. Wrap it, and explain *why* the change happened, not *how* it works, the diff already shows that.
- The failure mode to avoid: a long prose body under a headline-style subject. If you catch yourself writing paragraphs, cut it down to the subject line plus, at most, a few short bullets on the why.

## Release notes

Keep a Changelog style. Use `###` headings only for the categories that actually apply, always in this fixed order: Added, Changed, Deprecated, Removed, Fixed, Security.

- One or two lines per entry, active voice, present tense, phrased for the user rather than the implementation: "Touch lands where you aim on windows that draw their own decorations," not "changed hit-testing to use render_location."
- No tables, no benchmarks, no engineering rationale. Those belong in the commit body and in the docs.
- Add `### Upgrading` only when the user must actually do something (a hard refresh, a config migration). Omit it otherwise.
- A withdrawn or superseded release gets a `>` blockquote warning at the top, linking to its replacement. That warning must survive any later rewrite of the notes.

## Release title and tag

The tag and the title are allowed to differ, on purpose. The tag is always `vX.Y.Z`, because `git describe` and every tool downstream expects it; the title can take a friendlier, product-name form.

```bash
gh release create vX.Y.Z <asset> --title "<Product> X.Y.Z" --notes-file <file>
```

Whatever the title convention is, make it exact and write it down somewhere that loads automatically (this skill, a `CONTRIBUTING.md`, a project doc). A convention that has only ever been corrected in conversation drifts back within days.

## Tag and build provenance

- **Annotated tags only** (`git tag -a`, never a lightweight tag). An annotated tag carries a date, author, and message, and `git describe` prefers it over a lightweight one.
- **Build the artifact from the tagged tree, not the working directory.** A payload that bundles a README or an installer, built one commit early, ships docs that don't match the code sitting next to them.

## Version bump checklist

A version number usually lives in more places than anyone remembers. Enumerate them for the project once, then check every one on every release rather than relying on memory:

- [ ] Every crate manifest (`Cargo.toml`) that carries its own version, across the workspace.
- [ ] Every package manifest (`package.json`) that carries its own version.
- [ ] The lockfile, refreshed for any workspace member whose version it records. (A lockfile that only records external dependency versions, not an internal member's own version, doesn't need touching for this.)
- [ ] Any other place the version is echoed: a `--version` flag's constant, a doc header, an installer script.

## Verify before publishing

Check the **exit code**, not the output text, when a build gates a release. A compile error doesn't always print the word a grep-based check is looking for, and that kind of check can read as a green build when the build actually failed.

## Document the reasoning next to the decision

Dependency choices, lint rules, and build-profile settings all drift out of memory the same way a version number does. Put the "why" as a comment right next to the setting, in terms of the actual hot path or constraint it protects, not generic advice:

```toml
# ffmpeg-next over nvidia-video-codec-sdk: that crate's cudarc dependency
# hard-panics on older CUDA versions this project still supports.
ffmpeg-next = "..."

# warn, not allow: float equality bugs here are per-frame, per-surface,
# and only show up under load.
float_cmp = "warn"
```

Do the same for a rejected alternative: name it and say why it lost, so nobody proposes it again in six months.

## Portable Linux binaries

Building a binary that runs across distributions and shipping it safely is its own discipline: which glibc floor to build against, what to build from source, how to verify the artifact rather than the code, and what never gets bundled. See [PORTABLE-LINUX-BINARIES.md](PORTABLE-LINUX-BINARIES.md).
