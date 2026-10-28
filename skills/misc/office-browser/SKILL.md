---
name: office-browser
description: Work in the user's real, signed-in Google Chrome profile (office accounts such as Jira, Confluence, Google Workspace, internal portals) through one long-lived chrome-devtools connection, so Chrome asks to allow debugging only once. Use when office or web work needs the user's logged-in browser: reading or filling a web app, checking a ticket or page, downloading a report, or debugging a page in their session.
---

# Office browser

The user's real Google Chrome (not Chromium) holds their signed-in work accounts. Agents reach it through the `chrome-office` MCP server: `chrome-devtools-mcp --autoConnect`, which attaches to the running Chrome Stable. **Chrome asks the user to Allow every new debugging connection**, and one connection lasts as long as its MCP server process. So the job is: one Allow at the start, then every browser step through that same connection.

Which profile to work in is a machine fact, not in this skill: read the "Office browser" line in the machine-specific notes of the global instructions (`CLAUDE.md` / `AGENTS.md` / `GEMINI.md`). It names the account and its Chrome profile directory.

## Start of the job

1. **Check the pieces.** Chrome Stable is running (`pgrep -f /opt/google/chrome/chrome`), remote debugging is on (`~/.config/google-chrome/DevToolsActivePort` exists; the setting survives Chrome restarts, so if it is missing ask the user to open `chrome://inspect/#remote-debugging` and turn it on), and your tool list has `chrome-office` tools. Without them, see Setup below.
2. **Ask first.** Before any other browser step, tell the user Chrome is about to ask to allow a debugging connection, and wait for them to be ready (AskUserQuestion: "Ready, I'll click Allow" / "Not now"). The dialog raises Chrome, and on a window manager that focuses activated windows it pulls the user over once; that is why it happens now and not mid-task.
3. **Connect right away.** Call `list_pages` as the first browser call, while the user is watching for the dialog. The job's connection exists once it returns.
4. **Find an office-profile tab.** For candidate pages, `select_page` (never with `bringToFront`) and check `document.title` or a snapshot for the office account. If the office profile has no tab open at all, open one now, while the user is still at Chrome: `google-chrome-stable --profile-directory="<profile dir>" "<url>"`. This activates the Chrome window, so never do it later in the job.
5. **Open work tabs in the background.** With the office tab selected, `new_page` with `background: true` opens a tab in that same profile without switching the user's view. It is fully usable: clicks, typing, snapshots and screenshots all work while it stays in the background.
6. **Confirm the account** on the page (`take_snapshot` shows the signed-in email) before reading or changing anything.

## During the job

- **Every browser step goes through `chrome-office`.** A Playwright script, `connectOverCDP`, `curl` against port 9222, or a second MCP server each opens a new connection and makes Chrome ask again. Never restart the MCP server mid-job.
- **One connection per agent job, never shared.** Agents sharing a connection would act on the same tabs and selected page and clash. A subagent or another session starts its own `chrome-office` server and its own prompt, so keep browser steps in this session and hand results over.
- **Stay out of the user's way.** The browser tools act inside the page through the debugging protocol, so the user's real mouse, keyboard and focus are untouched. Keep it that way: `new_page` always with `background: true`, `select_page` never with `bringToFront`, and never the desktop-control skill (real mouse) for browser work.
- **Leave the user's tabs alone.** Read them if needed; do the work in tabs you opened, and close only those (`close_page`).
- **Writes are the user's call.** Submitting a form, sending a message, changing a ticket, approving anything: show what you will do and get a yes first.
- Chrome shows a "controlled by automated test software" bar while connected; that is expected.
- If the connection drops (Chrome restarted, the user clicked Deny, the session restarted), say so and repeat steps 2 and 3. Don't retry silently, since each retry is another prompt.

## Other browsers

- The Playwright plugin (`mcp__plugin_playwright_*`) runs its own clean browser with no logins. Use it for public pages and throwaway checks, never for the office profile.
- The `chrome-devtools` plugin server without `--autoConnect` launches a separate blank Chrome, not the user's.

## Setup (once per machine)

Find the profile directory for an account: `jq -r '.profile.info_cache | to_entries[] | "\(.key)\t\(.value.user_name)"' ~/.config/google-chrome/"Local State"`.

Add the server to each agent, pinned:

- Claude Code: `claude mcp add --scope user chrome-office -- npx -y chrome-devtools-mcp@<version> --autoConnect --no-usage-statistics --no-performance-crux`
- Codex (`~/.codex/config.toml`): `[mcp_servers.chrome-office]` with `command = "npx"` and the same `args`.
- Antigravity (`~/.gemini/config/mcp_config.json`): a `chrome-office` entry under `mcpServers` with the same command and args.

The server connects lazily, on its first browser tool call, so sessions that never use the browser never prompt. Since Chrome 136, `--remote-debugging-port` is ignored on the default profile directory, so the `chrome://inspect` toggle plus `--autoConnect` is the way in to the real profile.
