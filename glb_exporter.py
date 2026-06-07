"""
Exportador GLB (glTF 2.0 binário) para UE5 e O3DE.

Características:
  - Vertex colors RGB (sem textura — zero bleeding, funciona com NEAREST/BILINEAR)
  - Normais flat por face (vértices duplicados por face)
  - Triângulos (padrão glTF)
  - Escala configurável (voxel_size)
  - KHR_materials_unlit (shading flat — correto para voxels)
  - Um mesh por objeto do World View
  - Índices uint16 (<65535 verts) ou uint32 (fallback)
"""
import struct, json, os
from collections import defaultdict


# ── Normal por side ───────────────────────────────────────────────────────────
SIDE_NORMAL = {
    'xp': ( 1.0, 0.0, 0.0), 'xn': (-1.0, 0.0, 0.0),
    'yp': ( 0.0, 1.0, 0.0), 'yn': ( 0.0,-1.0, 0.0),
    'zp': ( 0.0, 0.0, 1.0), 'zn': ( 0.0, 0.0,-1.0),
}


# ── Empacotamento binário ──────────────────────────────────────────────────────
def _pack_f32(values):
    return struct.pack(f'<{len(values)}f', *values)

def _pack_u16(values):
    return struct.pack(f'<{len(values)}H', *values)

def _pack_u32(values):
    return struct.pack(f'<{len(values)}I', *values)

def _align4(data):
    pad = (4 - len(data) % 4) % 4
    return data + b'\x00' * pad


# ── Construção da mesh de um objeto ──────────────────────────────────────────
def _build_glb_mesh(vox_obj, palette, voxel_size):
    """
    Retorna (positions, normals, colors, indices) prontos para glTF.
    Vértices duplicados por face para normais flat corretas.
    Triângulos.
    """
    from greedy_obj_exporter import _build_object_mesh, SIDE_NORMAL_IDX

    vertices_local, polygons = _build_object_mesh(vox_obj)
    ox, oy, oz = vox_obj.offset
    s = voxel_size

    positions = []
    normals   = []
    colors    = []
    indices   = []
    vi        = 0  # índice de vértice atual

    for vis, side, color_idx in polygons:
        nx, ny, nz = SIDE_NORMAL[side]
        # Cor da paleta: color_idx é 1-based → palette[color_idx-1]
        cidx = max(0, min(255, color_idx-1))
        r, g, b = palette[cidx][:3]
        cr, cg, cb = r/255.0, g/255.0, b/255.0

        # 4 vértices do quad (coords globais escaladas)
        quad_pts = []
        for vi_local in vis:
            lx, ly, lz = vertices_local[vi_local-1]
            quad_pts.append(((lx+ox)*s, (ly+oy)*s, (lz+oz)*s))

        # Duplica os 4 vértices para esta face (flat shading)
        for pt in quad_pts:
            positions.extend(pt)
            normals.extend((nx, ny, nz))
            colors.extend((cr, cg, cb))

        # 2 triângulos do quad: [0,1,2] e [0,2,3]
        base = vi
        indices.extend([base, base+1, base+2,
                         base, base+2, base+3])
        vi += 4

    return positions, normals, colors, indices


