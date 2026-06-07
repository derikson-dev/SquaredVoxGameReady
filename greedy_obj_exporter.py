"""
Exportador OBJ engine-ready para UE5 e O3DE.
  - Normais flat explícitas por face (f v/vt/vn)
  - UVs de paleta
  - Escala configurável
  - Triangulação opcional
"""
import os, struct, zlib
from collections import defaultdict, Counter


# ── Paleta PNG ───────────────────────────────────────────────────────────────

def salvar_textura_paleta(path, palette):
    linha = bytearray([0])
    for i in range(256):
        r, g, b = palette[i][:3]
        linha.extend([r, g, b])
    def chunk(tag, dados):
        crc = zlib.crc32(tag + dados) & 0xFFFFFFFF
        return struct.pack('>I', len(dados)) + tag + dados + struct.pack('>I', crc)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', 256, 1, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(linha)))
           + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


# ── Normais flat (6 direções do greedy) ──────────────────────────────────────
# Índice 1-based no OBJ: xp=1, xn=2, yp=3, yn=4, zp=5, zn=6
SIDE_NORMAL = {
    'xp': ( 1, 0, 0), 'xn': (-1, 0, 0),
    'yp': ( 0, 1, 0), 'yn': ( 0,-1, 0),
    'zp': ( 0, 0, 1), 'zn': ( 0, 0,-1),
}
SIDE_NORMAL_IDX = {'xp':1,'xn':2,'yp':3,'yn':4,'zp':5,'zn':6}
NORMALS_LIST = [
    ( 1, 0, 0), (-1, 0, 0),
    ( 0, 1, 0), ( 0,-1, 0),
    ( 0, 0, 1), ( 0, 0,-1),
]


# ── Geometria greedy → vértices ───────────────────────────────────────────────
def _quad_verts(side, u, v, w, width, height):
    if side=='xp': return[(w+1,u,v),(w+1,u+width,v),(w+1,u+width,v+height),(w+1,u,v+height)]
    elif side=='xn': return[(w,u,v+height),(w,u+width,v+height),(w,u+width,v),(w,u,v)]
    elif side=='yp': return[(u,w+1,v+height),(u+width,w+1,v+height),(u+width,w+1,v),(u,w+1,v)]
    elif side=='yn': return[(u,w,v),(u+width,w,v),(u+width,w,v+height),(u,w,v+height)]
    elif side=='zp': return[(u,v,w+1),(u+width,v,w+1),(u+width,v+height,w+1),(u,v+height,w+1)]
    else:            return[(u,v+height,w),(u+width,v+height,w),(u+width,v,w),(u,v,w)]


# ── T-junction resolution (quad split) ───────────────────────────────────────
def _pt_strictly_between(p, a, b):
    for i in range(3):
        if a[i] != b[i]:
            lo, hi = min(a[i],b[i]), max(a[i],b[i])
            return all(p[j]==a[j] for j in range(3) if j!=i) and lo<p[i]<hi
    return False

def _build_edge_map(polygons):
    em = defaultdict(list)
    for fi, (vis, _side, _color) in enumerate(polygons):
        n = len(vis)
        for i in range(n):
            a, b = vis[i], vis[(i+1)%n]
            em[tuple(sorted([a,b]))].append((fi, i))
    return em

