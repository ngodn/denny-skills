## What it does

`device42` is a working reference for running Device42 discovery reliably and querying its data through DOQL. It covers the appliance architecture (Main Appliance, Remote Collector, Windows Discovery Service), Windows and SNMP discovery ports and authentication, least-privilege service account design, and the quirks of DOQL and the cloud resource data model.

The defining constraint: Windows and Linux/Unix discovery jobs do not ping a target before connecting, so in an ICMP-blocked network they don't fail fast, they fail slow, running every unreachable host to a full connection timeout.

## When to reach for it

Type `/device42`, or the agent reaches for it automatically when a Device42 task fits.

| Situation | Reach for |
|---|---|
| Setting up or debugging a Windows, Linux/Unix, or SNMP discovery job | `device42` |
| Designing a least-privilege discovery service account | `device42` |
| Writing or debugging a DOQL query, or working with the cloud resource views | `device42` |
| Designing the sync itself, once data is out of Device42 and going into another CMDB | [cmdb-sync](../engineering/cmdb-sync.md) |
| Choosing an isolation level or lock for the sync's own writes | [acid-transactions](../engineering/acid-transactions.md) |

## Discovery pre-check behaviour

The one table worth memorising:

| Job type | Pre-check | In an ICMP-blocked network |
|---|---|---|
| Windows (WMI/WinRM) | None | Runs unreachable hosts to full timeout |
| Linux/Unix (SSH) | None | Same |
| SNMP network autodiscovery | ICMP-or-TCP-port-check, on by default | Silently finds nothing until unchecked |

Three sibling files carry the depth the skill reads on demand: [WINDOWS-DISCOVERY.md](../../skills/engineering/device42/WINDOWS-DISCOVERY.md) for ports, ADM's local-admin requirement, the least-privilege pattern, and the WMI/SCM permission-grant technique; [SNMP.md](../../skills/engineering/device42/SNMP.md) for version exclusivity and the localized-key trap; [DOQL-AND-API.md](../../skills/engineering/device42/DOQL-AND-API.md) for query quirks, the cloud data model, and agent behaviour.

## Common questions

**Why does `Test-NetConnection` say the host is unreachable when I can clearly SSH into it?**

`PingSucceeded: False` is meaningless wherever ICMP is policy-blocked; it shows against a perfectly healthy host too. Read `TcpTestSucceeded` instead, and don't raise a network ticket off the ping line.

**My WMI permission-grant script wiped out permissions I didn't touch.**

That happens when a raw security descriptor gets captured from one place and applied wholesale elsewhere: it replaces the whole DACL. The fix is read-modify-write, get the current descriptor, append or remove the one ACE you care about, write the modified array back. The same applies to Service Control Manager access through SDDL.

**Why did my SNMPv3 credential fail with a generic auth error right after I copied it from another device?**

Some agents localize the SNMPv3 key to the device's own engine ID. A config line copied between devices carries a key welded to the original device, and it fails everywhere else with an error that doesn't say why. Delete and re-create the user with the plaintext password so it re-localizes.

**Why does my DOQL query 500 with no useful message?**

Two syntax patterns cause a flat 500: a regex brace quantifier like `{2}`, and a SQL line comment (`--`) anywhere in the query, even a trailing one after otherwise valid SQL. Write the regex out longhand and keep notes outside the query string.

## It's working if

- A Windows or Linux/Unix discovery job is built from a known target list, not a speculative subnet sweep, in any environment where ICMP might be blocked.
- A least-privilege discovery account is a domain group grant, not an individual account grant, and rotates without touching every target.
- A DOQL query avoids `{n}` regex bounds and inline `--` comments, and wraps nullable columns before negating them.
- A security finding about an over-privileged discovery account gets a remediation naming the specific feature driving the privilege (ADM, Hyper-V visibility), not a blanket "reduce permissions" note.

## Where it fits

`device42` is a **reach-for-it-anytime standalone**: platform reference for one specific CMDB/discovery product, not a step in a chain. Its natural neighbour is [cmdb-sync](../engineering/cmdb-sync.md), which picks up once data needs to move from Device42, or any other source, into a target CMDB. For the whole map, [ask-denny](../engineering/ask-denny.md).
