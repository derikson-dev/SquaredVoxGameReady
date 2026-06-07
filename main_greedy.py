"""
Pipeline VOX → OBJ / GLB

Uso:
    python main_greedy.py arquivo.vox           → gera .obj + .glb
    python main_greedy.py arquivo.vox .obj      → só OBJ
    python main_greedy.py arquivo.vox .glb      → só GLB
    python main_greedy.py arquivo.vox .obj .glb → ambos (explícito)

Opções de escala (editar VOXEL_SIZE abaixo):
    1.0  → UE5  (usa centímetros, 1 voxel = 1 cm)
    0.01 → O3DE (usa metros,      1 voxel = 1 cm = 0.01 m)

Opção de triangulação (editar TRIANGULATE abaixo):
    False → quads (Blender, loop cuts)
    True  → triângulos (máxima compatibilidade)

Nota sobre FBX:
    FBX requer a SDK proprietária da Autodesk e não é suportado
    em Python puro. UE5 e O3DE importam GLB nativamente com
    qualidade equivalente ou superior ao FBX.
"""
import sys
import os
from vox_reader import load_vox
from greedy_obj_exporter import export_greedy_obj
from glb_exporter import export_glb

# ── Configuração ──────────────────────────────────────────────────────────────
VOXEL_SIZE  = 1.0     # UE5: 1.0  |  O3DE: 0.01
TRIANGULATE = False   # OBJ: False = quads  |  True = triângulos
# ─────────────────────────────────────────────────────────────────────────────

FORMATOS_VALIDOS = {'.obj', '.glb'}

def uso():
    print('Uso: python main_greedy.py arquivo.vox [.obj] [.glb]')
    print()
    print('  Sem formato  → gera .obj e .glb')
    print('  .obj         → só OBJ  (Blender, quads, loop cuts)')
    print('  .glb         → só GLB  (UE5, O3DE, Blender — vertex colors)')
    print()
    print('Exemplos:')
    print('  python main_greedy.py ShapeTest.vox')
    print('  python main_greedy.py ShapeTest.vox .glb')
    print('  python main_greedy.py ShapeTest.vox .obj .glb')
    sys.exit(1)

def main():
    args = sys.argv[1:]

    if not args:
        uso()

    # Primeiro argumento: arquivo .vox
    vox_path = args[0]
    if not vox_path.endswith('.vox'):
        print(f'Erro: "{vox_path}" não é um arquivo .vox')
        uso()
    if not os.path.exists(vox_path):
        print(f'Erro: arquivo "{vox_path}" não encontrado')
        sys.exit(1)

    # Demais argumentos: formatos desejados
    formatos_pedidos = [a.lower() for a in args[1:]]

    # Valida formatos
    for f in formatos_pedidos:
        if f not in FORMATOS_VALIDOS:
            print(f'Erro: formato "{f}" não suportado. Use .obj ou .glb')
            print('Nota: .fbx requer SDK Autodesk (não disponível em Python puro)')
            uso()

    # Se nenhum formato especificado → gera ambos
    if not formatos_pedidos:
        formatos_pedidos = ['.obj', '.glb']

    # Remove duplicatas mantendo ordem
    formatos = list(dict.fromkeys(formatos_pedidos))

    base = os.path.splitext(vox_path)[0]

    # Carrega a cena
    print(f'Carregando {vox_path}...')
    scene = load_vox(vox_path)
    print(f'Objetos : {len(scene.objects)}')
    for obj in scene.objects:
        print(f'  {obj.name}: {len(obj.voxels)} voxels, size={obj.size}')
    print()

    # Exporta nos formatos pedidos
    for fmt in formatos:
        if fmt == '.obj':
            out = base + '_Greedy.obj'
            print(f'Exportando OBJ → {out}')
            export_greedy_obj(out, scene,
                              voxel_size=VOXEL_SIZE,
                              triangulate=TRIANGULATE)
            print()

        elif fmt == '.glb':
            out = base + '_Greedy.glb'
            print(f'Exportando GLB → {out}')
            export_glb(out, scene, voxel_size=VOXEL_SIZE)
            print()

    print('Concluído!')

if __name__ == '__main__':
    main()