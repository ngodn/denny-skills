# Contact measurement on skinned meshes

How to measure where one skinned surface passes into another (body against limbs, a garment against the
body, anything against the floor) across animations and body sliders, without a week of instrument bugs.

## Instrument

- Start from a library inside test: a generalized winding number (libigl, MeshLib `FastWindingNumber`) or
  Open3D `RaycastingScene` signed distance and occupancy. A hand-rolled ray-parity test on open skin
  patches produces false deep hits.
- Open shells (garments, cut-out skin patches) need border-face rejection and a capped search radius. A
  point in front of the body can still sit "behind" a distant back surface; accept a penetration only
  with opposing normals and a multi-ray containment majority.
- Whole-body containment does not say which part holds the point. For per-part attribution (thigh or
  torso, arm or chest), close each anatomical region with temporary caps and test containment per region;
  take the depth from the real skin triangles, never the caps.
- Label a maximum near the search cap as search-limited; report area as an estimate unless it is an exact
  clipped area.

## Controls before data

- Run known-answer controls first: clearly penetrating, clearly separated, border, closed solid.
- Break nearest-face ties by index so cached and rebuilt searches give the same rows.
- Every speed-up (cached BVH, compiled helper, evaluating one partner only) is checked row by row against
  the full evaluator before it replaces it; keep the comparison as evidence.
- Read the shipped drivers (blueprint bytecode, cooked curves) for morph stages and slider ranges; old
  authoring scripts can disagree with what ships.

## Sweeps

- Count cases and estimate time before launching (looks x poses x settings x frames x seconds per case).
- Thresholds such as "the chest size where contact starts" come from a coarse grid plus bisection to the
  needed precision, evaluating only the partner under test inside the bisection.
- Physics (secondary motion) runs only where the static gap is smaller than the measured swing; elsewhere
  record the gap and skip.
- Render only the cases a person will review: the worst per subject and pose, plus named diagnostics.
