# Copyright (c) 2026 Vassel Goleyu. All rights reserved.
"""OCR Tesseract di memori: gambar lewat stdin, teks dari stdout, tanpa file sementara."""

import io
import subprocess
import warnings

from PIL import Image

ALLOWED_FORMATS = frozenset({"JPEG", "PNG", "WEBP"})
# Batas piksel untuk mencegah decompression bomb (gambar kecil yang mengembang jadi raksasa di memori).
Image.MAX_IMAGE_PIXELS = 40_000_000
_MIN_SIDE, _MAX_SIDE = 1200, 3000


class InvalidImageError(ValueError):
    """Isi berkas bukan JPEG/PNG/WebP yang valid."""


class OcrError(RuntimeError):
    """OCR tidak bisa dijalankan (Tesseract tidak ada, gagal, atau timeout)."""


class OcrEmptyError(OcrError):
    """OCR berhasil tetapi tidak ada teks yang terbaca."""


def open_image(data: bytes) -> Image.Image:
    """Buka dan verifikasi gambar dari isi byte-nya (bukan ekstensi atau Content-Type)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(io.BytesIO(data))
            if img.format not in ALLOWED_FORMATS:
                raise InvalidImageError("format gambar harus JPEG, PNG, atau WebP")
            img.load()
    except InvalidImageError:
        raise
    except Exception:
        raise InvalidImageError("berkas bukan gambar JPEG, PNG, atau WebP yang valid") from None
    return img


def preprocess(img: Image.Image) -> Image.Image:
    """Grayscale lalu ubah ukuran: tangkapan layar kecil diperbesar, gambar besar diperkecil."""
    gray = img.convert("L")
    longest = max(gray.size)
    scale = _MIN_SIDE / longest if longest < _MIN_SIDE else min(1.0, _MAX_SIDE / longest)
    if scale != 1.0:
        gray = gray.resize((round(gray.width * scale), round(gray.height * scale)), Image.Resampling.LANCZOS)
    return gray


class TesseractOcr:
    def __init__(self, langs: str = "ind+eng", binary: str = "tesseract", timeout_s: float = 30.0) -> None:
        self._cmd = [binary, "stdin", "stdout", "-l", langs, "--psm", "3"]
        self._timeout_s = timeout_s

    def extract(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        preprocess(img).save(buf, format="PNG")
        try:
            proc = subprocess.run(
                self._cmd, input=buf.getvalue(), capture_output=True, timeout=self._timeout_s, check=False
            )
        except FileNotFoundError:
            raise OcrError("Tesseract tidak terpasang di server") from None
        except subprocess.TimeoutExpired:
            raise OcrError("OCR melebihi batas waktu") from None
        if proc.returncode != 0:
            raise OcrError(f"Tesseract gagal (kode {proc.returncode})")
        text = proc.stdout.decode("utf-8", errors="replace").strip()
        if not text:
            raise OcrEmptyError("Tidak ada teks yang terbaca dari gambar")
        return text
