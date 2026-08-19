## What it does

`releasing` fixes the conventions for cutting a release: what the commit message looks like, what the release notes say and in what order, how the tag and the release title relate, what gets checked before an artifact ships, and where the reasoning behind a dependency or build-profile choice lives. Its defining constraint is that the release notes speak to the user about to run the software, never to the engineer who wrote it, so a benchmark number or an implementation detail belongs in the commit body or the docs, never in the notes.

## When to reach for it

Type `/releasing`, or the agent reaches for it automatically when the task fits.

| The situation | Reach for |
|---|---|
| Writing a commit message for anything going into history | `releasing` |
| Drafting release notes for a tagged version | `releasing` |
| Picking a release title, or checking the tag/title convention hasn't drifted | `releasing` |
| Bumping a version across a multi-manifest workspace | `releasing` |
| Building a binary meant to run on a Linux distribution you don't control | `releasing`, its portable-binaries file |
| Writing a deploy template or config file that ships to users | `releasing` |
| The shape of the code being released, not the release process around it | [codebase-design](../engineering/codebase-design.md) instead |

## The three artifacts

A release produces a commit, a set of release notes, and a built artifact, and each is judged by a different reader. The commit history is for the next engineer: short, imperative, why over how. The release notes are for the user: one or two lines per entry, in Keep a Changelog's fixed category order (Added, Changed, Deprecated, Removed, Fixed, Security), with no benchmark numbers or engineering rationale leaking in. The artifact is for whatever machine runs it, which is why it gets built from the tagged tree and verified as the packaged file itself, not the extracted contents.

## Build old, verify twice

The leading idea behind the portable-binaries file: glibc symbol compatibility only runs one direction, so a binary has to be built against an old glibc to run everywhere, and no amount of packaging afterward fixes a binary built too new. Verification follows the same build-old logic: check the glibc floor with `objdump`, run `ldd` inside a *different* distribution's image than the one used to build, and run the packaged artifact itself rather than the extracted tree, because the two paths differ and the packaged one is what people actually run.

## Common questions

**Why does my commit message keep turning into a paragraph?**

Because writing more feels like being thorough. The rule is a hard line: subject under 50 characters, and a body only when it says something the subject doesn't. If a body is explaining *how* the change works, that belongs in a code comment or the diff, not the commit.

**Why do the release title and the git tag look different?**

On purpose. The tag is always `vX.Y.Z`, because tooling downstream expects it. The title can take a friendlier, product-name form. Write the exact convention down once it's picked; an unwritten convention corrected once in conversation drifts back within days.

**Why build the release binary in a container instead of on my own machine?**

Because glibc symbol compatibility only runs one direction: a binary built against a newer glibc won't run against an older one, and there is no packaging trick that fixes that afterward. Building inside a container pinned to an old glibc is the only way to guarantee the floor.

**My build script grepped the output for "error" and still shipped a broken binary. Why?**

Because a compile error doesn't always contain the word the grep was looking for. Gate a release on the exit code, never on matching text in the output.

## It's working if

- A commit's subject line reads as a complete imperative sentence, with no body unless it says something new.
- The release notes have no benchmark numbers, no tables, and every entry is one or two lines the user can act on.
- The tag is always `vX.Y.Z`, and the title matches the project's convention exactly.
- Every place the version number lives got checked off, not just the ones that came to mind.
- The artifact was built from the tagged tree and verified as the packaged file itself, not the extracted contents.
- Every dependency and lint override in the manifest has a comment next to it saying why.

## Where it fits

`releasing` is a **reach-for-it-anytime standalone**, used at the point a change is ready to ship rather than as a step in a longer chain. Its neighbour is [diagnosing-bugs](../engineering/diagnosing-bugs.md) for when the release itself breaks in a way that needs a feedback loop, and [domain-modeling](../engineering/domain-modeling.md) for recording a release-shape decision as an ADR, whose "Rejected alternative" and "Consequences we accept" shape pairs well with the reasoning this skill asks you to write down. For the whole map, [ask-denny](../engineering/ask-denny.md) routes you.
