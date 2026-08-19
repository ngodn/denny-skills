# Portable Linux binaries

The detail behind shipping a single binary that has to run across distributions you don't control: which glibc to build against, what to build from source, how to verify the artifact instead of the code, and what never gets bundled.

## Build old

glibc symbol compatibility is one-directional: a binary built against a newer glibc will not run against an older one, but a binary built against an older glibc runs fine on anything newer. No packaging trick fixes this after the fact. Build inside a container pinned to an old glibc; a base image several years old covers most current distributions' minimums in one build.

## Build heavy dependencies from source, minimally

Build heavy dependencies from source inside the build image, with only the features actually called, rather than installing the packaged version. Disabling everything by default and enabling only the specific codecs or features in use can take a dependency from tens of megabytes down to a few. Where a dependency loads a hardware library at runtime (`dlopen`) rather than linking it at build time, the feature can be built in without the full vendor SDK present at build time, and the build stays reproducible on a machine with none of that hardware, which is what makes it usable in CI.

## Verify before publishing

A recipe the test suite cannot catch, because it is about the artifact, not the code:

- `objdump -T <binary> | grep GLIBC_ | sort -V | tail -1` confirms the actual glibc floor the binary needs.
- Run `ldd` on the binary inside a different distribution's container than the one it was built in, to confirm nothing unexpected is unresolved.
- Run the packaged artifact itself, not the extracted tree. The two paths differ, and the packaged one is what people actually run.

## What's deliberately not bundled

Keep an authoritative exclusion list, one reason per entry, in the packaging script itself. The graphics and driver stack (OpenGL/EGL, DRM, the display server's client libraries, GPU compute libraries) cannot be bundled: a bundled copy can't talk to the target machine's actual kernel modules, so those have to come from the host. Loading them by name at runtime (`dlopen`) rather than linking them at build time keeps the list of things the target machine must already have as short as possible, ideally down to one or two libraries any working graphics stack already provides.

## Deploy templates

Ship deployment templates with obviously fake placeholder values (an example hostname, a documentation-reserved IP address) so an unedited copy fails visibly instead of silently pointing at something real. Keep real, filled-in copies out of version control.
