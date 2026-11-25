# Auth and permissions

Authentication says who is calling; authorization says what they may do. Both are decided on the server for every request, including requests replayed from an offline queue.

## Validating access tokens on an API

The API is a resource server: it validates tokens, it does not log anyone in. For a JWT access token from an OpenID Connect provider:

1. **Audience.** Accept only tokens whose `aud` is this API. Accepting a token minted for another resource is the confused-deputy problem.
2. **Issuer.** Read the provider's discovery document and require an exact `iss` match. For a single-tenant setup use the tenant-specific metadata; for multi-tenant, follow the provider's rules for tying `iss` to the tenant claim.
3. **Signature.** Pin the accepted algorithms (for example RS256 only). Select the key by `kid` from the `jwks_uri`. Providers rotate keys: refresh the key set on a schedule (Microsoft suggests checking about every 24 hours) and on an unknown `kid`, but rate-limit that on-demand refresh so forged tokens cannot trigger a refresh storm.
4. **Time.** Check `exp` and `nbf` against server time with a small leeway. Never device time.
5. **Stable user key.** Key users on the provider's immutable id scoped to the issuer or tenant (for Entra, `oid` plus `tid`; generically `sub` plus `iss`). Display names, emails and UPNs change and are not identifiers.
6. **Authorize on scopes or roles in the token**, mapped to your own permission model in one place.

Microsoft's version of these rules: https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens . Clients treat access tokens as opaque; only the API validates them.

## Permissions

- **Permission checks live in one module**, called by every handler, with deny as the default. A handler without an explicit check fails a test.
- **Check at the data layer too.** Scope queries by the caller's tenant or location, and back it with row-level security where the database supports it (see SECURITY-AND-RLS.md).
- **Segregation of duties is a rule, not a convention.** "The approver is not the requester" is a `CHECK` constraint or a domain rule checked on the server, not a UI hint.
- **Revocation has a stated delay.** Offline devices learn about revoked users at next sync. Write that delay down and make sure the server re-checks validity at the time of the action when the queue arrives.

## Shared devices and a second person

A common field requirement: one person stays signed in on a shared handheld, and a second person approves an action on the same device without taking over the session.

- Identity platforms in shared-device mode usually allow one signed-in account at a time; switching accounts signs the first person out. Check your provider's docs before promising otherwise.
- Resource-owner password flows (typing a password into the app) are the wrong answer: they break MFA and providers advise against them.
- Options, best first: the approver confirms on their own device (needs network); a separate isolated interactive sign-in whose token the server validates and the app never caches (test against real conditional-access policies); and for offline, a business control such as badge plus PIN verified locally against verifiers the server provisioned while online, re-checked on sync.
- Whatever the method, record approver identity, method, time and device, bind it into the signed record of the action, and have the server re-check it (verifier valid at that time, role allowed for that approval, approver is not the requester).
- Local PIN verifiers are slow hashes (Argon2id), encrypted at rest, with lockout after repeated failures recorded as audit events.

## Device keys

- Generate signing keys inside the platform keystore (hardware-backed where available) and never export them. Pick an algorithm every key store in the chain supports; ECDSA P-256 is the common denominator across mobile keystores and cloud HSMs, while Ed25519 support is patchy.

## Traps

- Accepting any token signed by the provider, without the audience check.
- Refreshing the key set on every unknown `kid` with no rate limit.
- Using email as the user key, then a user changes their email.
- An offline approval flow that the server trusts blindly on sync.

## Checklist

- [ ] Audience, issuer, algorithm, `kid`, `exp`/`nbf` checked on every request.
- [ ] Key set refreshed on a schedule and on unknown `kid`, rate-limited.
- [ ] Users keyed on an immutable id scoped to the issuer.
- [ ] One permission module, deny by default, every handler covered by a test.
- [ ] Segregation of duties enforced on the server.
- [ ] Revocation delay for offline devices written down and re-checked on sync.
- [ ] Second-person approvals bound into the record and re-verified by the server.
