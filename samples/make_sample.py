"""
Gerador de imagens sintéticas para o Voxel Inspector.
Cria um bracket (peça em L com reforço diagonal) em silhueta clara contra
fundo escuro, em 4 variantes:
  1. OK            — sem defeitos
  2. WARPING       — bordas inferiores deformadas (descolamento da mesa)
  3. CAMADA        — linhas horizontais de falha de fusão
  4. BURACO        — buraco/falha de extrusão no corpo

Saída: PNGs 1280x720 em ./captures/
"""

import os
import numpy as np
import cv2

# ---------- Configuração geral ----------
W, H = 1280, 720
BG_COLOR = (28, 28, 32)         # fundo escuro contrastante (BGR)
PART_COLOR = (192, 196, 200)    # alumínio claro
PART_SHADOW = (140, 144, 150)   # sombra/lateral
PART_HIGHLIGHT = (220, 222, 226)
OUT_DIR = "captures"

os.makedirs(OUT_DIR, exist_ok=True)


def make_background():
    """Fundo escuro com leve gradiente vertical pra parecer mesa real."""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        # gradiente: mais escuro em cima, levemente mais claro embaixo
        r = int(BG_COLOR[2] * (0.85 + 0.25 * t))
        g = int(BG_COLOR[1] * (0.85 + 0.25 * t))
        b = int(BG_COLOR[0] * (0.85 + 0.25 * t))
        img[y, :] = (b, g, r)
    # ruído sutil pra parecer textura de superfície
    noise = np.random.normal(0, 4, (H, W, 3)).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    return img


def bracket_polygon():
    """
    Retorna os vértices do bracket em L com reforço diagonal,
    centralizado horizontalmente, apoiado na parte inferior.
    """
    cx = W // 2
    base_y = H - 120     # linha de "mesa" onde a peça apoia
    height = 460
    base_w = 520         # largura da base
    wall_w = 110         # espessura da parede vertical
    base_h = 90          # altura da base horizontal

    left = cx - base_w // 2
    right = cx + base_w // 2
    top = base_y - height

    # Polígono externo do L (base + parede vertical à esquerda)
    pts = np.array([
        [left, base_y],                # canto inferior esquerdo
        [left, top],                   # canto superior esquerdo
        [left + wall_w, top],          # topo da parede
        [left + wall_w, base_y - base_h],  # cotovelo interno
        [right, base_y - base_h],      # quina interna direita da base
        [right, base_y],               # canto inferior direito
    ], dtype=np.int32)

    # Reforço diagonal (triângulo) que liga a parede vertical à base
    diag = np.array([
        [left + wall_w, top + 80],
        [left + wall_w, base_y - base_h],
        [right - 60, base_y - base_h],
    ], dtype=np.int32)

    return pts, diag, (left, right, top, base_y, base_h, wall_w)


