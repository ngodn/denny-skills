# SNMP discovery traps

## v1/v2c and v3 can be mutually exclusive

On some SNMP agents, v1/v2c and v3 are mutually exclusive at the device level: enabling v3 makes the agent stop answering v1/v2c entirely. Whether v3 is even available at all is release/firmware-dependent; check vendor release notes before assuming it. Confirm with whoever else already polls the device via v2c before flipping the version, or an unrelated monitoring tool silently breaks. Default rule of thumb: prefer v3 for security if nothing else depends on v2c; if something does, keep the existing v2c credential or create a new one rather than forcing a device-wide version flip.

## The localized-key trap

Some SNMP agents derive the SNMPv3 authentication key from the device's own base MAC or engine ID when a "localized" key form is configured. Copying a `snmp-server user ... localized <engineID> ...` config line from one device to another produces a key cryptographically welded to the original device. It fails authentication everywhere else, silently. Device42's discovery UI collapses this to a generic "no_auth" error, which is not diagnostic; don't trust it as the whole story.

Fix: delete and re-create the SNMPv3 user with the plaintext password, so the agent re-localizes the key to its own engine ID.

A second, independent failure mode on the same class of device: the user authenticates fine but the referenced SNMP view for read access was never defined, surfacing as "No more variables left in this MIB View" at the OID root. Fix by defining the view (`snmp-server view <name> iso included`).

## Diagnostic technique: read elapsed time, run the raw walk

Elapsed time in the discovery job log tells you which layer failed:

- A full timeout means no network path at all.
- A sub-second failure means the host is reachable and the request was rejected at a higher layer (auth, view).

Run the raw SNMP walk directly from the collector appliance (Device42's "Generate SNMP Output" tool) rather than trusting the collapsed job-log error. The raw walk surfaces the actual failing layer.

## Building a multi-credential job through the API

The create/update endpoint for an SNMP network discovery job accepts one v3 credential pair per call. Calling it again with the same job name and a different credential-id pair appends a second credential row rather than replacing the first, verified empirically. This is how you build up a single job to try multiple SNMPv3 credentials against a device range. Omitting the target-server field on a follow-up call leaves the existing target list untouched, so calls can be layered safely. An undocumented `snmp_timeout` parameter is accepted and honoured by the endpoint even though it is not in the public API docs.
