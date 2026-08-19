---
name: device42
description: Working reference for Device42 discovery, authentication, and DOQL querying. Use when the user sets up or troubleshoots a Device42 discovery job (WMI, SSH, SNMP), configures a Windows Discovery Service or WMI enabler script, designs a least-privilege discovery account, debugs discovery in an ICMP-blocked network, writes or debugs a DOQL query, or works with Device42's cloud resource or agent data model.
---

# Device42

Reference for running Device42 discovery reliably and querying its data. The single fact that changes behaviour most: Windows and Linux/Unix discovery jobs do not ping before connecting, so in an ICMP-blocked environment they don't fail fast, they fail slow.

## Architecture

- **Main Appliance (MA)**: hosts the CMDB, orchestrates discovery, holds integrations, serves reports.
- **Remote Collector (RC)**: a lightweight satellite placed per network zone or cloud account, runs discovery jobs, reports to the MA over HTTPS 443. One RC per cloud account or tenancy keeps cloud API traffic off on-prem egress and respects tenancy boundaries.
- **Windows Discovery Service (WDS)**: a .NET service on a domain-joined Windows host that performs WMI-based discovery and reports to an RC. It must run as a domain account, never Local System, because Local System cannot authenticate remotely.

Sizing guidance changes between releases. Check Device42's published sizing guide rather than trusting a copy. As of writing it was roughly: small/medium estate (under 2,500 devices) MA at 4 vCPU / 16 GB / 150 GB SSD; medium/large (over 2,500 devices, or with ADM + Resource Utilisation + Storage enabled) MA at 16 vCPU / 64 GB / 150 GB SSD; one RC per 1,000 workloads at 2 vCPU / 4 GB / 50 GB; one WDS per 1,000 Windows targets at 2 vCPU / 8 GB / 50 GB.

## Discovery pre-check behaviour by protocol

This is the highest-value fact here.

| Job type | ICMP/port pre-check | In an ICMP-blocked environment |
|---|---|---|
| Windows (WMI/WinRM) | None. Connects straight to the protocol port. | Unreachable host runs to full connection timeout instead of being skipped. |
| Linux/Unix (SSH) | None. Same as above. | Same as above. |
| SNMP network autodiscovery | Has an ICMP-or-TCP-port-check option, on by default. | Job silently finds nothing until the option is unchecked. |

Never point a Windows or Linux/Unix job at a speculative subnet sweep across a mixed-liveness range: it will crawl through full timeouts on every dead host. Build the job from a known target list instead. For SNMP autodiscovery in an ICMP-blocked environment, uncheck the pre-check option first, or the job returns nothing with no error explaining why.

### The Test-NetConnection red herring

`Test-NetConnection` reports `PingSucceeded: False` against a perfectly reachable host whenever ICMP is policy-blocked. That line is meaningless in that environment. Read `TcpTestSucceeded` instead. Don't raise a network ticket off the ping line alone.

## Windows discovery: ports, privilege, and least privilege

See [WINDOWS-DISCOVERY.md](WINDOWS-DISCOVERY.md) for:

- WMI/DCOM and WinRM port requirements, and why keeping both sets in one firewall request avoids a second approval cycle
- why Application Dependency Mapping (ADM) requires local administrator and plain discovery does not
- the domain-joined vs workgroup auth setting, and why leaving it wrong is itself a finding
- the least-privilege pattern (a domain group, not an individual account)
- the WMI and Service Control Manager permission-grant technique that keeps an enabler script idempotent
- bulk deployment options, ranked, with the real tradeoff for each
- testing a Windows-targeting script without a Windows box

## SNMP

See [SNMP.md](SNMP.md) for the v1/v2c vs v3 exclusivity trap, the localized-key trap, the elapsed-time diagnostic technique, and building a job with multiple v3 credential sets through the API.

## DOQL and the API

See [DOQL-AND-API.md](DOQL-AND-API.md) for DOQL syntax and quirks, the cloud resource data model, the raw-IP access pattern, agent binary behaviour, and verifying a collector is actually gone.

## Agent vs agentless

Agentless (WMI/SSH/SNMP from an RC or WDS) is the default. The installable agent is a segment-level substitution, not a replacement: it dials out to the MA on 443 instead of being dialled into, which suits a segment where inbound discovery ports are unacceptable. It does not cover Resource Utilisation trending or database discovery. Decide this per segment, not once for the whole estate.

## The over-privileged discovery account finding

A security review flagging "network-wide WMI execution" or "full Hyper-V admin access" on a discovery account usually traces back to specific product features, not misconfigured WMI rights: the documented minimum WMI grant already excludes remote code execution. The two real drivers are ADM's local-admin requirement and a Hyper-V-visibility fallback some versions implement via full Hyper-V Administrators membership instead of a scoped read path.

A defensible remediation: hybrid deployment, an agent on the sensitive segments and Hyper-V hosts, agentless everywhere else re-scoped to the documented minimum with firewall rules limited to the collector's own address, tiered service accounts instead of one shared account, interactive logon denied on the account, and alerting on any interactive logon for that account as a canary.
