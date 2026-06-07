"""Teste de fumaca do pipeline (sem interface grafica).

Gera frames sinteticos de peca OK e peca com defeito, roda o inspetor e
verifica se os vereditos fazem sentido. Util para validar a logica sem webcam.

Execute a partir da raiz do projeto:
    python tests/smoke_test.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from voxel_inspector import InspectorConfig, VoxelInspector, synthetic  # noqa: E402
from voxel_inspector.inspector import OK, WARN, DEFECT  # noqa: E402


def run_case(defect: bool, n_frames: int = 8):
    inspector = VoxelInspector(InspectorConfig())
    verdicts, scores = [], []
    for i in range(n_frames):
        frame = synthetic.render_frame(t=i / n_frames, defect=defect)
        res = inspector.analyze(frame)
        verdicts.append(res.verdict)
        scores.append(res.score)
    avg = sum(scores) / len(scores)
    return verdicts, avg


def main():
    print("== Voxel Inspector :: teste de fumaca ==\n")

    ok_verdicts, ok_avg = run_case(defect=False)
    print(f"[PECA OK]      vereditos={ok_verdicts}  score_medio={ok_avg:.1f}")

    bad_verdicts, bad_avg = run_case(defect=True)
    print(f"[PECA DEFEITO] vereditos={bad_verdicts}  score_medio={bad_avg:.1f}\n")

    failures = []
    if not all(v != "SEM PECA" for v in ok_verdicts):
        failures.append("peca OK nao foi detectada em algum frame")
    if not any(v == OK for v in ok_verdicts):
        failures.append("peca OK nunca recebeu veredito OK")
    if not any(v in (WARN, DEFECT) for v in bad_verdicts):
        failures.append("peca com defeito nunca foi reprovada")
    if not bad_avg < ok_avg:
        failures.append("score da peca defeituosa nao ficou abaixo da peca OK")

    if failures:
        print("FALHOU:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print("OK: pipeline aprovou a peca boa e reprovou a defeituosa.")


if __name__ == "__main__":
    main()
