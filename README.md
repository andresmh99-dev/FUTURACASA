# Lote 8, Manzana 147 — Fraccionamiento México (Morelia, Mich.)

Expediente digital interactivo y repositorio abierto para el proyecto residencial **Lote 8, Manzana 147**, ubicado en el Fraccionamiento México, Colonia Puerto de Buenavista, Morelia, Michoacán. Listo para publicar directamente en **GitHub Pages** sin paso de compilación.

## Qué incluye este sitio
- **Recorrido Virtual 360° Fotorealista (Blender 5 Cycles 3K · Geometría 1:1 exacta)**: 8 paradas equirectangulares (`3072×1536`) renderizadas sobre las medidas reales de obra (`15.07 m × 20.60 m`, Sótano `Z = -2.893 m`, Patio `Z = -3.093 m`, Cochera `Z = -0.620 m`, Planta Alta `Z = +0.150 m`, Techo `Z = +3.060 m`) con hotspots interactivos, transiciones suaves, indicador de nivel y descarga del archivo abierto `.blend`.
- **Maqueta 3D Interactiva abierta (Three.js)**: visor WebGL con 7 paradas guiadas, modo *Caminar dentro* (`WASD` / flechas / cruceta móvil), toggles por nivel (*Azotea*, *1ª Planta*, *Sótano*), corte horizontal y **exportación directa a `.GLB`** (formato abierto).
- **Galería de 5 Renders Arquitectónicos** con visor Lightbox a pantalla completa.
- **Poligonal Topográfica Interactiva (SVG a escala real desde UTM)** sincronizada con el **Cuadro de Construcción** (`281.30 m²`, perímetro `68.23 m`).
- **Visor Dual de Planos Oficiales (PDF)**: alterna entre la **Lámina Arquitectónica A-1** (*Arq. Salvador Emmanuel Valencia Contreras*) y el **Levantamiento Topográfico Hoja 1 de 2** (*Arq. José Alberto Méndez Aguilar*).

## Cuadro de Construcción (UTM)

| Lado (EST → PV) | Rumbo | Distancia (m) | Vértice | UTM X | UTM Y | Colindancia |
| --- | --- | ---: | :---: | ---: | ---: | --- |
| 1 → 2 | S 59° 44' 21" W | 13.06 | 2 | 276,452.185 | 2,178,455.250 | Lote 9 |
| 2 → 3 | S 24° 31' 18" E | 20.10 | 3 | 276,460.527 | 2,178,436.963 | Calle |
| 3 → 4 | N 59° 44' 21" E | 15.07 | 4 | 276,473.544 | 2,178,444.557 | Calle Zacamixtle |
| 4 → 1 | N 30° 15' 39" W | 20.00 | 1 | 276,463.465 | 2,178,461.832 | Lote 7 |

## Estructura del repositorio

```text
.
├── index.html                                  # Sitio web interactivo (listo para GitHub Pages)
├── styles.css                                  # Estilos arquitectónicos y diseño responsive
├── app.js                                      # Poligonal SVG UTM, lightbox y selector dual PDF
├── tour360.js                                  # Visor 360° Three.js con hotspots (8 paradas 1:1)
├── casa-l8-model.js                            # Modelo 3D paramétrico abierto
├── viewer3d.js                                 # Visor 3D interactivo, caminar libre y exportador .GLB
├── .nojekyll                                   # Desactiva Jekyll en GitHub Pages
├── blender/
│   ├── casa_l8_mexico.blend                    # Proyecto abierto editable en Blender 5 (1:1 exacto)
│   └── render_tour_360.py                      # Script reproducible Cycles + OptiX (panoramas 3K)
└── assets/
    ├── plano-arquitectonico-A1.pdf             # Lámina arquitectónica A-1
    ├── levantamiento-topografico-lote8.pdf     # Levantamiento topográfico oficial (Hoja 1 de 2)
    ├── L8_MEXICO_SKP_3.skp                     # Archivo original SketchUp 2025 (referencia)
    ├── L8_MEXICO_SKP_3.glb                     # Geometría base abierta GLB (1:1 exacto)
    ├── modelo-skp-preview.png                  # Vista previa extraída del .skp
    ├── galeria/                                # 5 renders arquitectónicos de referencia
    └── panoramas/                              # 8 panoramas 360° 3K renderizados en Blender 5 Cycles
```

## Regenerar los panoramas 360° en Blender 5

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" --background --python "blender\render_tour_360.py"
```

## Cómo publicar en GitHub Pages

1. Crea un repositorio vacío en https://github.com/new (por ejemplo, `lote8-fracc-mexico`).
2. Conecta este repositorio local y sube la rama `main`:
   ```powershell
   git remote add origin https://github.com/TU-USUARIO/lote8-fracc-mexico.git
   git push -u origin main
   ```
3. En GitHub, ve a **Settings → Pages**, elige **Source: Deploy from a branch**, rama **`main`** y carpeta **`/ (root)`**, y guarda.
