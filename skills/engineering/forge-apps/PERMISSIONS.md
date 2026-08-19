# A granular permission layer on coarse native roles

Depth on the permission layer named in [SKILL.md](SKILL.md). The platform's own roles are coarse (a small fixed set of native roles per schema); an app that needs row-level or attribute-level control has to build its own layer on top and enforce it itself, because the platform gives it nothing finer to delegate to.

## The grant model

A grant is: **principal** (a user or a group) x **function** (an ordered capability, typically read < write < delete < manage) x **scope** (schema, object type, object, attribute, or a value-level condition).

Evaluation is deny-by-default, then, in order:

1. **Most-specific scope wins.** A grant on one object beats a grant on its object type; a grant on an object type beats a grant on the schema.
2. **At equal specificity, explicit deny beats allow.** A deny grant at the same scope as an allow grant wins, so a deny can carve an exception out of a broader allow without needing to restructure the broader grant.
3. **At equal specificity, user beats group.** A grant made directly to a user overrides a grant made to a group the user belongs to, at the same scope.

`manage` at a given scope grants both structure-editing rights and the right to make further grants at or below that scope, so `manage` at the schema level is effectively schema admin, while `manage` at one object type is scoped to that type alone.

## Enforcement

Centralise enforcement in one authorise call, invoked from every single resolver that touches protected data. Client-side hiding of denied actions is a courtesy for the user experience; it is never the actual control, and treating it as one leaves every denied action reachable by anyone who can call the resolver directly.

Two asymmetric rules on top of the grant model, both server-side:

- **Read-denied attributes are stripped from the response before it leaves the resolver.** The client never even receives the value it is not allowed to see.
- **Write-denied attributes are preserved rather than overwritten on save,** even if a client-side bug or a malicious client sends a value for them in the payload. A write-denied field silently reverting to its previous value on save is the correct behaviour, not a bug to fix by trusting the payload more.

## Testing

Permission precedence is exactly the kind of logic that looks obviously correct and then silently breaks on refactor, because the interaction between scope specificity, deny-versus-allow, and user-versus-group is easy to get right for the cases you think to test and wrong for the ones you don't. Give it an exhaustive table-driven test matrix of its own (every combination of scope specificity, allow/deny, and user/group that can actually occur), separate from ordinary unit tests, and re-run it on every change to the authorise function.
