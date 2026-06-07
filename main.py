"""Voxel Inspector — ponto de entrada.

Captura video (webcam ou arquivo), executa o pipeline de Visao Computacional
em tempo real e exibe o resultado da inspecao sobreposto ao video.

Exemplos:
    python main.py                          # webcam padrao
    python main.py --source 1               # segunda webcam
    python main.py --source samples/peca_defeito.mp4
    python main.py --px-per-mm 6.0 --ref-width 40 --ref-height 60
    python main.py --source samples/peca_ok.mp4 --no-display --max-frames 30

Controles (janela de video):
    Q / ESC  sair
    ESPACO   pausar / continuar
    S        salvar screenshot
    C        calibrar: fixa a peca atual como referencia dimensional
    E        alternar visao de bordas (Canny)
    H        mostrar / ocultar o painel (HUD)
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

import cv2

from voxel_inspector import InspectorConfig, VoxelInspector
from voxel_inspector import analysis, overlay


def parse_args():
    p = argparse.ArgumentParser(description="Voxel Inspector - inspecao visual de impressao 3D")
    p.add_argument("--source", default="0",
                   help="Indice da webcam (0, 1, ...) ou caminho de um arquivo de video")
    p.add_argument("--width", type=int, default=960, help="Largura do frame de processamento")
    p.add_argument("--px-per-mm", type=float, default=0.0,
                   help="Calibracao: pixels por milimetro (0 = exibir em pixels)")
    p.add_argument("--ref-width", type=float, default=0.0, help="Largura nominal da peca (mm)")
    p.add_argument("--ref-height", type=float, default=0.0, help="Altura nominal da peca (mm)")
    p.add_argument("--record", default=None, help="Caminho para gravar o video anotado (.mp4)")
    p.add_argument("--no-display", action="store_true",
                   help="Roda sem janela (util para teste automatizado/headless)")
    p.add_argument("--max-frames", type=int, default=0,
                   help="Processa no maximo N frames e encerra (0 = ilimitado)")
    return p.parse_args()


def open_capture(source):
    """Abre webcam (se 'source' for um inteiro) ou arquivo de video."""
    if isinstance(source, str) and source.isdigit():
        source = int(source)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"[ERRO] Nao foi possivel abrir a fonte de video: {source!r}")
    return cap


def resize_to_width(frame, width):
    h, w = frame.shape[:2]
    if w == width:
        return frame
    scale = width / float(w)
    return cv2.resize(frame, (width, int(h * scale)), interpolation=cv2.INTER_AREA)


def make_writer(path, frame, fps=20.0):
    h, w = frame.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    return cv2.VideoWriter(path, fourcc, fps, (w, h))


def main():
    args = parse_args()

    cfg = InspectorConfig(
        source=args.source,
        frame_width=args.width,
        px_per_mm=args.px_per_mm,
        ref_width_mm=args.ref_width,
        ref_height_mm=args.ref_height,
    )
    inspector = VoxelInspector(cfg)
    cap = open_capture(args.source)

    writer = None
    show_edges = False
    show_hud = True
    paused = False
    last_result = None
    frame_count = 0
    t_prev = time.time()
    fps = 0.0

    print("[INFO] Voxel Inspector iniciado. Pressione Q para sair.")
    Path("captures").mkdir(exist_ok=True)

    while True:
        if not paused:
            ok, frame = cap.read()
            if not ok:
                print("[INFO] Fim do video / sem frames.")
                break
            frame = resize_to_width(frame, cfg.frame_width)
            last_result = inspector.analyze(frame)
            last_frame = frame
            frame_count += 1

            # FPS suavizado.
            now = time.time()
            dt = now - t_prev
            t_prev = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps else 1.0 / dt

        if show_edges:
            gray = analysis.preprocess(last_frame, cfg)
            edges = cv2.Canny(gray, cfg.canny_low, cfg.canny_high)
            display = overlay.edges_view(edges)
            display = overlay.render(display, last_result, fps, show_hud)
        else:
            display = overlay.render(last_frame, last_result, fps, show_hud)

        if args.record:
            if writer is None:
                writer = make_writer(args.record, display)
            writer.write(display)

        if not args.no_display:
            cv2.imshow("Voxel Inspector", display)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif key == ord(" "):
                paused = not paused
            elif key == ord("s"):
                _save_screenshot(display)
            elif key == ord("c"):
                if inspector.calibrate_reference(last_result):
                    print(f"[INFO] Referencia calibrada: "
                          f"{cfg.ref_width_mm:.1f} x {cfg.ref_height_mm:.1f} mm")
                else:
                    print("[AVISO] Calibre primeiro com --px-per-mm e tenha uma peca na imagem.")
            elif key == ord("e"):
                show_edges = not show_edges
            elif key == ord("h"):
                show_hud = not show_hud
        elif last_result is not None:
            print(f"[frame {frame_count:04d}] {last_result.verdict:9s} "
                  f"score={last_result.score:5.1f}")

        if args.max_frames and frame_count >= args.max_frames:
            break

    cap.release()
    if writer is not None:
        writer.release()
        print(f"[INFO] Video anotado salvo em: {args.record}")
    if not args.no_display:
        cv2.destroyAllWindows()
    print(f"[INFO] Encerrado. {frame_count} frames processados.")


def _save_screenshot(img):
    name = datetime.now().strftime("captures/voxel_%Y%m%d_%H%M%S.png")
    cv2.imwrite(name, img)
    print(f"[INFO] Screenshot salvo: {name}")


if __name__ == "__main__":
    main()