# ── Montagem do GLB ───────────────────────────────────────────────────────────
def export_glb(path, scene, voxel_size=1.0):
    """
    Exporta VoxScene para GLB (glTF 2.0 binário).

    voxel_size : float
        UE5  → 1.0  (1 voxel = 1 cm)
        O3DE → 0.01 (1 voxel = 0.01 m = 1 cm)
    """
    # glTF acumula todos os dados num único buffer binário
    bin_data  = bytearray()
    accessors = []
    buffer_views = []
    meshes    = []
    nodes     = []

    def add_buffer_view(data, target=None):
        """Adiciona dados ao buffer e retorna o índice do buffer_view."""
        aligned = _align4(data)
        bv_idx = len(buffer_views)
        bv = {'buffer': 0, 'byteOffset': len(bin_data), 'byteLength': len(data)}
        if target:
            bv['target'] = target
        buffer_views.append(bv)
        bin_data.extend(aligned)
        return bv_idx

    def add_accessor(bv_idx, component_type, count, type_, min_=None, max_=None):
        """Adiciona um accessor e retorna seu índice."""
        acc = {
            'bufferView':    bv_idx,
            'byteOffset':    0,
            'componentType': component_type,
            'count':         count,
            'type':          type_,
        }
        if min_ is not None: acc['min'] = min_
        if max_ is not None: acc['max'] = max_
        idx = len(accessors)
        accessors.append(acc)
        return idx

    scene_node_indices = []

    for obj_i, vox_obj in enumerate(scene.objects):
        print(f'  {vox_obj.name}: {len(vox_obj.voxels)} voxels...', end=' ')

        positions, normals, colors, indices = _build_glb_mesh(vox_obj, scene.palette, voxel_size)

        n_verts = len(positions) // 3
        n_idx   = len(indices)

        use_u32 = n_verts > 65535

        # POSITIONS
        pos_bytes = _pack_f32(positions)
        bv_pos    = add_buffer_view(pos_bytes, target=34962)  # ARRAY_BUFFER
        xs = positions[0::3]; ys = positions[1::3]; zs = positions[2::3]
        acc_pos = add_accessor(bv_pos, 5126, n_verts, 'VEC3',
                               min_=[min(xs),min(ys),min(zs)],
                               max_=[max(xs),max(ys),max(zs)])

        # NORMALS
        nor_bytes = _pack_f32(normals)
        bv_nor    = add_buffer_view(nor_bytes, target=34962)
        acc_nor   = add_accessor(bv_nor, 5126, n_verts, 'VEC3')

        # COLOR_0 (RGB float32)
        col_bytes = _pack_f32(colors)
        bv_col    = add_buffer_view(col_bytes, target=34962)
        acc_col   = add_accessor(bv_col, 5126, n_verts, 'VEC3')

        # INDICES
        if use_u32:
            idx_bytes = _pack_u32(indices)
            bv_idx    = add_buffer_view(idx_bytes, target=34963)  # ELEMENT_ARRAY_BUFFER
            acc_idx   = add_accessor(bv_idx, 5125, n_idx, 'SCALAR',
                                     min_=[0], max_=[n_verts-1])
        else:
            idx_bytes = _pack_u16(indices)
            bv_idx    = add_buffer_view(idx_bytes, target=34963)
            acc_idx   = add_accessor(bv_idx, 5123, n_idx, 'SCALAR',
                                     min_=[0], max_=[n_verts-1])

        print(f'{n_verts} verts, {n_idx//3} tris')

        # Mesh
        mesh_idx = len(meshes)
        meshes.append({
            'name': vox_obj.name,
            'primitives': [{
                'attributes': {
                    'POSITION': acc_pos,
                    'NORMAL':   acc_nor,
                    'COLOR_0':  acc_col,
                },
                'indices':  acc_idx,
                'mode':     4,           # TRIANGLES
                'material': 0,
            }]
        })

        node_idx = len(nodes)
        nodes.append({'mesh': mesh_idx, 'name': vox_obj.name})
        scene_node_indices.append(node_idx)

    # Material único: KHR_materials_unlit (flat color, sem PBR)
    materials = [{
        'name': 'VoxelMaterial',
        'extensions': {'KHR_materials_unlit': {}},
        'pbrMetallicRoughness': {
            'baseColorFactor': [1.0, 1.0, 1.0, 1.0],
            'metallicFactor':  0.0,
            'roughnessFactor': 1.0,
        },
    }]

    gltf = {
        'asset': {'version': '2.0', 'generator': 'VoxGreedyMesher'},
        'extensionsUsed':     ['KHR_materials_unlit'],
        'extensionsRequired': ['KHR_materials_unlit'],
        'scene':      0,
        'scenes':     [{'nodes': scene_node_indices}],
        'nodes':      nodes,
        'meshes':     meshes,
        'materials':  materials,
        'accessors':  accessors,
        'bufferViews': buffer_views,
        'buffers':    [{'byteLength': len(bin_data)}],
    }

    json_bytes = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    # Spec glTF: chunk JSON alinhado a 4 bytes com padding 0x20 (espaço)
    while len(json_bytes) % 4 != 0:
        json_bytes += b' '

    # GLB header: magic + version + total_length
    # Chunk 0: JSON  (type 0x4E4F534A)
    # Chunk 1: BIN   (type 0x004E4942)
    json_chunk = struct.pack('<II', len(json_bytes), 0x4E4F534A) + json_bytes
    bin_bytes  = bytes(bin_data)
    # BIN chunk alinhado a 4 bytes com padding 0x00
    while len(bin_bytes) % 4 != 0:
        bin_bytes += b'\x00'
    bin_chunk  = struct.pack('<II', len(bin_bytes), 0x004E4942) + bin_bytes

    total_length = 12 + len(json_chunk) + len(bin_chunk)
    header = struct.pack('<III', 0x46546C67, 2, total_length)  # magic=glTF

    with open(path, 'wb') as f:
        f.write(header + json_chunk + bin_chunk)

    size_kb = os.path.getsize(path) / 1024
    print(f'\n--- GLB (voxel_size={voxel_size}) ---')
    print(f'Objetos  : {len(scene.objects)}')
    print(f'Arquivo  : {os.path.basename(path)} ({size_kb:.1f} KB)')
