"""Parametros de configuracao do pipeline de Visao Computacional.

Centralizar tudo num unico dataclass facilita o ajuste fino do detector sem
precisar caçar "numeros magicos" espalhados pelo codigo.
"""

from dataclasses import dataclass


@dataclass
class InspectorConfig:
    # ----- Captura de video -----
    source: object = 0          # 0 = webcam padrao; ou caminho de um arquivo .mp4
    frame_width: int = 960      # frame e redimensionado para esta largura (mantem proporcao)

    # ----- Pre-processamento -----
    blur_ksize: int = 5         # kernel do desfoque Gaussiano (suaviza ruido)
    use_clahe: bool = True      # equaliza contraste local (robustez a iluminacao irregular)

    # ----- Deteccao de bordas (Canny) -----
    canny_low: int = 50
    canny_high: int = 150

    # ----- Segmentacao da peca -----
    # Area minima do contorno aceito como "peca", em fracao da area do frame.
    min_contour_area_ratio: float = 0.02

    # ----- Analise de camadas (Hough Lines) -----
    hough_threshold: int = 55
    hough_min_line_ratio: float = 0.20   # comprimento minimo da linha (fracao da largura da peca)
    hough_max_gap: int = 14
    layer_angle_tol_deg: float = 12.0    # tolerancia angular para considerar a linha "horizontal"

    # ----- Limiares de qualidade -----
    # Solidez = area do contorno / area do fecho convexo. Perto de 1 => contorno regular.
    solidity_warn: float = 0.93
    solidity_defect: float = 0.86
    # Planicidade da base = desvio (p90) da base / altura da peca. Quanto maior, pior (warping).
    base_flatness_warn: float = 0.025
    base_flatness_defect: float = 0.050
    # Coef. de variacao do espacamento entre camadas. Quanto maior, mais irregular.
    layer_cv_warn: float = 0.35
    layer_cv_defect: float = 0.60

    # ----- Calibracao dimensional -----
    px_per_mm: float = 0.0       # 0 = nao calibrado (dimensoes exibidas em pixels)
    ref_width_mm: float = 0.0    # largura nominal esperada da peca (STL de referencia)
    ref_height_mm: float = 0.0   # altura nominal esperada da peca
    dim_tolerance: float = 0.05  # tolerancia dimensional (5%)

    def odd_blur(self) -> int:
        """Garante que o kernel do blur seja sempre impar (exigencia do OpenCV)."""
        return self.blur_ksize | 1
