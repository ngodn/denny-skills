---
name: self-hosting
description: Running your own edge (static hosting, access gates, a local trusted-HTTPS dev proxy) and remote access (remote desktop, streaming, VPN coexistence) on a Linux box. Use when the user is serving multiple static sites from one nginx container, gating a path behind a passphrase, setting up a locally-trusted HTTPS proxy for a dev server, choosing between remote-desktop options for a GPU session, remapping keybindings for a constrained remote keyboard, or debugging DNS/routing breakage between two VPN or overlay-network clients.
---

# Self-Hosting

Running your own edge and remote access on a Linux box: serving static content, gating it, terminating trusted HTTPS locally for development, and reaching a GPU-accelerated desktop remotely. The recurring theme: prefer a change that needs no config elsewhere (a bind mount, a new nginx `location`) over one that ripples through a whole stack, and treat "the vendor toast said success" or "the container shows Up" as unverified until you've checked the actual log or file.

## Multi-site static hosting behind a reverse proxy

Serve several static sites or decks from one `nginx:alpine` container sitting behind an existing reverse proxy:

- One read-only bind mount per public sub-path, so relative asset references inside each site resolve correctly without any proxy-side rewriting.
- Deploy files (compose file, nginx config, each site's source) live outside the served web root, so nothing in the build pipeline is reachable by path traversal.
- Redirect non-canonical case to the canonical path (a 301), rather than serving both.
- Long cache lifetime on static assets, no cache on HTML, so a redeploy is visible immediately while assets stay fast.
- Adding a new sub-path needs zero change to the proxy or tunnel layer in front of the container: it's a new bind mount plus one new `location` block, because the routing in front of the container is already wildcard/subdomain-based.

## Server-side passphrase gate in nginx alone

Gate a path with a passphrase using nginx configuration only, no app server:

- Match a cookie against a **salted hash** of the passphrase (`map $cookie_<name> $access { ... }`), never the raw passphrase itself.
- On a missing or invalid cookie, internally rewrite (`rewrite ... last`) *every* request under the gated path to a gate page, not just the index. A rewrite covers directly-linked assets too; returning a 403 or 404 does not stop a client that already has a direct asset URL.
- The raw passphrase never appears in any served file. The gate page itself can embed a hash of the passphrase to validate input client-side, but the cookie value nginx actually checks is a hash of the passphrase plus a server-side salt, so knowing the client-side hash alone doesn't let you forge the cookie.
- A client-side JavaScript overlay is not a gate. It still serves the underlying files to anything that fetches them directly; it only hides them visually from a browser that runs the script.
- `map_hash_bucket_size` needs raising from its default for a long hex key (a 64-character SHA-256 hex string as the map key overflows the default bucket size).

## Local trusted-HTTPS dev proxy with mkcert

Give a dev server a secure context when it's reached from another device on the network:

- The certificate's Subject Alternative Names must include the actual IP address you connect by, not just a hostname. Browsers ignore the certificate's Common Name and check only the SAN list, so a bare hostname- or `localhost`-only cert won't validate when reached by LAN IP.
- Run nginx as a **user-level systemd service**, not the system daemon, when the home directory is locked down (mode `0700`): the system nginx runs as an unprivileged service account that can't read a cert stored under a locked-down home directory, but a user service runs as the owning user and can. Bind to a high port (for example `8443`) to avoid needing a bind capability; if binding `:443` directly is wanted later, set `cap_net_bind_service` on the nginx binary and pin it with a package-manager hook, since the capability is silently wiped on every nginx package upgrade.
- **Distributing the local root CA to a device with no desktop to run mkcert on** (a tablet or phone): serve the CA root certificate over plain HTTP (not the HTTPS proxy itself) with the certificate MIME type (`application/x-x509-ca-cert`) and an inline `Content-Disposition`, so a mobile browser offers to install it as a profile. It has to be plain HTTP because the device doesn't trust the local HTTPS proxy yet. The certificate itself is public (only the CA's private key is secret), so serving it unencrypted is fine.
- **Installing the profile is only half of it on iOS.** After installing the certificate profile, you must separately go into Settings and manually toggle full trust for the root certificate on; the profile being "installed" doesn't make the browser trust it yet.
- Keep every proxy artifact, including nginx's own writable temp paths, inside one project directory. A user-scoped nginx instance confined to one directory is fully portable and deletable, and doesn't touch anything outside the project.
- Pin the proxy to HTTP/1.1 where a specific mobile browser version is known to mishandle WebSocket upgrades over HTTP/2 (sending a plain request instead of the upgrade handshake). On a LAN, HTTP/2 multiplexing usually isn't worth that risk; check for known WebSocket-over-h2 regressions in the target browser before enabling h2.
- When a backend already multiplexes a page and its WebSocket on one port, pass the path through unchanged rather than splitting it into two nginx `location` blocks. Rewriting or stripping the path here can leave an empty request URI on the WebSocket leg, breaking the upgrade with an opaque error.

