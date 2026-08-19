## What it does

`jsm-assets` is a limits-and-gotchas reference for Jira Service Management Assets (Cloud) as a data platform, not as a ticketing feature. Every item in it cost someone real time once, usually because the platform's actual behaviour contradicts either the obvious assumption or Atlassian's own documentation. It covers attribute limits, AQL paging and counting, measured latencies for sizing a batch job, endpoint gotchas that are easy to get wrong, the re-parent endpoint, the visibility model, and workflow/automation mechanics.

The defining constraint the whole skill is built around: visibility, inheritance, and paging on this platform do not behave the way the documentation, or a first read of the admin UI, suggests they do. Design against the measured behaviour, not the described behaviour.

## When to reach for it

Type `/jsm-assets`, or the agent reaches for it automatically when the task fits.

Reach for it before designing an object-type schema on Assets, before writing AQL, before building any bulk import/export or sync code against the Assets REST API, or the moment an AQL or attribute call returns an error that does not match what the endpoint name suggested it should do.

| The situation | Reach for |
|---|---|
| Designing a schema, or estimating how many attributes a deep taxonomy needs | `jsm-assets` |
| An AQL query against a Textarea attribute returns a 400 | `jsm-assets` |
| A count from a paged AQL response looks capped at 1,000 | `jsm-assets` |
| Sizing a bulk job against the rate limit | `jsm-assets` |
| Visibility grants aren't reaching a subtree the way the schema-level role suggests they should | `jsm-assets` |
| Building a Forge app that reads or writes Assets data | [forge-apps](../engineering/forge-apps.md), which assumes this skill's platform facts |
| The domain words for the schema itself ("asset" means three things to three teams) | [domain-modeling](../engineering/domain-modeling.md) |

## Attribute limits and the AQL gotchas

The core numbers: Text attributes cap at 255 characters, Textarea at 10,000, 120 attributes per object type, and Select options cap at 50 choices or 2,700 combined characters. None of these are configurable per-tenant.

Two behaviours matter more than the numbers. Textarea attributes are not AQL-searchable at all: a query filtering on one returns `HTTP 400 {"errorMessages":["Text area attributes are no longer supported in AQL."]}`, even though the same attribute's value comes back fine in results when attributes are included. Only the filter clause is blocked, not the read. And attribute inheritance does not work: a child object type shares zero attribute ids with its parent even when an inherited flag looks configured, so every leaf in a deep taxonomy needs its own copy of every shared attribute.

The skill's [SCHEMA-DESIGN.md](../../skills/engineering/jsm-assets/SCHEMA-DESIGN.md) sibling file goes further: canonical key design, where a grouping node belongs in a taxonomy, the cascading-select emulation pattern (mirror objects matched by parent and name, since Assets has no native cascading select across arbitrary depth), and a three-decision checklist for adding a vendor/contract register to an existing schema.

## Common questions

**Why does my count come back wrong on a large result set?**

The `total` field on a normal AQL response saturates at a fixed ceiling regardless of how many objects actually match. It is not a bug in the query; it is a hard cap on that field. Use the dedicated count endpoint (`POST /object/aql/totalcount`) for a real count.

**I set a role grant at the schema level and a subtree still isn't visible to the team it should be visible to. What's wrong?**

Effective visibility comes from the object type's own "Users" role, not the schema-level grant, contrary to how the documentation frames it. Apply the grant on the specific object types that need it. This exact failure has been re-learned three times: someone grants at a tidier root node expecting inheritance to carry it down, and it does not reliably hold.

**Why did creating a reference attribute produce a plain attribute instead?**

The reference-type identifier (the target type's reference-type uuid) is a separate field from the target object type id, and omitting it does not error. It silently creates a non-reference attribute that looks right in a quick glance at the schema but has no reference behaviour.

## It's working if

- A schema design states attribute-per-leaf costs up front, accounting for the lack of inheritance, instead of discovering the true attribute count after the taxonomy is half-built.
- Nothing in the codebase queries a Textarea attribute in an AQL `WHERE` clause.
- A count anywhere in the code comes from the dedicated count endpoint, never from a paged response's `total` field.
- Visibility grants are applied on the named object types, not on a root node relying on inheritance.
- A bulk job includes a retry adapter with backoff and is sized against the documented rate limit rather than a guessed concurrency level.

## Where it fits

`jsm-assets` is a **reach-for-it-anytime standalone**, a vocabulary-and-limits layer other work sits on top of rather than a step in a chain. Its closest neighbour is [forge-apps](../engineering/forge-apps.md): a Forge app that reads or writes Assets data inherits every limit here, plus a further set of Forge-specific runtime constraints. For the whole map, ask [ask-denny](../engineering/ask-denny.md).
