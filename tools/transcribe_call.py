import os
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

URL = "https://api.groq.com/openai/v1/audio/transcriptions"
CHUNK_SECONDS = 600


def ffmpeg_exe():
    try:
        import imageio_ffmpeg
    except ImportError:
        sys.exit("Сначала установи: pip install imageio-ffmpeg")
    return imageio_ffmpeg.get_ffmpeg_exe()


def split_audio(video, folder):
    pattern = str(Path(folder) / "part_%03d.mp3")
    cmd = [
        ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",
        "-f", "segment", "-segment_time", str(CHUNK_SECONDS), pattern,
    ]
    subprocess.run(cmd, check=True)
    return sorted(Path(folder).glob("part_*.mp3"))


def transcribe(part, key):
    with open(part, "rb") as f:
        r = httpx.post(
            URL,
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (part.name, f, "audio/mpeg")},
            data={"model": "whisper-large-v3", "language": "ru", "response_format": "text"},
            timeout=300,
        )
    if r.status_code != 200:
        sys.exit(f"Ошибка Groq {r.status_code}: {r.text[:300]}")
    return r.text.strip()


def main():
    if len(sys.argv) < 2:
        sys.exit('Запуск: python tools\\transcribe_call.py "путь\\к\\видео.mp4"')
    video = Path(sys.argv[1])
    if not video.exists():
        sys.exit(f"Файл не найден: {video}")
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        sys.exit("GROQ_API_KEY пустой в .env")
    out = video.with_name(video.stem + "_transcript.txt")
    with tempfile.TemporaryDirectory() as tmp:
        parts = split_audio(video, tmp)
        print(f"Частей по 10 минут: {len(parts)}")
        texts = []
        for i, part in enumerate(parts, 1):
            print(f"Расшифровываю {i}/{len(parts)}…")
            minute = (i - 1) * CHUNK_SECONDS // 60
            texts.append(f"[{minute:02d}:00]\n{transcribe(part, key)}")
    out.write_text("\n\n".join(texts), encoding="utf-8")
    print(f"Готово: {out}")


if __name__ == "__main__":
    main()