## Remote desktop and streaming

Two different stacks solve two different problems; don't reach for the gaming one to access a plain desktop, or vice versa:

| Goal | Stack |
|---|---|
| Reach the actual Linux desktop from a browser, no client install | Headless compositor output plus a VNC server, fronted by a browser-based gateway |
| GPU-accelerated, low-latency access for anything interactive (gaming) | Hardware-encoded capture plus a native streaming client, tunnelled over a mesh VPN rather than a forwarded port |

Tuning notes that apply to a virtual/headless output:

- Match the virtual output's resolution to the client device's real pixel dimensions (not its logical/point size), and subtract the client's own chrome (a browser status bar, a PWA's window chrome) from that, since that chrome eats real pixels naive resolution matching misses.
- Prefer a **disjoint workspace number range** for virtual outputs (for example 11-15 when physical monitors use 1-5), so a virtual output never steals workspaces already bound to a physical monitor.
- Compositor components that don't automatically appear on a virtual output (a status bar, for instance) need to be explicitly restarted or re-targeted onto it; don't assume a virtual monitor inherits the full desktop chrome for free.
- Whatever capability the capture binary needs (commonly a capability for KMS-level screen capture) gets wiped on every package upgrade and must be reapplied; pin the reapplication with a package-manager hook rather than a manual step you'll forget.

## Remapping keybindings for a constrained remote keyboard

When a remote keyboard is missing a modifier key entirely (a tablet's attached keyboard with no Super/Cmd-as-Super equivalent, for example), duplicate every binding that uses that modifier under an alternate combination using the compositor's submap mechanism, leaving the original bindings untouched so the same machine still works normally with a local keyboard. Audit **every** binding that uses the modifier being rerouted, not just the ones you remember off the top of your head; a partial audit reliably produces repeated "this still doesn't work" reports for whichever bindings got missed.

## Two overlay/VPN clients on one host

Running two VPN or overlay-network clients on the same host at once is a recurring, well-understood source of DNS and routing breakage. Try userspace networking mode on the secondary client first. Whatever flags neuter its default route/DNS-takeover behavior, pin them with a systemd unit override that reapplies them on every start, not a one-time CLI invocation: a bare bring-up of the client, a package update, or a reinstall will silently re-enable route and DNS takeover otherwise.

**Re-diagnose a known workaround after a major upgrade**, rather than reapplying it reflexively. The underlying bug the workaround was built for may already be fixed, and what looks like the same symptom can have an unrelated cause, stale network state left over from an upgrade being a common one. Also: a query refused by a resolver outside the VPN tunnel while the VPN is up is expected leak-protection behavior, not a fault to fix.

## Decision table for remote access to a GPU-accelerated session

| Need | Reach for |
|---|---|
| Blend GPU-accelerated apps into the existing host desktop | A container runtime that shares the host's display socket directly |
| Sandboxed remote desktop, non-gaming | A container with its own headless display server plus VNC/RDP |
| Low-latency access for anything interactive (gaming) | Hardware-encoded capture and streaming, as above |
| A genuinely different OS, or hard isolation | Full device passthrough (only justified case for it) |

Caveat for the streaming route: if the mesh VPN can't establish a direct connection and falls back to a relay, bandwidth through the relay is capped well below what's needed for smooth high-resolution streaming. Verify a direct connection is actually in use before troubleshooting stream quality anywhere else.

## Reflecting a hardcoded loopback target onto a real address

Some mobile client tools hardcode a fixed loopback-style address as the debug or control-server target they expect (a specific `10.x.x.x` address, for instance), which is unreachable from a phone or tablet on the same network. Fix by NAT-reflecting that fixed address onto the dev machine's real reachable IP with firewall prerouting rules, rather than trying to change the client's hardcoded expectation.
