# Gera assets/avatar.png no estilo duotone pontilhado (verde-escuro + laranja)
import numpy as np
from PIL import Image, ImageOps

PX = 3                      # tamanho do "pixel"
ESCURO = np.array([22, 78, 72])     # verde petroleo
CLARO = np.array([240, 128, 86])    # laranja
FUNDO = np.array([214, 196, 160])   # bege

img = Image.open("assets/foto.png").convert("L")
msk = Image.open("assets/mask.png").convert("L")
S = 1024
w, h = img.size
box = (int(w*.12), int(h*.02), int(w*.88), int(h*.78))   # enquadra cabeca e ombros
img = img.crop(box).resize((S, S), Image.LANCZOS)
msk = msk.crop(box).resize((S, S), Image.LANCZOS)
n = S // PX
g = np.asarray(img.resize((n, n), Image.BOX), float) / 255
m = np.asarray(msk.resize((n, n), Image.BOX), float) / 255
bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16
th = np.tile(bayer, (n // 4 + 1, n // 4 + 1))[:n, :n]
pv = g[m > .5]
lo, hi = np.percentile(pv, 3), np.percentile(pv, 97)
g = np.clip((g - lo) / (hi - lo), 0, 1) ** 1.6      # contraste so na pessoa, sombras mais fortes
claro = g > th
out = np.where(claro[..., None], CLARO, ESCURO)
out = np.where((m > .5)[..., None], out, FUNDO).astype(np.uint8)
Image.fromarray(out).resize((S, S), Image.NEAREST).save("assets/avatar.png")
print("ok")
