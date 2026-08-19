# Virtual schema, cold start, and value-level encryption

Depth on the backbone-schema storage pattern from [SKILL.md](SKILL.md): how to build an app-defined object model on top of a small number of real Assets object types, how to keep a large backbone fast on a cold container, and how to encrypt what it stores.

## The virtual-schema pattern

The 120-attributes-per-object-type ceiling means a rich app data model cannot be built as one real Assets attribute per app field once the model has more than a handful of fields per object. Sidestep it by keeping the model virtual:

- Virtual attribute definitions (names, types, ordering, validation) live in one encrypted definition object, not as real Assets attributes. Editing the model's structure is one object rewrite, not a real-attribute migration across every existing object of that type.
- Every real object backing a virtual object gets a fixed, small real-attribute footprint regardless of how many virtual attributes it represents:
  - A searchable hashed name attribute, for exact-match lookup without exposing plaintext in a field anyone with schema read access can browse.
  - A few long-text attributes holding chunks of an encrypted blob (the object's actual virtual-attribute values).
  - A version counter, for optimistic locking on writes.
  - Who last updated it.
- Reuse the native object key as the identity key for the virtual object, rather than minting a separate synthetic identifier. One fewer field to manage, one fewer API call per create.

This keeps every virtual object type's real footprint constant no matter how many virtual fields it grows, which is what actually avoids the attribute ceiling; the ceiling is per real object type, and a virtual model only ever consumes a handful of real attributes per type no matter how deep the virtual model gets.

## Cold start on a large backbone

Naive full type discovery on every cold container is expensive once the backbone accumulates a large number of real object types: fetching the whole type roster before the app can serve a single request costs many seconds, and Forge spins up fresh containers often enough that this cost is paid repeatedly rather than once.

Fix: persist a tiny bootstrap roster (reserved type ids and schema roots) as its own config object in the backbone. A cold container reads the roster with a couple of cheap queries instead of the full discovery scan. Fall back to full discovery only if the roster is missing or looks stale, so the system self-heals rather than depending on the roster always being correct.

## Value-level encryption

Authenticated symmetric encryption (for example AES-GCM), with a random nonce generated per object rather than reused, and the authentication tag stored alongside the ciphertext so tampering is detectable on decrypt. Use a versioned blob format (a leading version tag before the nonce/tag/ciphertext) so the format can change later without breaking objects encrypted under an older version.

Chunk the encrypted blob across several long-text attributes, accounting for base64 inflation (roughly a third larger than the raw bytes) when sizing how much plaintext fits per chunk against the Textarea character limit.

Use a keyed hash (for example an HMAC derived from the encryption key) for exact-match search on a value without exposing its plaintext to anyone with ordinary schema read access. This gives lookup-by-name without a plaintext name field.

Document what this actually protects against, honestly, in a risk table rather than leaving it implicit. If the encryption key itself is stored alongside the encrypted data in the same backbone, the scheme is not a security boundary against someone with native schema admin access to that backbone; it is obfuscation against casual browsing. Say so in the risk table rather than letting "encrypted" imply a stronger guarantee than the key-storage choice actually delivers. Keep a path open to a stronger key-management scheme (a wrapped key held outside the backbone) if the threat model later requires it.