def resolver_tjunctions_quad_split(raw_quads):
    """
    raw_quads: [(lista_4_verts, side, color_idx)]
    Retorna (vertices, polygons) onde polygons = [(vis, side, color_idx)]
    100% quads puros, selado, manifold.
    """
    vertex_map = {}; vertices = []
    def gv(pt):
        if pt not in vertex_map: vertex_map[pt]=len(vertices)+1; vertices.append(pt)
        return vertex_map[pt]

    polygons = [([gv(v) for v in verts], side, color) for verts, side, color in raw_quads]

    for _ in range(60):
        em = _build_edge_map(polygons)
        open_edges = {e: fl[0] for e, fl in em.items() if len(fl)==1}
        if not open_edges: break

        face_tjoints = defaultdict(list)
        for (ea,eb),(fi,ei) in open_edges.items():
            va, vb = vertices[ea-1], vertices[eb-1]
            for vi in range(1, len(vertices)+1):
                if vi!=ea and vi!=eb and _pt_strictly_between(vertices[vi-1], va, vb):
                    face_tjoints[fi].append((ea, eb, vi))
        if not face_tjoints: break

        new_polygons = []
        for fi, (vis, side, color) in enumerate(polygons):
            if fi not in face_tjoints:
                new_polygons.append((vis, side, color)); continue
            coords = [vertices[vi-1] for vi in vis]
            fixed_ax = next((ax for ax in range(3) if len(set(c[ax] for c in coords))==1), None)
            if fixed_ax is None:
                new_polygons.append((vis, side, color)); continue
            fixed_val = coords[0][fixed_ax]
            ax0, ax1 = [i for i in range(3) if i!=fixed_ax]
            u_vals = sorted(set(c[ax0] for c in coords))
            v_vals = sorted(set(c[ax1] for c in coords))
            for ea,eb,t_vi in face_tjoints[fi]:
                tp = vertices[t_vi-1]
                u_vals.append(tp[ax0]); v_vals.append(tp[ax1])
            u_vals = sorted(set(u_vals)); v_vals = sorted(set(v_vals))
            n = len(coords)
            area2 = sum(coords[i][ax0]*coords[(i+1)%n][ax1]-coords[(i+1)%n][ax0]*coords[i][ax1] for i in range(n))
            ccw = area2 > 0
            u0,u1 = min(c[ax0] for c in coords), max(c[ax0] for c in coords)
            v0,v1 = min(c[ax1] for c in coords), max(c[ax1] for c in coords)
            def m3(u,v,_ax0=ax0,_ax1=ax1,_fax=fixed_ax,_fv=fixed_val):
                p=[0,0,0]; p[_ax0]=u; p[_ax1]=v; p[_fax]=_fv; return tuple(p)
            for i in range(len(u_vals)-1):
                for j in range(len(v_vals)-1):
                    uu0,uu1=u_vals[i],u_vals[i+1]; vv0,vv1=v_vals[j],v_vals[j+1]
                    if uu0<u0 or uu1>u1 or vv0<v0 or vv1>v1: continue
                    if ccw: q=[gv(m3(uu0,vv0)),gv(m3(uu1,vv0)),gv(m3(uu1,vv1)),gv(m3(uu0,vv1))]
                    else:   q=[gv(m3(uu0,vv1)),gv(m3(uu1,vv1)),gv(m3(uu1,vv0)),gv(m3(uu0,vv0))]
                    new_polygons.append((q, side, color))
        polygons = new_polygons
    return vertices, polygons


# ── Mesh de um VoxObject ──────────────────────────────────────────────────────
def _build_object_mesh(vox_obj):
    from greedy_mesher import (greedy_mesh_xp,greedy_mesh_xn,
                               greedy_mesh_yp,greedy_mesh_yn,
                               greedy_mesh_zp,greedy_mesh_zn)
    sides = [('xp',greedy_mesh_xp),('xn',greedy_mesh_xn),
             ('yp',greedy_mesh_yp),('yn',greedy_mesh_yn),
             ('zp',greedy_mesh_zp),('zn',greedy_mesh_zn)]
    raw_quads = []
    for side, fn in sides:
        for u,v,w,width,height,color in fn(vox_obj):
            raw_quads.append((_quad_verts(side,u,v,w,width,height), side, color))
    return resolver_tjunctions_quad_split(raw_quads)


# ── Triangulação de quads ─────────────────────────────────────────────────────
def _triangulate(vis):
    """Divide quad [a,b,c,d] em dois tris: [a,b,c] e [a,c,d]."""
    a,b,c,d = vis
    return [a,b,c], [a,c,d]


