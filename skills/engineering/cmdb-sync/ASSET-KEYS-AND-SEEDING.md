# Asset keys, hierarchy placement, and seeding

## Asset key design

A canonical asset key is opaque: no business unit, site, owner, IP, or classification encoded in the key itself, so reorganising the business never invalidates a key. Keys are immutable and never reused. Keep source-system ids (a discovery tool's primary key, a serial number, a ticketing system's key) as separate columns, never folded into the canonical key string. Anything else worth tracking gets its own attribute, not an appendage to the key.

State the real key-assignment mechanism, not the intended one. Documentation that says keys are system-generated can describe an aspirational design rather than what actually happens; verify and say plainly whether assignment is automated or manual before anyone builds against the assumption.

## Hierarchy placement

A grouping node (a team, a classification bucket) belongs under the deepest applicable existing node in the taxonomy. Never invent a shortcut node, and never mix a classification node with a team node at the same level. When source data does not cleanly map to an existing leaf, that is a signal to go find the right home, not a license to place it "close enough."

Unresolved or no-data rows go into an explicit ungrouped leaf under the correct parent. Never omit them and never guess a placement for them; an explicit "unresolved" leaf keeps the gap visible instead of hiding it inside a plausible-looking wrong answer.

## Seeder and backfill script conventions

- Support a dry run.
- Match by `(parent, name)` for idempotency, so a re-run only creates what is missing.
- Document in the script itself what was deliberately excluded, and why. A future re-run or reviewer should not have to rediscover the reasoning behind an exclusion.
- Take credentials from the environment, never hardcoded.
- Treat one credential reaching more than one environment (a sandbox and a production instance, for example) as a review point on its own: it widens the blast radius of that one credential beyond what either environment alone would justify.