def draw_bracket(img, with_holes=True):
    """Desenha o bracket base (sem defeitos). Retorna img + dimensões."""
    pts, diag, dims = bracket_polygon()
    left, right, top, base_y, base_h, wall_w = dims

    # Sombra projetada da peça na "mesa" — elipse escura embaixo
    shadow = img.copy()
    cv2.ellipse(shadow, (W // 2, base_y + 20), (320, 30), 0, 0, 360, (10, 10, 12), -1)
    img = cv2.addWeighted(shadow, 0.6, img, 0.4, 0)

    # Corpo principal preenchido
    cv2.fillPoly(img, [pts], PART_COLOR)
    cv2.fillPoly(img, [diag], PART_COLOR)

    # Sombreamento lateral direito da parede vertical (dá volume)
    side_shade = np.array([
        [left + wall_w - 20, top + 8],
        [left + wall_w, top],
        [left + wall_w, base_y - base_h],
        [left + wall_w - 20, base_y - base_h - 8],
    ], dtype=np.int32)
    cv2.fillPoly(img, [side_shade], PART_SHADOW)

    # Sombreamento inferior da base (frente da peça)
    front_shade = np.array([
        [left, base_y],
        [left + 18, base_y - 16],
        [right - 18, base_y - 16],
        [right, base_y],
    ], dtype=np.int32)
    cv2.fillPoly(img, [front_shade], PART_SHADOW)

    # Highlight superior da parede (brilho sutil)
    cv2.line(img, (left + 4, top + 6), (left + wall_w - 6, top + 6),
             PART_HIGHLIGHT, 3, lineType=cv2.LINE_AA)

    # Furos de parafuso (3 na parede vertical + 3 na base)
    if with_holes:
        # parede vertical — 3 furos
        wall_cx = left + wall_w // 2
        for i, ratio in enumerate([0.18, 0.50, 0.82]):
            y = int(top + (base_y - base_h - top) * ratio)
            cv2.circle(img, (wall_cx, y), 14, (40, 40, 44), -1, lineType=cv2.LINE_AA)
            cv2.circle(img, (wall_cx, y), 14, (20, 20, 22), 2, lineType=cv2.LINE_AA)

        # base — 3 furos
        base_cy = base_y - base_h // 2
        for ratio in [0.30, 0.58, 0.85]:
            x = int(left + (right - left) * ratio)
            cv2.circle(img, (x, base_cy), 14, (40, 40, 44), -1, lineType=cv2.LINE_AA)
            cv2.circle(img, (x, base_cy), 14, (20, 20, 22), 2, lineType=cv2.LINE_AA)

    # Linhas de camada (efeito de impressão 3D) — sutis, horizontais
    overlay = img.copy()
    for y in range(top + 3, base_y, 4):
        cv2.line(overlay, (left, y), (right, y), (170, 174, 178), 1, lineType=cv2.LINE_AA)
    img = cv2.addWeighted(overlay, 0.18, img, 0.82, 0)

    # Contorno geral pra reforçar borda
    cv2.polylines(img, [pts], True, (90, 92, 96), 2, lineType=cv2.LINE_AA)

    return img, dims


def add_label(img, text, color=(80, 220, 120)):
    """Coloca um rótulo no canto superior esquerdo identificando a imagem."""
    cv2.rectangle(img, (30, 30), (30 + 12, 30 + 36), color, -1)
    cv2.putText(img, text, (60, 60), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (240, 240, 240), 2, lineType=cv2.LINE_AA)
    cv2.putText(img, "VOXEL INSPECTOR / SAMPLE", (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 160), 1, lineType=cv2.LINE_AA)


# ============================================================
# DEFEITOS
# ============================================================

def apply_warping(img, dims):
    """Warping: bordas inferiores se curvam pra cima (descolamento da mesa)."""
    left, right, top, base_y, base_h, wall_w = dims
    # Desenha curva clara saindo da base, como se a peça tivesse soltado
    # do build plate nos cantos
    for side in [left, right]:
        # arco de descolamento
        cx = side
        for dx in range(0, 70):
            offset_y = int(18 * np.sin(dx / 70 * np.pi))
            if side == left:
                px = cx + dx
            else:
                px = cx - dx
            # apaga o pixel da base original (vira fundo) e cria
            # linha curva acima representando warping
            cv2.line(img, (px, base_y - offset_y), (px, base_y),
                     BG_COLOR, 1, lineType=cv2.LINE_AA)
        # marca visual do defeito (sombra escura no canto)
        cv2.ellipse(img, (cx + (30 if side == left else -30), base_y - 5),
                    (40, 10), 0, 0, 360, (15, 15, 18), -1)
    return img


def apply_layer_failure(img, dims):
    """Falha de camada: linhas horizontais escuras profundas no corpo."""
    left, right, top, base_y, base_h, wall_w = dims
    # 3 falhas em diferentes alturas da parede vertical
    failures_y = [
        top + 80,
        top + 180,
        top + 290,
    ]
    for y in failures_y:
        # linha de falha (sombra)
        cv2.line(img, (left + 5, y), (left + wall_w - 5, y),
                 (50, 50, 54), 3, lineType=cv2.LINE_AA)
        # pequeno deslocamento lateral (mostra mal-alinhamento)
        cv2.line(img, (left + 5, y + 2), (left + wall_w - 5, y + 2),
                 (30, 30, 34), 1, lineType=cv2.LINE_AA)
    return img


def apply_hole_defect(img, dims):
    """Buraco/falha de extrusão: vazio no corpo da peça."""
    left, right, top, base_y, base_h, wall_w = dims
    # buraco irregular no reforço diagonal
    cx = left + wall_w + 90
    cy = base_y - base_h - 60
    # contorno irregular usando vários círculos sobrepostos com cor do fundo
    rng = np.random.default_rng(42)
    for _ in range(8):
        dx = rng.integers(-12, 12)
        dy = rng.integers(-10, 10)
        r = rng.integers(14, 22)
        cv2.circle(img, (cx + dx, cy + dy), r, BG_COLOR, -1, lineType=cv2.LINE_AA)
    # borda escura ao redor do buraco
    cv2.circle(img, (cx, cy), 26, (40, 40, 44), 2, lineType=cv2.LINE_AA)
    return img


# ============================================================
# GERAÇÃO
# ============================================================

def generate_all():
    variants = [
        ("01_bracket_OK.png",         "OK",                    (80, 220, 120),  None),
        ("02_bracket_WARPING.png",    "DEFEITO: WARPING",      (90, 140, 255),  apply_warping),
        ("03_bracket_CAMADA.png",     "DEFEITO: CAMADA",       (90, 140, 255),  apply_layer_failure),
        ("04_bracket_BURACO.png",     "DEFEITO: BURACO",       (90, 140, 255),  apply_hole_defect),
    ]

    for filename, label, color, defect_fn in variants:
        bg = make_background()
        img, dims = draw_bracket(bg.copy())
        if defect_fn is not None:
            img = defect_fn(img, dims)
        add_label(img, label, color)

        path = os.path.join(OUT_DIR, filename)
        cv2.imwrite(path, img)
        print(f"  ✓ {path}")

    print(f"\nGerado {len(variants)} arquivos em ./{OUT_DIR}/")


if __name__ == "__main__":
    print("Gerando imagens sintéticas do bracket Voxel...\n")
    generate_all()