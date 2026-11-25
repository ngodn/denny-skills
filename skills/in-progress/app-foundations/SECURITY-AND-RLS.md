# Security and row-level security

## Row-level security (PostgreSQL)

Row-level security (RLS) makes the database filter rows per role or per session, so a forgotten `WHERE tenant_id = ...` in one query does not leak another tenant's data. Facts that decide whether it actually protects you (from https://www.postgresql.org/docs/current/ddl-rowsecurity.html):

- With RLS enabled and **no policy**, the default is deny: no rows are visible or modifiable.
- **Superusers and roles with `BYPASSRLS` always bypass it. Table owners bypass it too** unless the table has `FORCE ROW LEVEL SECURITY`. So the app must not connect as the table owner, or the table must be forced.
- `USING` filters which existing rows a command sees or targets; `WITH CHECK` validates rows being written. Without `WITH CHECK`, the `USING` expression applies to new rows as well. Rows failing `USING` are silently skipped (an `UPDATE` reports 0 rows); rows failing `WITH CHECK` raise an error.
- **Unique, primary key and foreign key checks bypass RLS.** A unique violation can reveal that a row exists in another tenant. Design keys so that does not leak anything (tenant-scoped uniqueness, opaque ids).
- `TRUNCATE` is not subject to RLS.
- Policies with subqueries can race under Read Committed; the docs describe the countermeasures.

How to wire it:

1. App connects as a role that owns nothing and has no `BYPASSRLS`. Migrations run as a different role.
2. Set the caller context per transaction (`SET LOCAL app.tenant_id = ...` or a similar setting), read it in policies with `current_setting`. Use `SET LOCAL` so the value cannot leak to the next request on a pooled connection.
3. Enable and force RLS on every tenant table; write explicit policies per command.
4. Test it: a test that queries as tenant A must see zero rows of tenant B, and an insert for tenant B as tenant A must fail.

RLS is a backstop, not the permission model. Authorization still happens in the app (see AUTH-AND-PERMISSIONS.md).

## Secrets

- No secrets in code, images, config files in git, or env files in git. Use the platform secret store and workload identity where it exists.
- Wrap secrets in a type that redacts itself in debug output, and never derive debug printing on structs that hold tokens. TLS libraries have shipped advisories for exactly this.
- Mark the `Authorization` header (and cookies, if any) as sensitive in the HTTP tracing layer so it never reaches logs.
- Log ids (request, device, actor), never raw tokens or full payloads at info level.
- TLS everywhere, including to the database, with certificate verification on (`verify-full` or equivalent).

## Tamper evidence

- An append-only table plus a hash chain (`hash = H(prev_hash || canonical_bytes(record))`) proves internal consistency. It does not stop someone with database access from rewriting history and recomputing hashes.
- Close that gap with periodic **checkpoints**: sign the chain head with a key held in an HSM or key vault and export it to write-once storage or a separate system.
- Canonical bytes are an explicit, versioned layout, not a general JSON serializer (key order, number format and escaping are not canonical). Freeze golden test vectors.

## Supply chain

- Commit the lockfile and build with it locked.
- Delay adopting freshly published dependency versions (some package managers support a minimum publish age); take urgent security fixes deliberately.
- Run advisory, licence and ban checks in CI on every pull request **and daily**, because advisories land between your commits.
- Embed the dependency list in release binaries or produce an SBOM per image so deployed artifacts can be scanned.
- Any new dependency with unsafe code or a build script gets a named reviewer.
- Read licences before copying code from reference repos; copyleft projects are study-only.

## Hardening defaults

- Request body limits and timeouts on every route (see AVAILABILITY-AND-RECOVERY.md).
- Minimal, non-root container images pinned by digest.
- Lint against panics in production paths (`unwrap`, `expect`, unchecked indexing, truncating casts) and against floats for money.
- Native code on mobile: keep keystore operations behind the platform, never pass private keys into shared code.

## Checklist

- [ ] App role does not own tables and has no `BYPASSRLS`; tenant tables have RLS enabled and forced.
- [ ] Caller context set with `SET LOCAL` per transaction.
- [ ] Cross-tenant read and write tests exist and pass.
- [ ] Secrets come from a secret store, redact in debug output, and never reach logs.
- [ ] Hash chain checkpoints are signed and exported outside the database.
- [ ] Lockfile committed; advisory checks run on PRs and daily.
