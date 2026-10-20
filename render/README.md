# Render del tótem De Cosecha

Fotomontaje fotorrealista del tótem, renderizado con Blender 4.2 (Cycles, CPU).
El modelo está construido a escala real en metros a partir de la retícula del
artboard: **1 px del diseño = 5 mm**.

## Medidas que usa el modelo

| Pieza | Medida |
|---|---|
| Cara del tótem | 3,20 × 5,84 m |
| Cajón de cabecera | 2,90 × 1,70 m |
| Cajones de categoría (×3) | 2,90 × 1,20 m |
| Separación entre cajones | 80 mm |
| Marco perimetral | 150 mm |
| Zócalo | 0,32 m |
| Altura total | 6,16 m |

## Pipeline

1. `shoot-board.js` abre un artboard `.dc.html` del lienzo de diseño en
   Chromium, resuelve sus fuentes e imágenes y lo captura a 3× (1920 × 3504).
2. Un recorte según la retícula del diseño reparte esa cara en los cuatro
   archivos que consume el render: `art/logo.png`, `art/p1.png`, `art/p2.png`,
   `art/p3.png`.
3. `totem_scene.py` levanta la escena y renderiza.
4. `post.py` añade viñeteo y grano.

## Uso

```bash
# texturas a partir de otro artboard
node shoot-board.js <ruta>/V-S2.dc.html art

# encuadre rápido
python totem_scene.py --preview --res 440x550 --samples 34 --out out/test.png

# render final
python totem_scene.py --res 1400x1750 --samples 400 --out out/totem_hero.png
python post.py out/totem_hero.png out/totem_hero_final.jpg
```

Opciones útiles de `totem_scene.py`:

| Opción | Qué hace |
|---|---|
| `--elev` | Altura del sol en grados. Negativo = hora azul. |
| `--rot` | Giro del sol. 25 ilumina el frente y el costado visible. |
| `--emit` | Fuerza del retroiluminado de los cajones. |
| `--lens` `--fstop` | Objetivo y diafragma. |
| `--cam` `--look` | Posición de cámara y punto de enfoque. |
| `--tilt` | Deja que la cámara se incline. Por defecto las verticales quedan paralelas. |
| `--backdrop` | Añade arboleda lejana. Apagada: el encargo pide espacio minimalista. |

La cámara va a 70 mm con sensor de 36 mm y encuadra por desplazamiento
vertical, como un objetivo descentrable, para que las verticales del tótem no
converjan. Es como se fotografía señalética.
