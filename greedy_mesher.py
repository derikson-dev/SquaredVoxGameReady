def greedy_mesh_plane(model, axis, direction):
    voxels = {(x, y, z): color for x, y, z, color in model.voxels}
    sx, sy, sz = model.size

    # Mapeamento: para cada eixo de varredura, define
    #   size_u, size_v  → dimensões do plano 2-D da máscara
    #   size_w          → dimensão perpendicular (profundidade da fatia)
    #   coord_global(u, v, w)   → converte (u,v,w) locais para (x,y,z) globais
    #   coord_vizinho(u, v, w)  → vizinho na direção do normal
    #
    # Convenção adotada e mantida consistente com o exportador:
    #   axis=x  → w=X, u=Y, v=Z   (a face varre Y×Z)
    #   axis=y  → w=Y, u=X, v=Z   (a face varre X×Z)
    #   axis=z  → w=Z, u=X, v=Y   (a face varre X×Y)

    if axis == "x":
        size_w, size_u, size_v = sx, sy, sz
        coord_global  = lambda u, v, w: (w, u, v)
        coord_vizinho = lambda u, v, w: (w + direction, u, v)
    elif axis == "y":
        size_w, size_u, size_v = sy, sx, sz
        coord_global  = lambda u, v, w: (u, w, v)
        coord_vizinho = lambda u, v, w: (u, w + direction, v)
    elif axis == "z":
        size_w, size_u, size_v = sz, sx, sy
        coord_global  = lambda u, v, w: (u, v, w)
        coord_vizinho = lambda u, v, w: (u, v, w + direction)
    else:
        raise ValueError("Eixo inválido.")

    quads = []

    for w in range(size_w):
        # Monta a máscara 2-D desta fatia
        mask = [[None] * size_v for _ in range(size_u)]

        for u in range(size_u):
            for v in range(size_v):
                pos_atual   = coord_global(u, v, w)
                pos_vizinha = coord_vizinho(u, v, w)

                if pos_atual not in voxels:
                    continue
                # Só expõe a face se o vizinho na direção do normal estiver vazio
                if pos_vizinha in voxels:
                    continue

                mask[u][v] = voxels[pos_atual]

        used = [[False] * size_v for _ in range(size_u)]

        for u in range(size_u):
            for v in range(size_v):
                color = mask[u][v]
                if color is None or used[u][v]:
                    continue

                # Expande em U
                width = 1
                while (
                    u + width < size_u
                    and mask[u + width][v] == color
                    and not used[u + width][v]
                ):
                    width += 1

                # Expande em V
                height = 1
                done = False
                while v + height < size_v and not done:
                    for uu in range(u, u + width):
                        if mask[uu][v + height] != color or used[uu][v + height]:
                            done = True
                            break
                    if not done:
                        height += 1

                # Marca como usadas
                for uu in range(u, u + width):
                    for vv in range(v, v + height):
                        used[uu][vv] = True

                # Tupla: (u, v, w, width, height, color)
                # Semântica por eixo:
                #   x: u=Y_global, v=Z_global, w=X_global, width=ΔY, height=ΔZ
                #   y: u=X_global, v=Z_global, w=Y_global, width=ΔX, height=ΔZ
                #   z: u=X_global, v=Y_global, w=Z_global, width=ΔX, height=ΔY
                quads.append((u, v, w, width, height, color))

    return quads


def greedy_mesh_xp(model): return greedy_mesh_plane(model, "x",  1)
def greedy_mesh_xn(model): return greedy_mesh_plane(model, "x", -1)
def greedy_mesh_yp(model): return greedy_mesh_plane(model, "y",  1)
def greedy_mesh_yn(model): return greedy_mesh_plane(model, "y", -1)
def greedy_mesh_zp(model): return greedy_mesh_plane(model, "z",  1)
def greedy_mesh_zn(model): return greedy_mesh_plane(model, "z", -1)