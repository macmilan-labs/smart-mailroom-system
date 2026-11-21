"""
biometric_service.py — Face encoding & verification for Smart Mailroom
=======================================================================
Strategy:
  1. Try to import `face_recognition` (requires dlib — optional C-extension).
     If available → real 128-float face embedding, cosine/distance comparison.
  2. Fallback (PIL only, pure-Python) → store the raw base64 JPEG and compare
     using a perceptual hash (8×8 average-hash).  Works on any Windows machine
     with Pillow installed.

Both paths expose the same two public functions:
    encode_face(base64_image: str) -> str          # JSON to store in DB
    verify_face(stored: str, new_image: str) -> bool
"""

import base64
import hashlib
import io
import json
import logging

_logger = logging.getLogger("mailroom")

# ── Try real face_recognition ────────────────────────────────────────────────
try:
    import face_recognition  # type: ignore
    import numpy as np       # type: ignore
    _USE_FACE_RECOGNITION = True
    _logger.info("[FACE] face_recognition library available — using real embeddings")
except ImportError:
    _USE_FACE_RECOGNITION = False
    _logger.warning(
        "[FACE] face_recognition not installed — using PIL perceptual-hash fallback. "
        "Install with: pip install face_recognition"
    )

# ── Try PIL (Pillow) ─────────────────────────────────────────────────────────
try:
    from PIL import Image  # type: ignore
    _USE_PIL = True
except ImportError:
    _USE_PIL = False
    _logger.warning("[FACE] Pillow not installed — install with: pip install Pillow")


# ═══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _b64_to_bytes(b64_str: str) -> bytes:
    """
    Accept both plain base64 and data-URL prefix
    (e.g. 'data:image/jpeg;base64,/9j/…').
    """
    if b64_str.startswith("data:"):
        b64_str = b64_str.split(",", 1)[1]
    return base64.b64decode(b64_str)


def _ahash(img_bytes: bytes, size: int = 8) -> str:
    """
    Compute an 8×8 average perceptual hash of an image.
    Returns a 64-character hex string.
    Requires PIL.
    """
    img = Image.open(io.BytesIO(img_bytes)).convert("L").resize((size, size), Image.LANCZOS)
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p >= avg else "0" for p in pixels)
    hex_hash = "{:0>16x}".format(int(bits, 2))
    return hex_hash


def _hamming_distance(h1: str, h2: str) -> int:
    """Bit-level hamming distance between two hex hash strings."""
    n1 = int(h1, 16)
    n2 = int(h2, 16)
    xor = n1 ^ n2
    return bin(xor).count("1")


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def encode_face(base64_image: str) -> str:
    """
    Process a base64-encoded JPEG/PNG and return a JSON string suitable for
    storage in the `face_encoding` DB column.

    With face_recognition:  {"type": "embedding", "data": [float, …]}   (128 floats)
    With PIL fallback:       {"type": "ahash",     "data": "<hex>"}
    Without either:          {"type": "raw_b64",   "data": "<truncated>"}

    Raises ValueError if no face is detected (face_recognition path only).
    """
    img_bytes = _b64_to_bytes(base64_image)

    if _USE_FACE_RECOGNITION:
        # Decode image for face_recognition (expects RGB numpy array)
        img = face_recognition.load_image_file(io.BytesIO(img_bytes))
        encodings = face_recognition.face_encodings(img)
        if not encodings:
            raise ValueError("No face detected in the captured image. Please retake.")
        embedding = encodings[0].tolist()  # list[float], 128 elements
        return json.dumps({"type": "embedding", "data": embedding})

    if _USE_PIL:
        ahash = _ahash(img_bytes)
        return json.dumps({"type": "ahash", "data": ahash})

    # Last resort — store the raw base64 (no comparison possible, registration only)
    _logger.warning("[FACE] No image library available; storing raw base64 (no comparison)")
    raw = base64_image[:512]  # truncate for safety
    return json.dumps({"type": "raw_b64", "data": raw})


def verify_face(stored_encoding: str, new_image: str, threshold: float = 0.6) -> bool:
    """
    Compare a newly captured face image against the stored encoding.

    Returns True if they match within the given threshold, False otherwise.
    Threshold meanings:
      - embedding path: cosine tolerance (face_recognition default ~0.6)
      - ahash path: max allowed hamming distance out of 64 bits (default 10)
    """
    img_bytes = _b64_to_bytes(new_image)

    try:
        stored = json.loads(stored_encoding)
    except Exception:
        _logger.error("[FACE] Could not parse stored encoding JSON")
        return False

    enc_type = stored.get("type")

    # ── Real embedding comparison ────────────────────────────────────────────
    if enc_type == "embedding" and _USE_FACE_RECOGNITION:
        stored_vec = np.array(stored["data"])
        new_img = face_recognition.load_image_file(io.BytesIO(img_bytes))
        new_encodings = face_recognition.face_encodings(new_img)
        if not new_encodings:
            _logger.warning("[FACE] verify: no face detected in new image")
            return False
        results = face_recognition.compare_faces(
            [stored_vec], new_encodings[0], tolerance=threshold
        )
        return bool(results[0])

    # ── Perceptual hash comparison ───────────────────────────────────────────
    if enc_type == "ahash" and _USE_PIL:
        stored_hash = stored["data"]
        new_hash = _ahash(img_bytes)
        distance = _hamming_distance(stored_hash, new_hash)
        # Allow up to 10 bit differences out of 64 (≈ 84% similarity)
        max_bits = int(threshold * 64 / 0.6)  # scale threshold → bit budget
        _logger.info(f"[FACE] verify: ahash distance={distance}, budget={max_bits}")
        return distance <= max_bits

    # ── Type mismatch or missing library ────────────────────────────────────
    # If embedding stored but no face_recognition, or raw_b64: cannot verify → deny
    _logger.warning(
        f"[FACE] verify: cannot compare — stored type='{enc_type}', "
        f"face_recognition={_USE_FACE_RECOGNITION}, PIL={_USE_PIL}"
    )
    return False
