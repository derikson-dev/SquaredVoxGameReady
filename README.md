Markdown

# SquaredVoxGameReady

> **MagicaVoxel → Greedy Mesh (C Ext) → Bake Nativo → Engine-ready FBX**
>
> Add-on para Blender 5.1 que converte arquivos `.vox` em geometrias altamente otimizadas operando 100% na memória. Utiliza algoritmos de _Greedy Meshing_ acelerados em C e resolve T-Junctions em tempo real para exportar assets perfeitos para Bevy 0.18, UE5 e O3DE.

---

## 🎯 Visão Geral

O MagicaVoxel armazena arte voxel como um grid 3D de cubos. Uma exportação nativa de um modelo 32³ pode gerar centenas de milhares de faces inúteis. O **SquaredVoxGameReady** resolve isso colapsando faces coplanares da mesma cor nos maiores _quads_ possíveis (Greedy Meshing).

O projeto evoluiu de um pipeline de scripts em linha de comando (CLI) para um **Add-on Monolítico nativo do Blender**. Agora, a geometria é construída diretamente na memória (`bpy.data.meshes`), sem gerar arquivos `.obj` temporários. O algoritmo foi reescrito em C (Fase 3), garantindo velocidade máxima mesmo para modelos muito densos.

```text
Arquivo .vox
  → Blender Import (Greedy C Ext + T-Junction Resolver)
  → Blender Bake (1 tile por cor + UV map interno)
  → Exportação FBX Otimizada

✨ Features Principais

    100% In-Memory (Blender Add-on): Fim dos arquivos temporários. O .vox vira malha otimizada instantaneamente na Viewport.

    C-Accelerated Greedy Meshing: Algoritmo reescrito em C puro, processando fatias em milissegundos (até 15x mais rápido que a versão anterior em Numpy).

    T-Junction Resolution em C: Sela as emendas dos quads gerando malhas manifold impecáveis.

    Bake de Alta Performance: Textura assada com 1 tile por cor (sem sangramento/bleeding), gerando UVs exatas baseadas nos atributos de cor dos vértices.

    Hierarquia Preservada: Suporta o World View do MagicaVoxel, mantendo múltiplos objetos e seus respectivos offsets globais.

    Escala Customizável: 1.0 padrão para Bevy 0.18 e UE5, ou 0.01 para O3DE.

    Fallback Inteligente: Se as bibliotecas em C não estiverem compiladas, o Add-on alterna automaticamente para o motor em Python puro.

⚙️ Pré-requisitos e Instalação
1. Compilar as Extensões C (Fase 3)

Para garantir a velocidade máxima, você precisa compilar os binários (.pyd) usando o interpretador Python embutido no Blender 5.1.

Abra o terminal/PowerShell na pasta do projeto e execute (ajustando o caminho do seu Blender):
PowerShell

& "C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe" setup.py build_ext --inplace

Isso gerará os arquivos greedy_mesher_ext...pyd e tjunction_resolver...pyd.
2. Instalar o Add-on no Blender

    Abra o Blender 5.1.

    Vá em Edit > Preferences > Add-ons.

    Clique na setinha superior e escolha Install from Disk... (ou simplesmente arraste o arquivo se estiver usando extensões locais).

    Selecione o arquivo squared_voxel_optimizer.py e ative-o.

🚀 Como Usar

Com o Add-on ativado, abra a aba lateral na View3D (pressione N) e localize o painel Sqrd Voxel Optimizer:

    Import: Clique em Import .VOX e selecione sua arte. A malha já nascerá otimizada na cena.

    Configurações: - Defina a Texture Resolution (ex: 1024).

        Defina o Voxel Size (1.0 para Bevy/UE5, 0.01 para O3DE).

    Bake: Com o modelo selecionado, clique em Bake. A textura e o material serão criados e aplicados instantaneamente.

    Export: Clique em Export FBX para gerar o modelo final pronto para sua engine.

📂 Estrutura do Monorepo

Com a adoção da Clean Architecture e a remoção das dependências legadas, o projeto agora é altamente focado:
Plaintext

SquaredVoxGameReady/
├── squared_voxel_optimizer.py  # Add-on principal (Core, UI, Bake, Operadores)
├── setup.py                    # Script de build para as extensões C
├── greedy_mesher_ext.c         # Lógica do Greedy Meshing (Alta performance)
├── tjunction_resolver.c        # Resolução de frestas e quads (Alta performance)
├── .gitignore                  # Regras de exclusão de binários e cache
└── README.md                   # Documentação do projeto

🗺️ Roadmap (Concluído)

    [x] Fase 1 — Performance Python: Algoritmo mesher acelerado com numpy.

    [x] Fase 2 — Bake pipeline CLI: Textura UV + FBX via Blender headless.

    [x] Fase 3 — Extensão C/C++: Núcleo reescrito em C (greedy_mesher_ext.c) reduzindo tempos para milissegundos.

    [x] Fase 4 — Blender Add-on Monolítico: Pipeline 100% nativo no Blender via API bpy com fluxo de trabalho in-memory (squared_voxel_optimizer.py).

📄 Licença

MIT — sinta-se à vontade para modificar e usar nos seus projetos indie.
```
