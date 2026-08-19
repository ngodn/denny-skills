# DOQL and the Device42 API

DOQL is Postgres-flavoured SQL over Device42's own read-only views (`view_device_v2`, `view_hardware_v1`, `view_vendor_v1`, `view_resource_v2`, `view_cloudinfrastructure_v2`, `view_resourcerelationship_v2`, `view_software_v1`, `view_discoveryscores_v1`, and others).

## What works

Standard joins, `CASE WHEN`, `COALESCE`/`NULLIF`, `ILIKE`, POSIX regex match (`~*`), subqueries, `bool_and`, `count(*) FILTER (WHERE ...)`, JSON field access (`->>`, `->`), aggregate filters.

## Quirks that cost time

| Quirk | What happens | Workaround |
|---|---|---|
| Regex brace quantifier `{n}` | Returns HTTP 500. This is DOQL's own parser, not a proxy or WAF in front of it. | Write the pattern out longhand, e.g. `[0-9][0-9]` instead of `[0-9]{2}`. |
| SQL line comments (`--`) anywhere in the query | Whole query rejected with a generic 500, even trailing after complete, balanced SQL. | Keep notes in a sibling structure, e.g. a JSON `_note` key next to the query, never inline as SQL comments. |
| `information_schema` and `::` type casts | Blocked through the API layer. | Get column names with `SELECT * ... LIMIT 1` instead. Type casts do work from a DB-side query editor context, if you have one, distinct from the HTTP API. |
| Reserved words (`authorization`, `rows`, etc.) | Rejected unless quoted. | Quote or alias. |
| Negated boolean over a nullable column | `NOT (a OR b)` evaluates to NULL, not TRUE, whenever `b` is NULL. Rows that should match are silently dropped. | Wrap nullable columns with `COALESCE(col, '')` before using them in negated logic. |

## The cloud resource data model

Cloud resources split across two views that do not share a shape:

- Non-compute resources (S3, Lambda, ELB/ALB, EBS, RDS, DynamoDB, Blob Storage, VM Scale Sets, API Gateway, CloudFront, KMS/Key Vault, security groups, AMIs, and more) live in one wide view keyed by `resource_pk`/`identifier`, with a `vendor_resource_type` discriminator column, a `details` JSON blob for type-specific fields, and vendor-native tags in their own `vendor_custom_fields` JSON column, separate from Device42's own internal tagging.
- Compute instances (EC2, Azure VMs) live in a separate, smaller view and carry no cloud-native tags at all. This is a platform limitation; no downstream integration can fix it by querying harder.

Join a compute instance to its parent cloud account through the instance's raw account id against the cloud-infrastructure view's `account_id`. The shortcut foreign-key-looking column that appears to do this join directly is unreliable, effectively always null in practice. Filter out soft-deleted or dead rows explicitly; the "Deleted"/"not in service" status column is not filtered by default on either view.

Cross-resource relationships (API Gateway to Lambda trigger, Function App to its functions) are modeled as generic from/to/relation triples in `view_resourcerelationship_v2`. Join it back into the resource view twice, once per direction, and aggregate with `COUNT(DISTINCT CASE WHEN rr.relation = '...' THEN rr.to_resource_fk END)` to turn a generic edge table into several named counts in one row per resource.

## Access pattern: dial the IP, not the domain

When both a domain name and a raw IP reach the same instance, dial the raw IP directly and pass the real hostname as the HTTP `Host` header, rather than dialling the domain name. If the IP stops responding, that is the caller's own network path (VPN, tunnel), not a server-side outage. Don't fail over to the domain name: a domain-name fallback can silently route traffic through an intermediate proxy or WAF layer with different, unintended behaviour.

## Agent binaries

An agent binary embeds the target appliance URL at download time, but accepts a runtime host-override flag (check the binary's own help output; kit documentation may not mention it) to point the same binary at a different host, useful when the appliance's domain name becomes unreachable and re-downloading isn't convenient.

Tags passed at agent invocation land only on the host device the agent runs on. Sub-objects the agent discovers on that host (containers on a Docker host, for example) arrive as separate, untagged objects linked to the parent. Find them by discovery timestamp if they need tagging retroactively.

## Verifying a collector is actually gone

Deleting a collector from the UI can be cosmetic: removing its database row does not necessarily stop the underlying service process, and things that were routing through it may keep working via a different, undocumented-looking path that never depended on the deleted row. Verify from server-side access logs what is still hitting the appliance, rather than trusting a UI element's absence as proof.

A DOQL view meant to enumerate a class of appliance may also filter out special or reserved primary-key rows. Absence from the view is not absence from the system; check the audit log by object id directly if a specific row's history matters.
