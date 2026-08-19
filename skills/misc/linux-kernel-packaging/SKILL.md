---
name: linux-kernel-packaging
description: Building, patching, and packaging Linux kernels and out-of-tree kernel modules on an Arch-family distro, plus repackaging a foreign binary app for Linux. Use when the user is layering a hardware patch set onto a distro kernel PKGBUILD, managing kernel config toggles, signing kernel modules, bisecting a broken kernel build, fixing an out-of-tree module broken by a kernel bump, or repackaging a Windows-only Electron app for Linux.
---

# Linux Kernel Packaging

Reference for building a patched kernel package on an Arch-family distro (PKGBUILD-based), keeping an out-of-tree module working across kernel version bumps, and repackaging a foreign-platform Electron app for Linux. The common thread: pin every version-specific fact (a patch commit, an API rename, a download URL) to one variable, so bumping it later is a one-line change instead of a re-investigation.

## Layering a hardware patch set on a distro base kernel

Pin the hardware patch set as a git source at an exact commit, stored in one variable at the top of the PKGBUILD:

```
_HW_PATCH_HASH=<commit>
source+=("patches::git+https://example.org/hw-patches#commit=${_HW_PATCH_HASH}")
```

Bumping the patch set later is a one-line hash change, not a re-fetch-and-diff exercise.

**Application order is defensive, not naive.** Apply the hardware patches first, then when the distro's own base patches run, skip anything whose filename mentions the hardware target (a plain substring check on the patch source name). Dry-run every patch (`patch -Np1 --dry-run`) before applying for real, and classify the result instead of letting one bad patch abort the whole build:

| Dry-run result | Meaning | Action |
|---|---|---|
| Clean apply | No conflict | Apply normally |
| "already exists" / hunk already applied | The base kernel already carries this change | Skip |
| "FAILED" hunks | Patch doesn't match this kernel version | Skip, treat as a version mismatch, not a hard error |
| Unknown conflict | Neither of the above | Force-apply with `--forward --reject-file=-` so a partial apply doesn't abort the build; inspect the `.rej` file afterward |

## Config management

Sequence: copy the distro's base `.config` in, append an extra config fragment if the hardware patch set ships one, then toggle build-time options with the kernel's own `scripts/config` tool rather than hand-editing the file:

| Axis | Tool call shape |
|---|---|
| Microarchitecture | `scripts/config --set-val GENERIC_CPU 0` / enable the specific `MNATIVE`/`MZEN*` symbol |
| Scheduler | `scripts/config -e <SCHED_SYMBOL>` (pick one of the distro's offered scheduler variants) |
| Timer frequency (HZ) | `scripts/config --set-val HZ <n>` plus the matching `HZ_<n>=y` |
| Preemption model | `scripts/config -e PREEMPT` / `PREEMPT_VOLUNTARY` / `PREEMPT_NONE` |
| Link-time optimisation | `scripts/config -e LTO_CLANG_THIN` (or `_FULL`), requires building with clang+lld |

Doing this via `scripts/config` instead of sed keeps dependent Kconfig symbols consistent, which hand-editing the raw file does not guarantee.

## Module signing

After the build, read the signing key path out of the *built* `.config` (`CONFIG_MODULE_SIG_KEY`), resolve it to an absolute path under the build directory, then sign every `.ko` with the in-tree tool:

```
find "$pkgdir" -name '*.ko' -exec "$srcdir/$_kernelname/scripts/sign-file" sha256 \
  "$keypath" "$srcdir/$_kernelname/certs/signing_key.x509" {} \;
```

Run this pass twice: once against the module tree in the kernel package, once against the headers package (out-of-tree modules built later against the headers need signed `.ko`s too when Secure Boot is on).

## Bisecting a broken kernel build

Toggle these off one at a time rather than guessing at a root cause:

1. **Memory pressure during build**: reduce parallelism (`MAKEFLAGS="-j2"`) before assuming a real compile error.
2. **Link-time optimisation**: set LTO to `none` to isolate whether LTO itself is the break.
3. **Patch/kernel-version mismatch**: check the hardware patch set's commit against the target kernel version; a patch written against an older kernel is a common silent-failure source.
4. **Module load failures**: rebuild the initramfs (`mkinitcpio -p <preset>`) and the module dependency database (`depmod -a`); a module that built fine can still fail to load if these are stale.

## Patch series organisation for a raw fork

When you're not layering onto a distro base but maintaining a raw kernel fork directly, keep a numbered patch series, one logical change per file (`1001-add-driver.patch`, `1002-move-driver-to-staging.patch`, `1003-fix-sparse-errors.patch`, ...). As the base kernel version moves forward, amend patches in place (rebase them) rather than stacking new patches on top of stale ones. The series should always read as "the current diff against upstream," not as a changelog of fixes-to-fixes.

## Out-of-tree module drift on a new kernel

When a vendor or out-of-tree module (a hypervisor's host modules, a legacy proprietary driver, and similar) breaks on a new kernel, the fix is almost always upstream kernel API drift. Structure the fix as a named before/after table, not a scattered patch:

| Category | Example drift |
|---|---|
| Build system | A deprecated build variable (e.g. an old `*_CFLAGS` knob) replaced by a newer one |
| Timer API | A renamed timer function |
| Register/MSR access | A renamed low-level accessor function |
| Module init | Bare init function replaced by requiring the module-init macro |
| Compiler | The kernel was built with a different compiler (clang vs gcc) than the module expects |

Auto-detect the kernel's compiler in the module's Makefile itself (inspect the running kernel's build config or `/proc/version` for the compiler string, and switch `LD`/`CC` accordingly) rather than requiring the user to export `CC=clang LD=ld.lld` by hand every time.

**Keep a pre-patched source tree per upstream vendor version, not just patch files.** Vendor tarball *layout* changes release to release (files move, get renamed, get split), so a patch file written against one vendor version often doesn't apply cleanly to the next even when the underlying fix is unchanged. A full pre-patched source tree per version survives that churn; a patch-only approach doesn't.

### Troubleshooting checklist

| Symptom | Cause | Fix |
|---|---|---|
| Module refuses to load, no error, device node missing | Secure Boot is on and the module is unsigned | Disable Secure Boot or sign the module (see above) |
| Build fails looking for kernel headers | Matching headers package not installed | Install the distro's kernel-headers package for the running kernel |
| Missing clang/lld errors during build | Toolchain not installed | Install the compiler toolchain the kernel was built with |
| Unrecognized compiler flag (e.g. a retpoline-thunk flag) | Compiler flag mismatch: module built with a different compiler family than the running kernel | The tell for a mixed-toolchain build. Rebuild the module with the same compiler (clang vs gcc) the kernel itself used |

## Repackaging a foreign-platform Electron app for Linux

Pipeline: download the vendor's installer for the *other* platform, extract the Electron app's resources from it, replace any platform-specific native modules with Linux-compatible builds, then package to several output formats from one script that detects the host distro (apt vs pacman family) and produces `.deb`, a native Arch package, or an AppImage depending on a flag.

**Sandbox tradeoff**: an AppImage typically runs with `--no-sandbox` because Electron's sandbox helper needs elevated privileges to create namespaces, which conflicts with the AppImage model. Mitigations, in order of preference: ship the `.deb` instead (it can set the needed capability at install time), wrap the AppImage with bubblewrap, or use an AppImage-integration tool that handles the sandbox for you.

**Updating for a new upstream release should be a single constant to bump**: the vendor's download URL, not a script rewrite. If the vendor's URL scheme itself changes, that's the one place to fix it.
