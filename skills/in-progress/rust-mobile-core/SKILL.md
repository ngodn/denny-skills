---
name: rust-mobile-core
description: Reference for sharing one Rust core between a backend and Android or iOS apps through UniFFI. Use when the user is splitting a Rust workspace into shared domain and platform crates, designing a UniFFI surface (records, errors, callback interfaces, async), building Rust for Android with cargo-ndk and Gradle, hitting 16 KB page alignment, JNA or checksum errors, putting an encrypted SQLite store inside the core, or calling a platform keystore from Rust.
---

# Rust mobile core

One Rust rule set, compiled into the server and into the mobile apps, so validation, conflict rules, hashing and wire formats are written once. The platform app (Kotlin, Swift) stays a UI and device-integration layer. The cost is an FFI boundary you must design as carefully as a public API.

Read this file for the design. Read [BUILD.md](BUILD.md) when wiring the build (cargo-ndk, Gradle, 16 KB alignment, R8, release profile), and check its dated versions section before pinning anything.

## When it pays

- The device must enforce the same business rules as the server while offline, or produce data the server must verify byte for byte (hash chains, signatures, canonical encodings).
- More than one client platform needs the same logic.

If the app is a thin online client, a shared core is cost without payoff.

## Crate split

```
crates/
  domain/     no IO: types, state machines, validation, conflict rules, canonical bytes, hash chain
  protocol/   wire DTOs shared by device and server, versioned (can live inside domain)
  core/       on-device engine: encrypted SQLite store, drafts, outbox queue, batching, pull apply
  ffi/        UniFFI bindings over core (crate-type cdylib + lib); the only crate with uniffi
  server/     HTTP server, database adapters, depends on domain + protocol, never on ffi
```

Rules:

1. **`domain` has no IO.** No async runtime, no database driver, no HTTP client. Check it in CI by asserting that the dependency tree of `domain` contains none of them.
2. **No UniFFI derives on domain types.** Map at the boundary in `ffi`, so the server never compiles UniFFI and the domain stays free to change shape.
3. **Features are additive.** Cargo unifies features across a workspace, so server-only code goes in server crates, never behind a feature flag in `domain`.
4. **Pure-Rust crypto in shared crates** (RustCrypto hashes and curves). It cross-compiles to every mobile target with no C toolchain. Server-only TLS can use a C-backed provider.
5. **`std` is fine.** UniFFI needs it and so do the platforms. Stay `no_std`-friendly only if a firmware target is real.

## Boundaries

- **The core does no networking.** The platform owns HTTP, identity tokens and background scheduling. The core produces push request bodies and consumes push results and pull payloads as bytes, so the wire format is defined once in Rust and shared with the server. (Moving HTTP into Rust is possible, but a Rust TLS stack may not honour the platform's network security config or user-installed CAs, which matters behind corporate TLS inspection.)
- **The core cannot reach the keystore.** Signing and key unwrapping go through a **callback interface** (a foreign trait) the app implements with Android Keystore or the iOS Keychain/Secure Enclave. Pick an algorithm all your key stores support: ECDSA P-256 works in Android Keystore, the Secure Enclave and cloud HSMs.
- **The core owns the local database** when it owns sync. One encrypted SQLite file opened by the core; the platform never opens it. The database key is unwrapped by the app (through the keystore) and handed to the core at open.

### Who owns the local store

| Option | For | Against |
|---|---|---|
| Rust core owns it (encrypted SQLite opened from Rust) | Queue, sequences, cursors, idempotency and read models live next to the rules; host-testable; one crypto build | No platform ORM conveniences (reactive queries, paging); every UI read crosses FFI; building SQLCipher with a crypto backend for Android is a spike item |
| Platform owns it (Room plus SQLCipher, Core Data) | Best UI integration | Sync semantics split across two languages; two places to get transaction boundaries right |

Pick one. Never ship two encrypted SQLite copies in one app.

## Designing the FFI surface

1. **Chunky, not chatty.** Every call crosses JNA (Kotlin) or the C ABI (Swift) with marshalling. Batch high-rate inputs (one call per scanner burst of tens of milliseconds, never per item). Return whole view records, not one field per call.
2. **Bytes for protocol payloads.** Push and pull bodies cross as byte buffers holding the serialized wire format, not as deep record trees.
3. **One object as the entry point**, constructed with the database path, key, device id and the signer callback. Methods for: reference data, lookups, drafts (create, update on every keystroke, validate, submit), sync (next push batch, apply push result, apply pull, queue status, exceptions), and audit (log, verify chain).
4. **One small stable error enum per surface** with `#[derive(uniffi::Error)]`. Use `#[uniffi(flat_error)]` when the platform only needs the variant and a message. Wrap it on the Kotlin side in a sealed type in one module so the app never sees raw generated exceptions. Keep variants coarse: locked, not found, invalid (code and message), storage, crypto.
5. **Panics are not errors.** A Rust panic is not one of your variants. Test how your UniFFI version surfaces a panic, keep the mobile profile on unwind until you have, and lint against `unwrap`, `expect` and unchecked indexing in non-test code.
6. **Async needs explicit cancellation.** UniFFI turns `async fn` into a Kotlin `suspend fun` (the foreign side drives the future; Rust needs no executor), but cancelling the coroutine does not cancel the Rust future. Add a cancel method or token for long operations, or keep calls synchronous and short and run them on a background dispatcher.
7. **Change notifications through a callback**, which the app turns into a Flow or publisher. The UI then observes core state like any reactive store.
8. **The app depends on an interface, not the bindings.** A hand-written gateway interface in the platform code with two implementations: the real bindings and a fake. Feature work proceeds against the fake while the core lands.

## Testing

- Rules, storage and protocol are tested in Rust on the host (`cargo test` or nextest), including property tests and golden vectors.
- A thin instrumented test on a device or emulator loads the real `.so`, opens the database, and runs the golden vectors through the bindings.
- Run the same golden vectors in server tests, so device and server agree byte for byte.

## Pitfalls

- Generated bindings and the native library from different UniFFI versions or builds: checksum mismatch at load time. Generate both in the same build job and never commit generated code separately.
- JNA or the generated bindings stripped by R8: keep rules needed (see BUILD.md).
- Native libraries not 16 KB aligned, including third-party ones (see BUILD.md).
- A per-item FFI call inside a scanner callback.
- UniFFI derives creeping into the domain crate "just for convenience".
- `panic = "abort"` in the mobile profile, turning any bug into a silent app kill.

## Review checklist

- [ ] `domain` has no IO dependencies, checked in CI; no UniFFI in `domain` or `server`.
- [ ] Core does no networking; keystore access goes through a callback interface.
- [ ] One owner for the local database.
- [ ] FFI calls are batched; protocol payloads cross as bytes.
- [ ] One coarse error enum per surface, wrapped in a sealed platform type.
- [ ] Long async calls have explicit cancellation.
- [ ] App codes against a gateway interface with a fake.
- [ ] Golden vectors run in Rust, through the bindings on device, and on the server.
- [ ] Build items in [BUILD.md](BUILD.md) are satisfied.
