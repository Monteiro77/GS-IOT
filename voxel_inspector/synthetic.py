"""Gerador de pecas 3D sinteticas para demonstracao e teste.

Permite exercitar todo o pipeline de Visao Computacional sem precisar de uma
peca impressa fisica na frente da camera. Produz duas situacoes:

* peca "OK"      -> contorno regular, base plana, camadas uniformes;
* peca "defeito" -> warping (base empenada), entalhe (material faltando) e
                    espacamento de camadas irregular.

Usado por ``samples/make_sample.py`` (gera os .mp4) e pelo teste de fumaca.
"""

from __future__ import annotations

import cv2
import numpy as np


def _background(h, w, rng):
    bg = np.full((h, w, 3), 46, np.uint8)
    noise = rng.normal(0, 6, (h, w, 1)).astype(np.int16)
    return np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def render_frame(t: float = 0.0, defect: bool = False, size=(540, 960), seed: int = 7):
    """Gera um frame BGR com uma peca impressa sintetica.

    Args:
        t: fase de animacao em [0, 1) (deriva/rotacao leves, simulando handheld).
        defect: se True, injeta warping + entalhe + camadas irregulares.
        size: (altura, largura) do frame.
        seed: semente base do gerador aleatorio.
    """
    h, w = size
    rng = np.random.default_rng(seed + int(t * 1000))
    frame = _background(h, w, rng)

    # Geometria da peca (com leve deriva no tempo).
    cx = w // 2 + int(16 * np.sin(2 * np.pi * t))
    cy = h // 2 + int(8 * np.cos(2 * np.pi * t))
    hw, hh = 120, 165
    top, bottom = cy - hh, cy + hh

    # Base: plana (OK) ou curvada para cima nos cantos (warping).
    amp = 70 if defect else 0
    xs = np.arange(cx - hw, cx + hw)
    base_y = (bottom - amp * ((xs - cx) / hw) ** 2).astype(np.int32)

    poly = np.array(
        [(cx - hw, top), (cx + hw, top)] +
        [(int(x), int(y)) for x, y in zip(xs[::-1], base_y[::-1])],
        dtype=np.int32,
    )
    mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask, [poly], 255)

    # Mordida em "V" no meio da aresta direita (material faltando) -> concavidade
    # real, que derruba a solidez (cortar um canto manteria o poligono convexo).
    if defect:
        bite = np.array([
            [cx + hw, cy - 80],
            [cx + hw - 95, cy],
            [cx + hw, cy + 80],
        ], np.int32)
        cv2.fillPoly(mask, [bite], 0)

    # Aparencia da peca + linhas de camada.
    part = np.full((h, w, 3), (150, 150, 156), np.uint8)
    pnoise = rng.normal(0, 5, (h, w, 1)).astype(np.int16)
    part = np.clip(part.astype(np.int16) + pnoise, 0, 255).astype(np.uint8)

    spacing = 18
    y = top + spacing
    while y < bottom - 3:
        cv2.line(part, (cx - hw, int(y)), (cx + hw, int(y)), (118, 118, 124), 1, cv2.LINE_AA)
        if defect:
            step = spacing * rng.uniform(0.5, 1.9)
            if rng.random() < 0.2:
                step += spacing          # camada "faltando"
        else:
            step = spacing
        y += step

    m = mask > 0
    frame[m] = part[m]

    # Leve rotacao global (camera na mao). Menor que a tolerancia das camadas.
    ang = 3.0 * np.sin(2 * np.pi * t + 1.0)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    return cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
