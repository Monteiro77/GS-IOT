"""Renderizacao da sobreposicao visual (HUD) sobre o frame de video.

Desenha contorno, fecho convexo, bounding box, base ajustada, camadas
detectadas e um painel lateral com as metricas e o veredito final.
"""

from __future__ import annotations

import cv2
import numpy as np

from .inspector import OK, WARN, DEFECT, NO_PART

# Cores em BGR.
COLOR = {
    "ok": (80, 200, 80),
    "warn": (40, 180, 255),
    "defect": (60, 60, 235),
    "n/a": (170, 170, 170),
    "contour": (80, 220, 80),
    "hull": (200, 200, 60),
    "bbox": (255, 200, 80),
    "layer": (230, 200, 60),
    "base_ok": (80, 220, 80),
    "base_bad": (60, 60, 235),
    "text": (240, 240, 240),
    "panel": (28, 28, 28),
}

VERDICT_COLOR = {
    OK: COLOR["ok"],
    WARN: COLOR["warn"],
    DEFECT: COLOR["defect"],
    NO_PART: COLOR["n/a"],
}

FONT = cv2.FONT_HERSHEY_SIMPLEX


def render(frame, result, fps=None, show_help=True):
    """Devolve uma copia do frame com toda a sobreposicao desenhada."""
    out = frame.copy()
    if result.part_found:
        _draw_geometry(out, result)
    _draw_panel(out, result, fps)
    if show_help:
        _draw_help(out)
    return out


# -- Geometria sobre a peca --------------------------------------------------
def _draw_geometry(img, result):
    # Fecho convexo (referencia da "forma ideal").
    if result.hull is not None:
        cv2.polylines(img, [result.hull], True, COLOR["hull"], 1, cv2.LINE_AA)

    # Contorno real da peca.
    if result.contour is not None:
        cv2.drawContours(img, [result.contour], -1, COLOR["contour"], 2, cv2.LINE_AA)

    # Bounding box + dimensoes.
    if result.bbox is not None:
        b = result.bbox
        cv2.rectangle(img, (b["x"], b["y"]), (b["x"] + b["w"], b["y"] + b["h"]),
                      COLOR["bbox"], 1, cv2.LINE_AA)
        if b["w_mm"] is not None:
            label = f"{b['w_mm']:.1f} x {b['h_mm']:.1f} mm"
        else:
            label = f"{b['w']} x {b['h']} px"
        cv2.putText(img, label, (b["x"], max(b["y"] - 8, 14)),
                    FONT, 0.5, COLOR["bbox"], 1, cv2.LINE_AA)

    # Linhas de camada detectadas.
    for x1, y1, x2, y2 in result.layer_segments:
        cv2.line(img, (int(x1), int(y1)), (int(x2), int(y2)), COLOR["layer"], 1, cv2.LINE_AA)

    # Perfil da base: pontos reais vs reta ajustada (evidencia o warping).
    if result.base_profile is not None:
        xs, ys, fit = result.base_profile
        flat_metric = next((m for m in result.metrics if m.name == "Planicidade da base"), None)
        base_color = COLOR["base_bad"] if (flat_metric and flat_metric.status != "ok") else COLOR["base_ok"]
        pts_fit = np.array([[int(x), int(y)] for x, y in zip(xs, fit)], dtype=np.int32)
        if len(pts_fit) >= 2:
            cv2.polylines(img, [pts_fit], False, (200, 200, 200), 1, cv2.LINE_AA)
        # Amostra os pontos reais da base para nao poluir.
        step = max(1, len(xs) // 60)
        for i in range(0, len(xs), step):
            cv2.circle(img, (int(xs[i]), int(ys[i])), 1, base_color, -1, cv2.LINE_AA)


# -- Painel de metricas ------------------------------------------------------
def _draw_panel(img, result, fps):
    h, w = img.shape[:2]
    pw = 330
    x0 = w - pw

    # Fundo translucido.
    panel = img[:, x0:].copy()
    dark = np.full_like(panel, COLOR["panel"])
    img[:, x0:] = cv2.addWeighted(panel, 0.25, dark, 0.75, 0)

    pad = 16
    y = 38
    cv2.putText(img, "VOXEL INSPECTOR", (x0 + pad, y), FONT, 0.62, COLOR["text"], 2, cv2.LINE_AA)
    y += 22
    cv2.putText(img, "Inspecao de manufatura aditiva", (x0 + pad, y),
                FONT, 0.42, COLOR["n/a"], 1, cv2.LINE_AA)
    y += 26

    # Veredito em destaque.
    vcolor = VERDICT_COLOR.get(result.verdict, COLOR["n/a"])
    cv2.rectangle(img, (x0 + pad, y), (w - pad, y + 46), vcolor, -1)
    cv2.putText(img, result.verdict, (x0 + pad + 12, y + 32),
                FONT, 0.9, (20, 20, 20), 2, cv2.LINE_AA)
    if result.part_found:
        score_txt = f"{result.score:0.0f}/100"
        cv2.putText(img, score_txt, (w - pad - 95, y + 32),
                    FONT, 0.7, (20, 20, 20), 2, cv2.LINE_AA)
    y += 46 + 18

    # Barra de score.
    if result.part_found:
        bar_w = pw - 2 * pad
        filled = int(bar_w * result.score / 100.0)
        cv2.rectangle(img, (x0 + pad, y), (x0 + pad + bar_w, y + 8), (70, 70, 70), -1)
        cv2.rectangle(img, (x0 + pad, y), (x0 + pad + filled, y + 8), vcolor, -1)
        y += 26

    # Metricas.
    for m in result.metrics:
        mc = COLOR.get(m.status, COLOR["n/a"])
        cv2.circle(img, (x0 + pad + 5, y - 4), 5, mc, -1, cv2.LINE_AA)
        cv2.putText(img, m.name, (x0 + pad + 18, y), FONT, 0.46, COLOR["text"], 1, cv2.LINE_AA)
        if m.value is not None:
            cv2.putText(img, f"{m.value:0.3f}", (w - pad - 58, y),
                        FONT, 0.46, mc, 1, cv2.LINE_AA)
        y += 18
        cv2.putText(img, _wrap(m.detail), (x0 + pad + 18, y),
                    FONT, 0.38, COLOR["n/a"], 1, cv2.LINE_AA)
        y += 24

    # FPS.
    if fps is not None:
        cv2.putText(img, f"{fps:0.1f} FPS", (x0 + pad, h - 16),
                    FONT, 0.45, COLOR["n/a"], 1, cv2.LINE_AA)


def _draw_help(img):
    h = img.shape[0]
    txt = "[Q] sair  [ESPACO] pausar  [S] salvar  [C] calibrar  [E] bordas  [H] HUD"
    cv2.putText(img, txt, (14, h - 16), FONT, 0.42, (220, 220, 220), 1, cv2.LINE_AA)


def _wrap(text, limit=40):
    return text if len(text) <= limit else text[: limit - 1] + "."


def edges_view(edges):
    """Converte o mapa de bordas (1 canal) para BGR, para exibir lado a lado."""
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
