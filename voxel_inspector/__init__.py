"""Voxel Inspector — Visao Computacional para validacao de impressao 3D.

Modulo complementar ao projeto Voxel (Global Solution 2026 - tema "Space Connect").
Inspeciona, em tempo real, pecas de manufatura aditiva em busca de defeitos
(warping, camadas irregulares, deformacao do contorno) usando OpenCV.
"""

from .config import InspectorConfig
from .inspector import VoxelInspector, InspectionResult, Metric

__all__ = [
    "InspectorConfig",
    "VoxelInspector",
    "InspectionResult",
    "Metric",
]

__version__ = "1.0.0"
