---
name: jsm-assets
description: Limits-and-gotchas reference for Jira Service Management Assets (Cloud) as a data platform. Use when the user is designing an object-type schema on JSM Assets, writing AQL, building bulk import/export or sync code against the Assets REST API, hitting an unexpected AQL or attribute error, sizing a batch job against the rate limit, or deciding where visibility/RBAC grants belong on an Assets schema.
---

# JSM Assets (Cloud)

Reference for Jira Service Management Assets (Cloud) as a data platform, not as a ticketing feature. Each item here cost someone real time once, usually because the platform's actual behaviour contradicts either the obvious assumption or the documentation. Treat every limit and gotcha below as a fact to design around, not a corner case to handle later.

## Attribute limits

| Limit | Value |
|---|---|
| Text attribute length | 255 characters |
| Textarea attribute length | 10,000 characters |
| Attributes per object type | 120 |
| Select options per attribute | 50 options, 2,700 combined characters |
| Attribute cardinality | 20,000 |

**Textarea is not AQL-searchable, at all.** Atlassian removed it. A query with a Textarea attribute in the `WHERE` clause returns:

```
HTTP 400 {"errorMessages":["Text area attributes are no longer supported in AQL."]}
```

Textarea values still come back fine in results when `includeAttributes=true`. A bulk blob read works; only the filter clause is blocked. Never store anything you need to query, filter, or automate on in a Textarea. Use Text (255 chars) for anything that has to appear in a `WHERE` clause, an automation condition, or a group-by.

**No usable attribute inheritance.** A child object type shares zero attribute ids with its parent, even when an "inherited" flag looks configured, verified across several configurations. Every leaf type needs its own copy of every shared attribute. For a deep taxonomy this changes the cost estimate materially: attribute count scales with leaf count times shared-attribute count, not with the shared set alone.

## AQL paging and counts

- `maxResults` is honoured up to a few hundred (verified to 500).
- The `total` field on a normal AQL response saturates at a fixed ceiling (1,000) regardless of the real result count. Never use it as a count. Use the dedicated count endpoint instead:

  ```
  POST /object/aql/totalcount
  ```

- Page size is a real performance lever, not a cosmetic setting. In one measured case, paging at 100 versus 500 was the difference between a 30s query and a 3.5s query for the same result set.
- Dot-notation `ORDER BY` was removed by Atlassian for performance reasons. Do not rely on it, even if it appears to work in a small test.

## Measured latencies

For sizing a batch job. Measured against a live instance, not documented platform numbers, so treat them as order-of-magnitude guidance rather than an SLA:

| Operation | Latency |
|---|---|
| Page read, 500 objects, `includeAttributes=true` | ~1.1s (cold start spikes 2-3.5s) |
| Page read, 500 objects, `includeAttributes=false` | ~0.6s |
| Object create | ~340ms |
| Single object GET | ~160-210ms |
| Single object PUT | ~435ms |

## Rate limit and reliability

Assets AQL is documented at roughly 1,000 requests/minute per instance. Look this figure up against the current Atlassian docs before sizing a real batch job rather than trusting this number as fixed; Atlassian revises published limits.

The platform drops sockets under sustained load independent of the rate limit. Any bulk or long-running job needs a retry adapter with backoff, not just a rate-limit-aware throttle. Wrap every call in try/catch: a dropped socket surfaces as the fetch call throwing, not as a non-2xx response, so a status-code-only retry branch never sees it.

## Endpoint gotchas

| Gotcha | Detail |
|---|---|
| Attribute creation path | `POST /objecttypeattribute/{objectTypeId}`, not the more guessable `/objecttype/{id}/attribute`. |
| Reference attributes | Need both the target object type id and the reference-type identifier (its uuid, e.g. "Dependency" or "Reference") set together. Supplying the target type without the reference-type identifier does not error; it silently creates a plain, non-reference attribute. |
| Reference-type lookup | Looking up reference-type uuids by name needs the `read:cmdb-config:jira` scope against the config endpoint for reference types. |
| Redirects | Assets endpoints redirect; handle it manually (`redirect: 'manual'` on the fetch) or the call silently follows to the wrong place. |
| Object key in AQL | `objectKey` is not addressable as a plain AQL clause the way the `Key` attribute is. A query with an `objectKey` clause fails with `"No matching attribute for AQL clause (objectKey)"`. Filter on the `Key` attribute instead. |

## Re-parenting an object type

Moving an object type to a new parent in a live schema: use the position endpoint, not the field that looks like the obvious way to do it.

| Approach | Result |
|---|---|
| `POST /objecttype/{id}/position` | Moves the type and its whole subtree, zero data loss. |
| `PUT` with `parentObjectTypeId` | Rejected (400). |

Strongly prefer the position endpoint over delete-and-recreate for restructuring a live schema; delete-and-recreate loses every object under the moved type.

## Visibility model

The documentation describes visibility as a schema-level grant. In practice, effective visibility comes from the object type's own "Users" role, not the schema-level grant. A scoped subtree enforces correctly with the schema-level grant left empty, as long as the specific object types are populated.

Apply grants on the specific object types a person or team actually needs, never as a shortcut through a tidier root-level grant that relies on inheritance. This has been re-broken and re-learned three separate times: someone applies a grant at a root node expecting it to cover the subtree, it does not reliably hold, and access silently fails for a leaf type. Grant explicitly on every type that needs it.

## Workflow and automation mechanics

- The object-lookup step in workflow/automation config caps at a low count (around 100, sometimes lower depending on configuration). Anything bulk needs a direct REST call instead of the built-in lookup step.
- Approval steps support no conditional logic.
- Placeholders (`${customfield_x}`-style) only work in the filter/scope field, not generally across the config.
- Status is its own distinct attribute type, not a generic Select. Treat it differently when building forms or automation conditions against it.

## Field config endpoint

```
PUT /rest/servicedesk/cmdb/latest/fieldconfig/{id}
```

The body addresses attributes **by name**, not by id, and the call needs the workspace id (from `GET /rest/servicedeskapi/assets/workspace`). Passing an attribute id where the endpoint expects a name fails silently or targets the wrong field depending on the payload shape; always resolve to the name first.

## No API, no events

- No Cloud API exists for comments, attachments, or role assignment. Those are UI-only operations; do not design a feature that assumes they are scriptable.
- No product events fire for Assets object changes. An app that needs to detect a change (its own or someone else's) has to track its own version counters on the writes it makes; there is nothing to subscribe to.

## Deleting a large schema

`DELETE /objectschema/{id}` times out on a large schema. Delete object types deepest-first instead, which cascades and deletes their objects, then delete the now-empty schema. Deleting top-down on a deep schema is the version that times out.

## Schema and data design

Cascading-select emulation, canonical key design, grouping-node placement, and vendor/contract register design are covered in [SCHEMA-DESIGN.md](SCHEMA-DESIGN.md).
