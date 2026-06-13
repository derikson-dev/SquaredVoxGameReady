# SquaredVoxGameReady

> **MagicaVoxel → Greedy Mesh (C ext) → Native Bake → Engine-ready FBX**
>
> A Blender 5.1 add-on that converts `.vox` files into highly optimized meshes,
> working entirely in memory. It uses C-accelerated greedy meshing and resolves
> T-junctions on the fly to export clean assets for Bevy 0.18, UE5, and O3DE.

---

## Overview

MagicaVoxel stores voxel art as a 3D grid of cubes. A naive export of a 32³ model
can produce hundreds of thousands of useless faces. **SquaredVoxGameReady** fixes
this by collapsing coplanar faces of the same color into the largest possible
quads (greedy meshing).

The project started as a command-line (CLI) pipeline and is now a **monolithic,
native Blender add-on**. Geometry is built directly in memory (`bpy.data.meshes`),
with no temporary `.obj` files. The core algorithm is written in C for maximum
speed, even on very dense models.

```text
.vox file
  → Blender import (greedy C ext + T-junction resolver)
  → Blender bake (1 tile per color + internal UV map)
  → optimized FBX export
```

## Features

- **100% in-memory (Blender add-on):** No temporary files. The `.vox` becomes an
  optimized mesh directly in the viewport.
- **C-accelerated greedy meshing:** Core algorithm written in plain C, processing
  slices in milliseconds (up to ~15x faster than the previous NumPy version).
- **T-junction resolution in C:** Stitches quad seams to produce clean, manifold
  meshes.
- **High-performance bake:** Texture baked with one tile per color (no bleeding),
  generating exact UVs from per-vertex color attributes.
- **Hierarchy preserved:** Supports MagicaVoxel's World View, keeping multiple
  objects and their global offsets.
- **Custom scale:** 1.0 by default (Bevy 0.18 / UE5) or 0.01 for O3DE.
- **Smart fallback:** If the C libraries are not compiled, the add-on switches
  automatically to the pure-Python engine.

## Requirements & Installation

### 1. Compile the C extensions

For maximum speed, compile the binaries (`.pyd`) using the Python interpreter
bundled with Blender 5.1.

Open a terminal/PowerShell in the project folder and run (adjusting your Blender
path):

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe" setup.py build_ext --inplace
```

This produces `greedy_mesher_ext...pyd` and `tjunction_resolver...pyd`.

> If the extensions are not compiled, the add-on still works through its
> pure-Python fallback (slower on dense models).

### 2. Install the add-on in Blender

1. Open Blender 5.1.
2. Go to **Edit > Preferences > Add-ons**.
3. Click the top dropdown and choose **Install from Disk...**.
4. Select `squared_voxel_optimizer.py` and enable it.

## How to Use

With the add-on enabled, open the sidebar in the View3D (press **N**) and find the
**Squared VOR** tab, which contains the **Squared Voxel Optimizer** panel:

1. **Import:** Click **Import and Optimize .Vox** and select your art. The mesh is
   created already optimized in the scene. With **Show Optimization Report**
   enabled, a popup reports raw vs. optimized face counts and the geometry
   reduction.
2. **Settings:**
   - **Texture Resolution:** POT sizes from 128 up to 2048 (default 1024).
   - **Voxel Size:** 1.0 for Bevy/UE5, 0.01 for O3DE.
   - **Save in imported .vox folder:** writes the baked texture next to the
     source `.vox` (otherwise it is saved next to the .blend file).
3. **Bake:** With the model selected, click **Bake**. The baked texture, UVs, and
   material are created and applied instantly.
4. **Export:** Click **Export FBX** to generate the final, engine-ready model
   (selection only, textures embedded).

## Repository Structure

```text
SquaredVoxGameReady/
├── squared_voxel_optimizer.py  # Main add-on (core, UI, bake, operators)
├── setup.py                    # Build script for the C extensions
├── greedy_mesher_ext.c         # Greedy meshing logic (high performance)
├── tjunction_resolver.c        # Seam / quad resolution (high performance)
├── .gitignore                  # Ignore rules for binaries and cache
└── README.md                   # Project documentation
```

## Roadmap (completed)

- [x] **Phase 1 — Python performance:** Mesher accelerated with NumPy.
- [x] **Phase 2 — Bake pipeline (CLI):** UV texture + FBX via headless Blender.
- [x] **Phase 3 — C extensions:** Core rewritten in C (`greedy_mesher_ext.c`),
      cutting times down to milliseconds.
- [x] **Phase 4 — Monolithic Blender add-on:** Fully native `bpy` pipeline with an
      in-memory workflow (`squared_voxel_optimizer.py`).

## License

MIT — free to modify and use in your indie projects.
