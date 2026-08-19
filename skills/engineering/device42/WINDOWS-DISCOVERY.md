# Windows discovery: ports, privilege, and least privilege

## Port requirements

| Path | Ports | Notes |
|---|---|---|
| WMI/DCOM | TCP 135 (RPC endpoint mapper) | Always required, discovery cannot start without it. |
| WMI/DCOM | Dynamic RPC, high range | 49152-65535 for Server 2008+/Vista+ (a modern estate); 1024-65535 is the older, wider legacy span. |
| WMI/DCOM | NetBIOS 137/138/139, SMB 445 | Optional/legacy. Windows 2000+ uses 445 instead of NetBIOS. |
| WMI/DCOM, domain-joined targets | Kerberos 88 TCP/UDP, both directions | The WDS is the Kerberos client requesting a service ticket; the target validates it via its own domain membership. Usually already open on a domain network, so this is a confirmation, not a new rule. |
| WinRM | 5985/5986 | Removes the need for a WDS host entirely. |

WinRM vs WMI is a decision Device42 leaves open per deployment. Put both port sets in the same firewall request or workbook, so either path can be approved later without a second approval cycle.

## ADM forces local administrator, plain discovery does not

Application Dependency Mapping (ADM) requires local Administrator on every target, unavoidably. Device42 documents exactly two ADM data-collection methods, and both write connection data to a path only the local Administrators group can write to (default `ADMIN$`/`IPC$`; the alternative, a custom Windows share, still needs the same admin write access). Treat this as a security conversation to have before rollout, not a config toggle to route around.

Plain WMI discovery needs none of that. It needs only the documented minimum WMI namespace rights: Enable Account, Remote Enable, Read Security on `Root\CIMv2`, `Root\DEFAULT`, `Root\StandardCimv2`, plus optional namespaces for Hyper-V, IIS, SQL, SCCM, or Cluster if those are in scope.

## Domain-joined vs workgroup auth

`AllowAnonymousCallback` and `LocalAccountTokenFilterPolicy` exist to let a local, non-domain account authenticate remotely. On a domain-joined target they should be off, because a domain account authenticating against the domain needs neither. Leaving `LocalAccountTokenFilterPolicy = 1` on a domain machine re-enables full-token remote admin for local accounts, which hardening baselines require to stay off. Finding this set wrong on a domain estate is itself a security finding, not just a discovery blocker.

## Least privilege

A domain-joined machine still has its own local SAM and local groups, and a local group (Distributed COM Users, for example) can contain a domain group as a member. So: create one domain security group, put the discovery service account in it, then grant the group, not the individual account, into local groups and namespace ACLs on every target. Rotating or replacing the account later then needs no per-endpoint change.

## The permission-grant technique: read, modify, write

Grant WMI namespace permissions by reading the current security descriptor, appending the new ACE (or filtering one out for removal) into the existing DACL array in place, then writing the modified array back. Never capture a raw security-descriptor byte array from one place and apply it elsewhere wholesale: that replaces the whole DACL and destroys every other permission already on the namespace.

```
$security = Invoke-WmiMethod ... -Name GetSecurityDescriptor
# append or remove the one ACE you care about, in place, on $security.Descriptor.DACL
Invoke-WmiMethod ... -Name SetSecurityDescriptor -ArgumentList $security.Descriptor
```

The same principle applies to Service Control Manager access. Read the current SDDL string with `sc.exe sdshow`, insert the new ACE textually after the `D:` prefix (SDDL is `D:(ace)(ace)...S:(ace)...`), then `sc.exe sdset scmanager "<new SDDL>"`. Never build an SDDL string from scratch. Read-modify-write on the live descriptor is what makes a permission-grant script idempotent and safe to re-run; a captured-and-replayed descriptor is not.

## Bulk deployment, ranked

| Option | Tradeoff |
|---|---|
| GPO Immediate Task (Scheduled Tasks preference) | Runs as SYSTEM, applies on the next background GPO refresh (about 90 minutes plus up to 30 minutes of jitter), no reboot required. Usually the best default. |
| GPO Startup Script | Only fires at boot, so every target needs a reboot first. A real operational cost on a live estate. |
| SCCM Configuration Baseline (detection + remediation) | Best when ConfigMgr is already deployed: self-heals on a schedule and gives a compliance percentage useful as sign-off evidence. Only reaches hosts with a healthy ConfigMgr client. Ansible is a viable substitute in a non-Windows-native shop. |

## Testing without a Windows box

Unit-level: run the script inside the official `mcr.microsoft.com/powershell` container image, with a mock harness that stubs every external cmdlet it calls (`Get-WmiObject`, `Invoke-WmiMethod`, `Get-LocalGroup*`, `Get-ItemProperty`, `Get-Service`, `Get-NetFirewallRule`, and a mock `net` function), then assert behaviour across synthetic host profiles, at minimum a modern host and a legacy host.

End-to-end: `dockur/windows`, a Docker-based Windows-in-a-container project reachable through a web-based remote desktop, spins up a disposable Windows target to observe the real discovery sequence, including confirming pre-check behaviour empirically rather than trusting documentation alone.
