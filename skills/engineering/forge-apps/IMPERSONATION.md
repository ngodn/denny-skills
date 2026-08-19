# Impersonation from a web trigger

Depth on the impersonation nuance named in [SKILL.md](SKILL.md). This is the single most valuable non-obvious fact in this skill.

## The nuance

Web triggers carry no attached user context, and the platform's own documentation reads as a blanket statement: user-context calls will not work in web triggers. Taken at face value, that reading is wrong for one real case.

**If the app already has the target user's account id from an independent source** (resolved from a third-party token's claims, looked up by email before the call, whatever the source), a user-context call made directly inside the web trigger handler does work, provided the manifest declares impersonation for the app. The documentation's blanket statement describes the case where the web trigger has no way to know who the user is; it does not describe the case where the app already knows the account id and only needs to act as that user.

## Preconditions

Before designing around direct impersonation, confirm every one of these holds for the target user, because any one failing makes the impersonated call fail:

- The impersonated user has access to the installed app (any licensed user for a shared install, or an app contributor for a private, unshared install).
- The user is not deactivated.
- The user is not anonymous.
- The user is not a portal-only customer without a full licence.
- The user is not another app's service account.

Impersonation itself is silent: a system-token-plus-account-id exchange, no browser popup, no per-call consent dialog shown to the impersonated user. Normal write scopes need only the one-time admin consent granted at install; only PII-adjacent scopes need a separate per-user consent grant.

## Fallback architecture

When direct impersonation is undesirable, or one of the preconditions cannot be guaranteed for every user who might trigger the flow, fall back to a two-step design instead of forcing the direct path:

1. The web trigger validates the external callback (signature, issuer, claims, per the checklist below) and writes a pending action to storage. It does not attempt the user-context call itself.
2. A scheduled trigger, which does have the ability to defer work rather than needing to resolve it immediately, picks up pending actions and processes them with `asUser()` in its own invocation.

This adds a delay bounded by the scheduled trigger's interval, but avoids depending on every possible target user meeting the impersonation preconditions in the moment the web trigger fires. Accept the delay as the cost of the safer path when the preconditions cannot be guaranteed.

## Security checklist for an external caller into a web trigger

Any web trigger a third-party service calls into needs these checks before it acts on the request, not just a valid-signature check alone:

- Validate the token's signature and issuer.
- Verify the calling-application claim matches the specific registered caller, not just "any validly signed token from this issuer." A validly signed token from a different application under the same issuer should still be rejected.
- Verify the identity claim maps to an allowed actor for this action, rather than trusting the claim's subject blindly.
- Add a correlation nonce to the callback URL or payload for replay protection, so a captured, valid request cannot be replayed later to repeat the action.
- Keep any long-lived secrets used to validate the caller (a signing key, a client secret) in encrypted storage, never in the manifest or in plaintext environment configuration.
