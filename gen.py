import numpy as np
from PIL import Image, ImageDraw, ImageFont


RUTA = "cyberpunk.png"
COLUMNAS_ASCII = 200
FUENTE_ARCHIVO = "consola.ttf"   
TAM_FUENTE = 14
FONDO_OSCURO = True            
GAMMA = 0.6            
USAR_PERCENTILES = True
AVIVAR_COLOR = 0.7     


def cargar_imagen(ruta):
    """Devuelve el RGB como decimales, shape (alto, ancho, 3)."""
    return np.asarray(Image.open(ruta).convert("RGB")).astype(float)

def luminancia(rgb):
    """Un número de brillo por píxel, shape (alto, ancho)."""
    pesos = np.array([0.2126, 0.7152, 0.0722])
    return rgb @ pesos

def bloque_a_caracter(bloque, simbolos_orden, dens_norm, fondo_oscuro):
    t = bloque.mean() / 255
    if not fondo_oscuro:
        t = 1 - t
    return simbolos_orden[np.abs(dens_norm - t).argmin()]

def densidad(simbolo, fuente, ancho_celda, alto_celda):
    celda = Image.new("L", (ancho_celda, alto_celda), 0)
    ImageDraw.Draw(celda).text((0, 0), simbolo, fill=255, font=fuente)
    return np.asarray(celda).mean() / 255

fuente = ImageFont.truetype(FUENTE_ARCHIVO, TAM_FUENTE)
ancho_celda = round(fuente.getlength("M"))
alto_celda = sum(fuente.getmetrics())      # ascenso + descenso

simbolos = [chr(i) for i in range(32, 127)]    # los 95 imprimibles
densidades = {s: densidad(s, fuente, ancho_celda, alto_celda) for s in simbolos}
RAMPA_BASE = "".join(sorted(simbolos, key=densidades.get, reverse=True))

simbolos_orden = RAMPA_BASE[::-1]
dens_norm = np.array([densidades[s] for s in simbolos_orden])
dens_norm = dens_norm / dens_norm.max()
rampa = RAMPA_BASE[::-1] if FONDO_OSCURO else RAMPA_BASE


rgb = cargar_imagen(RUTA)
L = luminancia(rgb)
if USAR_PERCENTILES:
    lo, hi = np.percentile(L, [2, 98])
    L = np.clip((L - lo) / (hi - lo), 0, 1) * 255
L = 255 * (L / 255) ** GAMMA
H, W = L.shape
bw = max(1, W // COLUMNAS_ASCII)
bh = max(1, round(bw * alto_celda / ancho_celda))   

# Recortar
Hc, Wc = H - H % bh, W - W % bw
L = L[:Hc, :Wc]
rgb = rgb[:Hc, :Wc]

ny, nx = Hc // bh, Wc // bw
bloques = L.reshape(ny, bh, nx, bw).swapaxes(1, 2)             
colores = rgb.reshape(ny, bh, nx, bw, 3).mean(axis=(1, 3))     
maximo = np.maximum(colores.max(axis=2, keepdims=True), 1)
vivos = colores / maximo * 255
colores = colores * (1 - AVIVAR_COLOR) + vivos * AVIVAR_COLOR
#text
lineas = []          
lineas_color = []    
for i in range(ny):
    plano = ""
    con_color = ""
    for j in range(nx):
        c = bloque_a_caracter(bloques[i, j], simbolos_orden,dens_norm,FONDO_OSCURO)
        r, g, b = (int(v) for v in colores[i, j])
        plano += c
        con_color += f"\033[38;2;{r};{g};{b}m{c}\033[0m"
    lineas.append(plano)
    lineas_color.append(con_color)

print("\n".join(lineas_color))

with open("salida_ascii.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lineas))

#pasaje a imagen
fondo = (0, 0, 0) if FONDO_OSCURO else (255, 255, 255)
imagen = Image.new("RGB", (nx * ancho_celda, ny * alto_celda), fondo)
dibujo = ImageDraw.Draw(imagen)

for i in range(ny):
    for j in range(nx):
        simbolo = lineas[i][j]
        if simbolo == " ":
            continue                     
        color = tuple(int(v) for v in colores[i, j])
        dibujo.text((j * ancho_celda, i * alto_celda), simbolo, fill=color, font=fuente)

imagen.save("salida_ascii.png")
print(f"\nPNG guardado: {imagen.size[0]}x{imagen.size[1]} px")