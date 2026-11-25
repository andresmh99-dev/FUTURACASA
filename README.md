# Lote 8, Manzana 147 — Fraccionamiento México (Morelia, Mich.)

Sitio web estático y repositorio de archivos técnicos para el **Levantamiento Topográfico Arquitectónico** y el **Modelo 3D en SketchUp** del predio **Lote 8, Manzana 147**, ubicado en el Fraccionamiento México, Colonia Puerto de Buenavista, Morelia, Michoacán.

## Resumen del predio

| Dato | Valor |
| --- | --- |
| **Propiedad** | Lote 8, Manzana 147, Fraccionamiento México |
| **Ubicación** | Col. Puerto de Buenavista, Morelia, Michoacán |
| **Área total** | **281.30 m²** |
| **Perímetro** | **68.23 m** |
| **Escala del plano** | 1:100 · Cotas en metros · Curvas de nivel c/ 0.50 m |
| **Instrumentación** | Estación total electrónica · Coordenadas UTM (aprox. 5 m) |
| **Fecha** | 16 de junio de 2025 (Hoja 1 de 2) |
| **Responsable** | Topografía Profesional de Morelia — Arq. José Alberto Méndez Aguilar (Céd. Prof. 2177829 / D.R.O. 301) |

## Cuadro de Construcción

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
├── styles.css                                  # Estilos arquitectónicos y responsive
├── app.js                                      # Poligonal SVG a escala real, tabla y lightbox
├── casa-l8-model.js                            # Modelo 3D paramétrico abierto (desde Plano A-1)
├── viewer3d.js                                 # Visor Three.js, recorrido 7 paradas y exportador .GLB
├── .nojekyll                                   # Desactiva Jekyll en GitHub Pages
└── assets/
    ├── plano-arquitectonico-A1.pdf             # Plano arquitectónico A-1 (Plantas, Sección y Fachadas)
    ├── levantamiento-topografico-lote8.pdf     # Plano topográfico oficial (Hoja 1 de 2)
    ├── L8_MEXICO_SKP_3.skp                     # Archivo original SketchUp 2025 (referencia)
    ├── L8_MEXICO_SKP_3.glb                     # Conversión GLB previa (referencia)
    ├── modelo-skp-preview.png                  # Vista previa extraída del archivo .skp
    └── galeria/                                # 5 renders arquitectónicos (fachadas, patio e interior)
```

## Cómo publicar en GitHub Pages

1. Crea un repositorio vacío en [GitHub](https://github.com/new) (por ejemplo, `lote8-fracc-mexico`).
2. Conecta este repositorio local y sube la rama principal:

```bash
git remote add origin https://github.com/TU-USUARIO/lote8-fracc-mexico.git
git branch -M main
git push -u origin main
```

3. En GitHub, ve a **Settings → Pages**, selecciona **Source: Deploy from a branch**, rama **`main`** y carpeta **`/ (root)`**, y guarda. En ~1 minuto tu sitio quedará publicado en `https://TU-USUARIO.github.io/lote8-fracc-mexico/`.
