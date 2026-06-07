"""Funcoes puras de Visao Computacional (OpenCV/NumPy).

Cada funcao executa uma etapa isolada do pipeline e nao guarda estado, o que
facilita testar e reaproveitar. A orquestracao fica em ``inspector.py``.

Pipeline:
    preprocess        -> normaliza iluminacao + remove ruido
    segment_part      -> isola a silhueta da peca (Canny + contornos)
    measure_dimensions-> bounding box (px e, se calibrado, mm)
    compute_solidity  -> regularidade do contorno (proxy de deformacao)
    detect_base_warping-> planicidade da base (proxy de warping)
    detect_layers     -> regularidade das linhas de camada (Hough)
"""

from __future__ import annotations

import cv2
import numpy as np


def preprocess(frame: np.ndarray, cfg) -> np.ndarray:
    """Converte para cinza, equaliza contraste (CLAHE) e suaviza ruido."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if cfg.use_clahe:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
    k = cfg.odd_blur()
    gray = cv2.GaussianBlur(gray, (k, k), 0)
    return gray


def segment_part(gray: np.ndarray, cfg):
    """Encontra a silhueta da peca.

    Usa Canny para detectar bordas (independente do contraste ser claro/escuro),
    fecha as lacunas morfologicamente e seleciona o maior contorno externo.

    Retorna (contour, mask, edges) ou (None, None, edges) se nada relevante for achado.
    A ``mask`` e o contorno preenchido — base para medidas de area, base e camadas.
    """
    edges = cv2.Canny(gray, cfg.canny_low, cfg.canny_high)

    # Fecha pequenas falhas das bordas para formar uma silhueta continua.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None, edges

    h, w = gray.shape
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < cfg.min_contour_area_ratio * (h * w):
        return None, None, edges

    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)
    return largest, mask, edges


def measure_dimensions(contour: np.ndarray, cfg) -> dict:
    """Mede a bounding box da peca em pixels e, se calibrado, em milimetros."""
    x, y, w, h = cv2.boundingRect(contour)
    dims = {"x": x, "y": y, "w": w, "h": h, "w_mm": None, "h_mm": None}
    if cfg.px_per_mm and cfg.px_per_mm > 0:
        dims["w_mm"] = w / cfg.px_per_mm
        dims["h_mm"] = h / cfg.px_per_mm
    return dims


def compute_solidity(contour: np.ndarray):
    """Solidez = area do contorno / area do fecho convexo.

    Valor proximo de 1.0 indica contorno regular; valores menores revelam
    concavidades fortes (material faltando, deformacao, base levantada).
    Retorna (solidity, hull).
    """
    hull = cv2.convexHull(contour)
    area = cv2.contourArea(contour)
    hull_area = cv2.contourArea(hull)
    solidity = float(area / hull_area) if hull_area > 0 else 0.0
    return solidity, hull


def _base_profile(mask: np.ndarray):
    """Para cada coluna, encontra o y do ultimo pixel da peca (a 'base').

    Vetorizado: vira a mascara de cabeca para baixo e usa argmax para achar,
    por coluna, o primeiro pixel branco vindo de baixo.
    """
    flipped = mask[::-1, :]
    has_part = flipped.max(axis=0) > 0
    last_from_bottom = mask.shape[0] - 1 - flipped.argmax(axis=0)
    xs = np.where(has_part)[0]
    ys = last_from_bottom[xs]
    return xs.astype(np.float64), ys.astype(np.float64)


def detect_base_warping(mask: np.ndarray, dims: dict, trim: float = 0.12):
    """Mede a planicidade da base da peca (proxy de warping).

    Warping faz os cantos levantarem, curvando a base. Ajustamos uma reta
    (minimos quadrados) ao perfil inferior e medimos o desvio normalizado pela
    altura da peca.

    As colunas das extremidades sao descartadas (``trim``): quando a peca esta
    levemente rotacionada, as arestas verticais laterais geram picos espurios no
    "ultimo pixel por coluna" que nada tem a ver com warping.

    Retorna (flatness, profile) onde profile = (xs, ys, fit) para desenho,
    ou (0.0, None) se nao houver dados suficientes.
    """
    xs, ys = _base_profile(mask)
    if xs.size < 20:
        return 0.0, None

    n = xs.size
    k = int(n * trim)
    if n - 2 * k < 10:
        k = 0
    xs, ys = xs[k:n - k], ys[k:n - k]

    coeffs = np.polyfit(xs, ys, 1)          # reta y = a*x + b
    fit = np.polyval(coeffs, xs)
    resid = np.abs(ys - fit)
    # Percentil 90 e robusto a pequenos "dentes" do contorno, mas captura a curva.
    deviation = float(np.percentile(resid, 90))
    flatness = deviation / max(dims["h"], 1)
    return flatness, (xs, ys, fit)


def _find_peaks(sig: np.ndarray, min_dist: int, min_height: float):
    """Encontra maximos locais acima de ``min_height`` separados por ``min_dist``."""
    peaks = []
    for i in range(1, len(sig) - 1):
        if sig[i] >= sig[i - 1] and sig[i] > sig[i + 1] and sig[i] >= min_height:
            if peaks and (i - peaks[-1]) < min_dist:
                if sig[i] > sig[peaks[-1]]:
                    peaks[-1] = i          # mantem o pico mais forte do par
            else:
                peaks.append(i)
    return peaks


def detect_layers(gray: np.ndarray, mask: np.ndarray, dims: dict, cfg):
    """Analisa a regularidade das linhas de camada da impressao.

    Em vez de depender da Transformada de Hough (esparsa em camadas finas),
    realca as bordas horizontais com o gradiente vertical (Sobel), projeta a
    resposta no eixo vertical e detecta os picos -> cada pico e uma camada.
    O coeficiente de variacao (std/media) do espacamento entre picos mede a
    regularidade: espacamento irregular => extrusao instavel.

    Retorna dict com: cv (float|None), count (int), segments (lista p/ desenho).
    """
    x, y, w, h = dims["x"], dims["y"], dims["w"], dims["h"]
    if h < 30 or w < 10:
        return {"cv": None, "count": 0, "segments": []}

    roi = gray[y:y + h, x:x + w].astype(np.float32)
    roi_mask = mask[y:y + h, x:x + w] > 0

    # Erode a mascara para ignorar a propria silhueta (topo, base e laterais),
    # cujas bordas geram gradientes fortes que poluiriam a contagem de camadas.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    inner = cv2.erode(roi_mask.astype(np.uint8) * 255, kernel, iterations=1) > 0

    # Gradiente vertical: responde fortemente as linhas de camada (horizontais).
    sobel = np.abs(cv2.Sobel(roi, cv2.CV_32F, 0, 1, ksize=3))
    sobel[~inner] = 0.0

    # Projeta no eixo vertical, considerando so as linhas bem cobertas pela peca.
    coverage = inner.sum(axis=1)
    valid = coverage > 0.30 * w
    proj = np.zeros(h, dtype=np.float32)
    proj[valid] = sobel.sum(axis=1)[valid] / np.maximum(coverage[valid], 1)
    if proj.max() <= 1e-6:
        return {"cv": None, "count": 0, "segments": []}

    # Suaviza no eixo vertical para fundir as bordas duplas de uma mesma camada.
    proj = cv2.GaussianBlur(proj.reshape(-1, 1), (1, 5), 0).ravel()

    nonzero = proj[proj > 0]
    min_height = float(nonzero.mean() + 0.6 * nonzero.std())
    min_dist = max(4, int(0.015 * h))
    peaks = _find_peaks(proj, min_dist, min_height)

    if len(peaks) < 3:
        return {"cv": None, "count": len(peaks), "segments": []}

    spacings = np.diff(np.array(peaks, dtype=np.float64))
    mean = float(spacings.mean())
    cv_val = float(spacings.std() / mean) if mean > 0 else None

    # Segmentos para desenho: uma linha por camada, na largura coberta da peca.
    segments = []
    for py in peaks:
        cols = np.where(roi_mask[py])[0]
        if cols.size:
            segments.append((x + int(cols.min()), y + int(py),
                             x + int(cols.max()), y + int(py)))
    return {"cv": cv_val, "count": len(peaks), "segments": segments}
