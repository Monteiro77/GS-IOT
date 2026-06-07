"""Orquestracao do pipeline e logica de veredito.

A classe ``VoxelInspector`` recebe um frame e devolve um ``InspectionResult``
com todas as metricas, um score 0-100 e um veredito final
(OK / ATENCAO / DEFEITO / SEM PECA).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from . import analysis
from .config import InspectorConfig

# Vereditos possiveis (ordenados do melhor para o pior).
OK = "OK"
WARN = "ATENCAO"
DEFECT = "DEFEITO"
NO_PART = "SEM PECA"

# Status por metrica -> peso no score.
_STATUS_SCORE = {"ok": 100.0, "warn": 60.0, "defect": 15.0}
_SEVERITY = {"ok": 0, "warn": 1, "defect": 2}


@dataclass
class Metric:
    """Resultado de uma metrica individual da inspecao."""
    name: str
    value: Optional[float]
    status: str          # "ok" | "warn" | "defect" | "n/a"
    detail: str


@dataclass
class InspectionResult:
    """Saida completa de uma inspecao de um frame."""
    part_found: bool
    verdict: str
    score: float
    metrics: list = field(default_factory=list)
    # Dados geometricos para a sobreposicao visual.
    contour: object = None
    hull: object = None
    bbox: Optional[dict] = None
    base_profile: object = None
    layer_segments: list = field(default_factory=list)


def _classify_low_is_bad(value, warn, defect):
    """Classifica metricas onde valores baixos sao ruins (ex.: solidez)."""
    if value <= defect:
        return "defect"
    if value <= warn:
        return "warn"
    return "ok"


def _classify_high_is_bad(value, warn, defect):
    """Classifica metricas onde valores altos sao ruins (ex.: warping)."""
    if value >= defect:
        return "defect"
    if value >= warn:
        return "warn"
    return "ok"


class VoxelInspector:
    """Pipeline de inspecao visual de pecas impressas em 3D."""

    def __init__(self, cfg: Optional[InspectorConfig] = None):
        self.cfg = cfg or InspectorConfig()

    # -- API principal -------------------------------------------------------
    def analyze(self, frame: np.ndarray) -> InspectionResult:
        cfg = self.cfg
        gray = analysis.preprocess(frame, cfg)
        contour, mask, _ = analysis.segment_part(gray, cfg)

        if contour is None:
            return InspectionResult(
                part_found=False, verdict=NO_PART, score=0.0,
                metrics=[Metric("Peca", None, "n/a", "Nenhuma peca detectada")],
            )

        dims = analysis.measure_dimensions(contour, cfg)
        solidity, hull = analysis.compute_solidity(contour)
        flatness, base_profile = analysis.detect_base_warping(mask, dims)
        layers = analysis.detect_layers(gray, mask, dims, cfg)

        metrics = [
            self._metric_solidity(solidity),
            self._metric_warping(flatness),
            self._metric_layers(layers),
            self._metric_dimensions(dims),
        ]

        verdict, score = self._aggregate(metrics)
        return InspectionResult(
            part_found=True, verdict=verdict, score=score, metrics=metrics,
            contour=contour, hull=hull, bbox=dims,
            base_profile=base_profile, layer_segments=layers["segments"],
        )

    # -- Calibracao em tempo de execucao ------------------------------------
    def calibrate_reference(self, result: InspectionResult) -> bool:
        """Fixa a peca atual como referencia dimensional (tecla 'c' na UI)."""
        if not result.part_found or not result.bbox:
            return False
        if result.bbox["w_mm"] is not None:
            self.cfg.ref_width_mm = result.bbox["w_mm"]
            self.cfg.ref_height_mm = result.bbox["h_mm"]
            return True
        return False

    # -- Metricas individuais -----------------------------------------------
    def _metric_solidity(self, solidity: float) -> Metric:
        cfg = self.cfg
        status = _classify_low_is_bad(solidity, cfg.solidity_warn, cfg.solidity_defect)
        detail = {
            "ok": "Contorno regular",
            "warn": "Contorno levemente irregular",
            "defect": "Contorno deformado / material faltando",
        }[status]
        return Metric("Solidez do contorno", solidity, status, detail)

    def _metric_warping(self, flatness: float) -> Metric:
        cfg = self.cfg
        status = _classify_high_is_bad(flatness, cfg.base_flatness_warn, cfg.base_flatness_defect)
        detail = {
            "ok": "Base plana",
            "warn": "Base levemente curva (possivel warping)",
            "defect": "Warping: base empenada / cantos levantados",
        }[status]
        return Metric("Planicidade da base", flatness, status, detail)

    def _metric_layers(self, layers: dict) -> Metric:
        cfg = self.cfg
        cv_val = layers["cv"]
        if cv_val is None:
            return Metric("Regularidade das camadas", None, "n/a",
                          "Camadas insuficientes para analise")
        status = _classify_high_is_bad(cv_val, cfg.layer_cv_warn, cfg.layer_cv_defect)
        detail = {
            "ok": f"{layers['count']} camadas uniformes",
            "warn": "Espacamento de camadas irregular",
            "defect": "Camadas mal fundidas / extrusao instavel",
        }[status]
        return Metric("Regularidade das camadas", cv_val, status, detail)

    def _metric_dimensions(self, dims: dict) -> Metric:
        cfg = self.cfg
        if dims["w_mm"] is None:
            return Metric("Conformidade dimensional", None, "n/a",
                          f"{dims['w']}x{dims['h']} px (nao calibrado)")
        if cfg.ref_width_mm <= 0:
            return Metric("Conformidade dimensional", None, "n/a",
                          f"{dims['w_mm']:.1f}x{dims['h_mm']:.1f} mm (sem referencia)")

        dev_w = abs(dims["w_mm"] - cfg.ref_width_mm) / cfg.ref_width_mm
        dev_h = abs(dims["h_mm"] - cfg.ref_height_mm) / cfg.ref_height_mm
        dev = max(dev_w, dev_h)
        status = _classify_high_is_bad(dev, cfg.dim_tolerance, cfg.dim_tolerance * 2)
        detail = {
            "ok": f"{dims['w_mm']:.1f}x{dims['h_mm']:.1f} mm (dentro da tolerancia)",
            "warn": f"Desvio de {dev * 100:.1f}% em relacao ao STL",
            "defect": f"Fora de escala: desvio de {dev * 100:.1f}%",
        }[status]
        return Metric("Conformidade dimensional", dev, status, detail)

    # -- Agregacao ----------------------------------------------------------
    def _aggregate(self, metrics: list) -> tuple:
        considered = [m for m in metrics if m.status in _STATUS_SCORE]
        if not considered:
            return OK, 100.0

        score = float(np.mean([_STATUS_SCORE[m.status] for m in considered]))
        worst = max(_SEVERITY[m.status] for m in considered)
        verdict = {0: OK, 1: WARN, 2: DEFECT}[worst]
        return verdict, score