# ── Exportador OBJ ────────────────────────────────────────────────────────────
def export_greedy_obj(path, scene, voxel_size=1.0, triangulate=False):
    """
    Exporta OBJ engine-ready.

    voxel_size : float
        Escala de cada voxel em unidades da engine.
        UE5  → 1.0  (1 voxel = 1 cm, UE5 usa cm)
        O3DE → 0.01 (1 voxel = 1 cm = 0.01 m, O3DE usa metros)

    triangulate : bool
        False = quads (Blender, O3DE glTF)
        True  = triângulos (máxima compatibilidade)
    """
    base     = os.path.splitext(path)[0]
    mtl_path = base + '.mtl'
    png_path = base + '_palette.png'

    salvar_textura_paleta(png_path, scene.palette)
    with open(mtl_path, 'w') as f:
        f.write('newmtl VoxelMaterial\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\n')
        f.write(f'map_Kd {os.path.basename(png_path)}\n')

    total_verts = total_polys = 0

    with open(path, 'w') as f:
        f.write(f'mtllib {os.path.basename(mtl_path)}\n')
        f.write(f'# Voxel Greedy OBJ | voxel_size={voxel_size} | tris={triangulate}\n\n')

        # 6 normais flat globais
        for nx, ny, nz in NORMALS_LIST:
            f.write(f'vn {float(nx):.1f} {float(ny):.1f} {float(nz):.1f}\n')
        f.write('\n')

        # UVs de paleta
        for i in range(256):
            f.write(f'vt {(i+0.5)/256.0:.6f} 0.500000\n')
        f.write('\n')

        vertex_offset = 0

        for obj in scene.objects:
            vertices, polygons = _build_object_mesh(obj)
            ox, oy, oz = obj.offset

            # Topologia
            ec = defaultdict(int)
            for vis,_,_ in polygons:
                n=len(vis)
                for i in range(n): ec[tuple(sorted([vis[i],vis[(i+1)%n]]))]+= 1
            n_open = sum(1 for c in ec.values() if c==1)
            n_nm   = sum(1 for c in ec.values() if c>2)
            status = '✓' if n_open==0 and n_nm==0 else f'⚠ open={n_open} nm={n_nm}'
            print(f'  {obj.name}: {len(vertices)} verts, {len(polygons)} quads [{status}]')

            f.write(f'o {obj.name}\n')
            s = voxel_size
            for lx,ly,lz in vertices:
                f.write(f'v {(lx+ox)*s:.6f} {(ly+oy)*s:.6f} {(lz+oz)*s:.6f}\n')
            f.write('usemtl VoxelMaterial\ns off\n')

            for vis, side, color_idx in polygons:
                vt  = max(1, min(256, color_idx))
                vni = SIDE_NORMAL_IDX[side]
                vo  = vertex_offset
                if triangulate:
                    t1, t2 = _triangulate(vis)
                    def fmt_tri(tri):
                        return ' '.join(f'{vi+vo}/{vt}/{vni}' for vi in tri)
                    f.write(f'f {fmt_tri(t1)}\n')
                    f.write(f'f {fmt_tri(t2)}\n')
                else:
                    verts_str = ' '.join(f'{vi+vo}/{vt}/{vni}' for vi in vis)
                    f.write(f'f {verts_str}\n')

            f.write('\n')
            vertex_offset += len(vertices)
            total_verts   += len(vertices)
            total_polys   += len(polygons)

    prim_count = total_polys*2 if triangulate else total_polys
    prim_label = 'tris' if triangulate else 'quads'
    print(f'\n--- OBJ ({prim_label}, voxel_size={voxel_size}) ---')
    print(f'Objetos  : {len(scene.objects)}')
    print(f'Vértices : {total_verts}')
    print(f'{prim_label.capitalize():8} : {prim_count}')