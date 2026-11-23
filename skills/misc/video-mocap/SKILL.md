---
name: video-mocap
description: Turn monocular video of people into game animation, a camera track and face curves on a local GPU. Use when capturing body, hands, face or camera from footage (SAM 3 tracking, SAM 3D Body, ViPE, MediaPipe, GVHMR-style tools), calling ComfyUI nodes from Python, fitting capture onto a 12 GB GPU, or checking capture quality against the source video.
---

# Video mocap

Footage in, per-shot animation + camera + face curves out. Stages, each with its own cache and report:
shot cuts > person tracks and identity > per-frame body + hands > camera > shared world frame > face and
gaze > cleanup > retarget > engine import. Judge every stage against the source frames with numbers, not
by eye.

## Look at the footage first

Before any model runs, build a contact sheet of the whole video (one frame per 10 s) and classify shots
yourself: wide (all bodies in view), POV (the camera operator is a performer and mostly unseen),
close-ups. Third-party scene labels (a "POV" flag, segment boundaries) are hints; they miss shots and do
not align with cuts. Pick the first test slice from a long wide shot with every body in view.

## GPU is shared

- Check what holds the GPU (`nvidia-smi --query-compute-apps=pid,used_memory --format=csv`) before every
  GPU stage. A running game or editor the user is using wins: do CPU stages meanwhile, never squeeze it.
- Run one GPU stage per process. Model managers keep the previous model resident; a second model in the
  same process runs out of memory.

## ComfyUI nodes from plain Python

Calling `Node.execute(...)` directly skips the executor, so:
- wrap the whole run in `torch.inference_mode()`; without it autograd keeps every activation (a DINOv3
  body backbone hit 9+ GB at batch 4);
- set precision through `comfy.options.enable_args_parsing()` + `sys.argv` before `import nodes`;
- SAM 3D Body hand refinement crashes in fp16 ("mat1 and mat2 must have the same dtype ... Float and
  Half"); ComfyUI picks fp16 on Ampere, so run `--force-fp32` (about 8 GB at batch 8 with hands) or patch;
- avoid its BVH export (broken rest pose); export raw MHR parameters or the skinned GLB;
- SAM 3D Body output axes: `pred_vertices`, `pred_keypoints_3d` and `pred_joint_coords` are camera axes
  (x right, y down, z forward, metres, add `pred_cam_t`), but `pred_global_rots` are MHR y-up axes:
  `R_cam = diag(1, -1, -1) @ R`. Check: each MHR bone's x axis runs along the bone (|cos| about 0.97 after
  the flip, 0.71 before). Joint names are not in ComfyUI; take them from the official MHR assets
  (`lod6.fbx` bones after `body_world`, same order as `mhr.skel_joint_parents`).

Measured on an RTX 3060 12 GB, 1080p, two people: SAM 3.1 tracking at 960x540 about 0.5 s/frame,
2.7 GB; SAM 3D Body fp32 with hands, batch 8, 2.85 s/frame, 5.7 GB peak. The fp16 crash is in
`forward_decoder` (keypoint prompt): `prev_estimate` arrives fp32; cast it to `image_embeddings.dtype`
before `prev_to_token`. Patched fp16 runs 2.4x faster (about 1.1 s/frame, 4.2 GB) and matches fp32 on
visible people (0.5 px, hands within 3 cm); occluded hands can flip between precisions either way. Track at reduced size: track masks are stored packed and
resized per frame by the body node.

## Per-stage traps

- **Identity** restarts at every cut: label people per shot (cheap with two), do not trust tracker ids
  across cuts.
- **Depth between people:** per-person models solve each body's distance on its own. Partners holding
  hands came out 87 to 99 cm apart with only 3 to 4 px 2D error. Pair placement and contact constraints
  come before smoothing.
- **Depth outliers:** a single frame can put a person absurdly far away (151 m in one 360-frame clip).
  Detect and repair isolated depth jumps (logged) before any temporal loss, or one frame dominates it.
- **Soft supports:** people on a mattress or cushion sink into it. A hard "nothing below the plane"
  constraint fights the video (4 to 5 px drift, outliers to 520 px on a two-person bed shot). Lowering
  only the plane weight is not enough when a final pass lifts the pair clear of the plane: that lift
  (3.6 cm median, 16.7 cm max at 2.2 m) shifted both bodies about 30 px. Allow a sink depth in both the
  optimisation and the final lift.
- **Shape lock** (one shape/scale per person per clip) removes size drift but not jitter; jitter needs the
  temporal pass.
- **Independent 2D checker** (RTMPose/RTMW whole-body): run it top-down on each tracked box. Its own
  person detector missed a person in 31% of frames of a two-person clip and saw a third person in others.
- **Face:** MediaPipe Face Landmarker fails on wide shots (one face in 450 frames) because its detector
  shrinks the full frame. Crop each head from the body model's face keypoints (MHR70 0 to 4: nose, eyes,
  ears), pad about 1.8x the span, resize to 256 px, one VIDEO-mode landmarker per person. It drops out
  past about 80 degrees yaw or 50% occlusion; profile spans need another source or hand keys.
- **Camera:** store per-frame pose plus both HFOV and VFOV. When game bodies differ from the actors,
  place the game camera relative to body landmarks so framing matches, not raw metres.

## Tooling traps

- ViPE on a new CUDA: build for your GPU only (`TORCH_CUDA_ARCH_LIST=8.6` on a 3060, about 16 min);
  CCCL 3 removed `thrust::tuple/get/make_tuple` (port to `cuda::std`); its pinned `gtsam-develop` may be
  gone from PyPI (override the pin); `import torch` before `vipe_ext` or it cannot find `libc10.so`.
  It reads at most 1000 frames per stream by default: run per shot.
- Take a game character's proportions from its mesh bind or its shipped clips' local tracks, not the
  Skeleton asset's reference pose: on one UE character the Skeleton reference had a 43.7 cm thigh while
  the mesh and every shipped clip used 51.5 cm.
- Name every imported source skeleton per capture and person (not just "person 0"). A retarget step that
  skips import when an asset of that name already exists will silently drive the new motion with an
  older capture's bone lengths.
- Keep each tool in its own venv (`uv venv` per tool under a vendor folder); pins conflict.
- Licences: SMPL, SMPL-X, MANO and FLAME (and tools built on them) carry use restrictions beyond
  non-commercial; SAM 3D Body (SAM License) and its MHR rig (Apache 2.0) do not. Record each tool's
  licence before its output ships, and let the owner decide.
