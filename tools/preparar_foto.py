# Roda uma vez, localmente (precisa de opencv): realca olhos/detalhes do rosto
# e salva assets/foto_ascii.png, que o gerar.py usa no lugar da foto original.
import cv2
g = cv2.cvtColor(cv2.imread("assets/foto.png"), cv2.COLOR_BGR2GRAY)
g = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(6, 6)).apply(g)
cv2.imwrite("assets/foto_ascii.png", g)
print("ok")
