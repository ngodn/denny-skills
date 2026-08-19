# Schema and data design on JSM Assets

Design guidance that generalises beyond any one schema. Read this alongside the limits and endpoint gotchas in [SKILL.md](SKILL.md), which explain the platform constraints these patterns work around.

## Canonical asset keys

Give every object a canonical key that is opaque, immutable, and never reused. Do not derive the key from any encoded metadata (a device type prefix, a location code) that might need to change later; that turns a rename into a key change, and a key change breaks every stored reference to the object.

Keep source-system identifiers (an external CMDB's own primary key, a serial number, an inventory tag) in separate attributes rather than folding them into the canonical key. The canonical key identifies the object inside this schema; the source id identifies where it came from. Conflating them means a re-import or a source-system migration forces a key change across every reference.

## Grouping node placement

A grouping node (a team, a business unit, a classification bucket) sits under the deepest applicable existing node in the taxonomy, never invented as a shortcut and never placed at a level that mixes a classification node with a grouping node. When source data does not cleanly map to an existing leaf, find the right home in the existing tree rather than placing it under a "close enough" node.

Give unresolved rows an explicit ungrouped leaf under the correct parent. Never omit an unresolved row and never guess its home; an explicit ungrouped leaf keeps unresolved rows visible and countable instead of hiding them as silently-dropped or silently-misfiled data.

## Cascading-select emulation

Assets has no native cascading-select attribute across arbitrary depth (pick a value at level 1, the options at level 2 narrow to match). Emulate it by mirroring the object-type tree into a parallel set of mirror objects:

- One mirror object per child object type, at every non-leaf level of the tree. The mirror object's label is the child type's name, so it becomes the selectable option at that level.
- Every type at depth N (N >= 1) gets a reference attribute pointing at its parent level's mirror object.
- Every real object at depth N sets that reference attribute to the mirror object one level up whose label matches its own type's name.

Match mirror objects and their back-references by `(parent, name)` rather than by any generated id. That makes the whole build idempotent: re-running the build only creates what is missing, so it is safe to re-run repeatedly as the tree grows, rather than a one-shot script that has to be re-derived every time a new branch is added.

## Vendor and contract register design

For a vendor or contract register layered onto an existing CMDB schema, three decisions hold up across different taxonomies:

- **Separate a governed register from a discovery-noise catalogue with a scope attribute, not a parallel tree.** A discovery tool's own manufacturer or vendor list is noisy and uncurated. Rather than standing up a second vendor object type or a parallel sub-tree to hold the "real" governed vendors, add a scope attribute (a Select, for example "Governance Scope") to the existing vendor type and use it to distinguish governed entries from discovery noise. A parallel tree means re-linking every asset reference that already points at the discovery-derived vendor objects; a scope attribute does not.
- **Model a contract as its own object type under Vendor, not a date field on the vendor record.** One vendor commonly holds several contracts, each with an independent start date, renewal date, and terms. A single date field on the vendor object cannot represent more than one contract and cannot drive renewal automation correctly once a vendor has more than one active agreement.
- **Keep vendor-related request types in the existing ticketing project.** Vendor onboarding, contract renewal, and offboarding requests belong in the same project as the rest of the asset-management request family, not a separate project. A separate project for vendor/contract work adds process sprawl without a corresponding benefit; the requester and the fulfiller are usually the same team already working in the existing project.
