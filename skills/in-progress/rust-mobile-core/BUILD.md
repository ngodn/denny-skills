# Building a Rust core for Android (and iOS)

## Pipeline

1. **Cross-compile with cargo-ndk.** It finds the newest NDK installed by Android Studio (or the one in `ANDROID_NDK_HOME`) and writes the `jniLibs` directory layout Android expects:

   ```sh
   cargo ndk -t arm64-v8a -t x86_64 -o app/src/main/jniLibs build --release
   ```

   Ship `arm64-v8a` for devices and `x86_64` for emulators. Add `armeabi-v7a` only if a real target device is 32-bit. `CARGO_NDK_PLATFORM` sets the API level. Source: https://github.com/bbqsrc/cargo-ndk

2. **Generate bindings from the built library (library mode):**

   ```sh
   cargo run --bin uniffi-bindgen generate \
     --library target/aarch64-linux-android/release/libyour_ffi.so \
     --language kotlin --out-dir build/generated/uniffi
   ```

   Library mode is the recommended form ("some external type features don't work otherwise"). Source: https://mozilla.github.io/uniffi-rs/latest/tutorial/foreign_language_bindings.html

3. **Package both in one step.** The generated Kotlin and the `.so` must come from the same UniFFI version and the same build, or method checksums fail at load. Never commit generated bindings by hand.

4. **Kotlin runtime dependencies:** JNA 5.12.0 or later as an `@aar` dependency, and kotlinx-coroutines 1.6 or later for async. Source: https://mozilla.github.io/uniffi-rs/next/kotlin/gradle.html

## Gradle integration

There is no official UniFFI Gradle plugin. Options seen in production:

- **A small in-repo convention plugin** that runs cargo-ndk and uniffi-bindgen, then registers the outputs (generated sources and jniLibs) through the current AGP variant API (`androidComponents.onVariants` with generated source directories). The UniFFI docs still show the older `libraryVariants` API.
- **Mozilla's `rust-android-gradle` plugin**, checking which release supports your AGP major.
- **A prebuilt AAR**: CI builds the core into an Android library module and publishes it to a Maven repo, so app developers do not need a Rust toolchain. Large open-source Rust SDKs with Kotlin bindings ship this way.

Wrap the core in its own Android library module that holds the generated bindings, the `.so` files, the gateway interface and a fake. Feature modules depend on the interface only.

## 16 KB memory pages

Android 15 and later supports devices with 16 KB pages. Native libraries built for 4 KB pages fail on them (or run in a compatibility mode with a warning). From https://developer.android.com/guide/practices/page-sizes :

- NDK r28 and later compile 16 KB aligned by default. With r27 and earlier, link with `-Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384`. Rust links through the NDK's clang that cargo-ndk selects, so a recent NDK gives you alignment; verify rather than assume.
- AGP 8.5.1 or later zip-aligns uncompressed native libraries to 16 KB.
- **Every** `.so` in the APK counts: yours, SQLCipher, JNA, vendor SDKs. Ask each vendor for 16 KB aligned builds.
- Check the **RELRO end** too: if `GNU_RELRO` shares a writable `LOAD` segment with later data, its end address must be 16 KB aligned or the app crashes with SIGSEGV on a 16 KB device.
- Remove code that assumes a 4 KB page (`PAGE_SIZE`, hard-coded 4096); use `sysconf(_SC_PAGESIZE)`.

Verify in CI on the built APK:

```sh
# load segments must be align 2**14 or more
llvm-objdump -p lib/arm64-v8a/libyour_ffi.so | grep LOAD
# RELRO end alignment
llvm-readelf -Wl lib/arm64-v8a/libyour_ffi.so | grep 'LOAD\|RELRO\|Type'
# zip alignment of the whole APK
zipalign -c -P 16 -v 4 app-release.apk
```

Then run the app on a 16 KB emulator image; `adb shell getconf PAGE_SIZE` should print `16384`. Android 17 adds a mode that aborts any incompatible binary instead of falling back:

```sh
adb shell setprop bionic.linker.16kb.app_compat.enabled fatal
adb shell setprop pm.16kb.app_compat.disabled true
```

## Release profile

```toml
[profile.release-mobile]
inherits = "release"
lto = "fat"            # or "thin" if build time hurts
codegen-units = 1
opt-level = "s"        # measure size and speed before keeping
strip = "symbols"
panic = "unwind"       # until you have tested how panics cross the FFI
overflow-checks = true
```

Archive the unstripped `.so` (or split debug info) for every release and upload symbols to your crash reporter, or native crash traces are unreadable.

## Shrinking (R8)

JNA uses reflection, and the generated bindings rely on it. Write and test keep rules for JNA, the generated package, and any vendor SDK in the first release build, not the week before launch. Run instrumented tests against the minified release variant.

## Encrypted SQLite in the core

`rusqlite` offers `bundled-sqlcipher` (links a system crypto library on native targets) and `bundled-sqlcipher-vendored-openssl` (vendors OpenSSL through `openssl-sys`). Android has no system libcrypto for you to link, so expect to use the vendored option or provide a crypto build, and treat the first Android build as a spike. Source: https://github.com/rusqlite/rusqlite

## iOS

UniFFI also generates Swift bindings. Build static libraries for the device and simulator targets, package them as an XCFramework with the generated Swift and module map, and implement the same callback interfaces with the Keychain and Secure Enclave. Check the UniFFI Swift docs for your version before wiring it; the library-mode tutorial shows Kotlin only.

## Versions (checked 2026-11-25)

Re-check every line before pinning; these move.

| Item | Value then | Source |
|---|---|---|
| UniFFI | 0.32.2. 0.31 changed method checksums (bindings and library from mismatched versions fail). 0.32.0: Kotlin callers pass a direct `java.nio.ByteBuffer` for byte arguments, async primary constructors fail generation, foreign-only traits via `#[uniffi::export(foreign)]`. 0.32.1 fixed a Kotlin checksum failure on aarch64, so skip 0.32.0. | https://raw.githubusercontent.com/mozilla/uniffi-rs/main/CHANGELOG.md |
| UniFFI licence | MPL-2.0 (file-level copyleft, fine to link; add it to your licence allowlist) | https://crates.io/crates/uniffi |
| Google Play 16 KB rule | Apps targeting API 35+ must support 16 KB pages on 64-bit devices; from 1 Feb 2027 updates without it cannot be released | https://developer.android.com/guide/practices/page-sizes |
| rusqlite | 0.43.0 | https://github.com/rusqlite/rusqlite |

## Build checklist

- [ ] One job builds the `.so` files and generates bindings with the same UniFFI version.
- [ ] Every `.so` passes the LOAD and RELRO alignment checks and the APK passes `zipalign -P 16`.
- [ ] App runs on a 16 KB emulator image.
- [ ] R8 keep rules cover JNA, generated bindings and vendor SDKs; minified build tested.
- [ ] Unstripped libraries archived and symbols uploaded per release.
- [ ] App developers can build without a Rust toolchain (prebuilt AAR or cached artifact).
