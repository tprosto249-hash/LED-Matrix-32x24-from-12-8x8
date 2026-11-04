#!/usr/bin/env python3
"""
Перетворює відео (YouTube-посилання або локальний файл)
на frames.h для LED-матриць 32x24 (12 матриць MAX7219).

Приклад:
  python tools/video2frames.py "https://youtu.be/XXXX" -o frames.h --fps 10 --start 5 --duration 20
"""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

# Розміри екрана (4 матриці в ширину x 3 в висоту, по 8x8)
W, H = 32, 24
FRAME_BYTES = W * H // 8  # 96 байт на кадр (як у вашому frames.h)


def download_youtube(url: str, out_dir: Path) -> Path:
    """Завантажує відео через yt-dlp. Бере найменше за роздільністю відео,
    а якщо такого формату нема, то будь-який доступний."""
    template = str(out_dir / "source.%(ext)s")
    subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--no-playlist",
         # спочатку мале відео до 360p, потім просто найгірше з відео, потім будь-що
         "-f", "worstvideo[height>=240]/worstvideo/worst/best",
         "-o", template, url],
        check=True,
    )
    files = list(out_dir.glob("source.*"))
    if not files:
        sys.exit("Не вдалося завантажити відео")
    return files[0]


def extract_frames(video: Path, fps: float, start, duration, mode: str) -> bytes:
    """ffmpeg віддає сирі сірі кадри 32x24 (1 байт на піксель) прямо в пам'ять."""
    if mode == "crop":
        # Заповнити екран: масштаб з обрізанням країв до пропорцій 4:3
        scale = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=area,crop={W}:{H}"
    else:
        # Вписати: масштаб із чорними смугами
        scale = (f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=area,"
                 f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2")

    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += ["-i", str(video), "-vf", f"fps={fps},{scale},format=gray",
            "-f", "rawvideo", "-pix_fmt", "gray", "-"]

    result = subprocess.run(cmd, check=True, capture_output=True)
    return result.stdout


def frame_to_bytes(raw: bytes, args) -> list:
    """Один кадр: сірі пікселі -> чорно-біла картинка -> 96 байт (MSB = лівий піксель)."""
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(H, W)
    img = Image.fromarray(arr)

    if args.autocontrast:
        # Розтягуємо контраст, щоб темні сцени не стали повністю чорними
        img = ImageOps.autocontrast(img, cutoff=2)

    if args.dither:
        # Дизерінг Флойда-Стейнберга: більше деталей на 1-бітному екрані
        bits = np.array(img.convert("1"), dtype=bool)
    else:
        bits = np.array(img) > args.threshold

    if args.invert:
        bits = ~bits
    if args.mirror:
        bits = bits[:, ::-1]

    # packbits пакує по 8 пікселів у байт, старший біт = лівий піксель
    return np.packbits(bits, axis=1).flatten().tolist()  # 24 рядки x 4 байти = 96


def write_header(frames: list, fps: float, out_path: Path):
    interval = round(1000 / fps)
    lines = [
        "#pragma once", "",
        "#include <Arduino.h>",
        "#include <avr/pgmspace.h>", "",
        f"#define FRAME_WIDTH {W}",
        f"#define FRAME_HEIGHT {H}",
        f"#define FRAME_BYTES {FRAME_BYTES}", "",
        f"#define FRAME_COUNT {len(frames)}",
        f"#define FRAME_INTERVAL_MS {interval}", "",
        "const byte videoFrames[FRAME_COUNT][FRAME_BYTES] PROGMEM = {", "",
    ]
    for i, data in enumerate(frames):
        lines.append(f"    // FRAME {i}")
        lines.append("    {")
        for row in range(H):
            chunk = data[row * 4:(row + 1) * 4]
            text = ", ".join(f"0x{b:02X}" for b in chunk)
            lines.append(f"      {text}" + ("," if row < H - 1 else ""))
        lines.append("    }" + ("," if i < len(frames) - 1 else ""))
        lines.append("")
    lines.append("};")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="YouTube -> frames.h для LED 32x24")
    p.add_argument("source", help="посилання YouTube або шлях до відеофайлу")
    p.add_argument("-o", "--output", default="frames.h", help="вихідний файл (frames.h)")
    p.add_argument("--fps", type=float, default=10, help="кадрів за секунду (за замовч. 10)")
    p.add_argument("--start", type=float, help="з якої секунди починати")
    p.add_argument("--duration", type=float, help="скільки секунд взяти")
    p.add_argument("--mode", choices=["crop", "fit"], default="crop",
                   help="crop = заповнити екран, fit = вписати зі смугами")
    p.add_argument("--threshold", type=int, default=110, help="поріг яскравості 0-255")
    p.add_argument("--dither", action="store_true", help="дизерінг замість порогу")
    p.add_argument("--no-autocontrast", dest="autocontrast", action="store_false",
                   help="вимкнути автоконтраст")
    p.add_argument("--invert", action="store_true", help="інвертувати (світле <-> темне)")
    p.add_argument("--mirror", action="store_true", help="віддзеркалити по горизонталі")
    p.add_argument("--max-frames", type=int, default=280,
                   help="ліміт кадрів (Uno/Nano ~280, Mega ~2500)")
    args = p.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        if args.source.startswith(("http://", "https://")):
            video = download_youtube(args.source, Path(tmp))
        else:
            video = Path(args.source)
        raw = extract_frames(video, args.fps, args.start, args.duration, args.mode)

    count = len(raw) // (W * H)
    if count == 0:
        sys.exit("Кадрів не отримано — перевірте --start/--duration")
    if count > args.max_frames:
        print(f"⚠ {count} кадрів не влізе в пам'ять, обрізаю до {args.max_frames}")
        count = args.max_frames

    frames = [frame_to_bytes(raw[i * W * H:(i + 1) * W * H], args) for i in range(count)]
    write_header(frames, args.fps, Path(args.output))

    print(f"Готово: {count} кадрів, {count * FRAME_BYTES} байт у flash, "
          f"тривалість ≈ {count / args.fps:.1f} с -> {args.output}")


if __name__ == "__main__":
    main()