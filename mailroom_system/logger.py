"""
logger.py — Structured logging helper for Smart Mailroom System
Provides category-prefixed log helpers for: AUTH, PARCEL, OTP, FACE, FINGERPRINT
"""

import logging
import sys

# ─── ANSI colour codes (works on Windows 10+ terminals) ───────────────────────
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_BLUE   = "\033[94m"
_MAGENTA= "\033[95m"

# ─── Root logger setup ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Quieten noisy third-party loggers
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

_logger = logging.getLogger("mailroom")

# ─── Category helpers ─────────────────────────────────────────────────────────

def _fmt(colour: str, tag: str, msg: str) -> str:
    return f"{_BOLD}{colour}[{tag}]{_RESET} {msg}"


def log_auth(msg: str):
    _logger.info(_fmt(_GREEN, "AUTH", msg))

def log_auth_error(msg: str, exc: Exception | None = None):
    _logger.error(_fmt(_RED, "AUTH", msg))
    if exc:
        _logger.exception(exc)


def log_parcel(msg: str):
    _logger.info(_fmt(_CYAN, "PARCEL", msg))

def log_parcel_error(msg: str, exc: Exception | None = None):
    _logger.error(_fmt(_RED, "PARCEL", msg))
    if exc:
        _logger.exception(exc)


def log_otp(msg: str):
    _logger.info(_fmt(_YELLOW, "OTP", msg))

def log_otp_error(msg: str, exc: Exception | None = None):
    _logger.error(_fmt(_RED, "OTP", msg))
    if exc:
        _logger.exception(exc)


def log_face(msg: str):
    _logger.info(_fmt(_BLUE, "FACE", msg))

def log_face_error(msg: str, exc: Exception | None = None):
    _logger.error(_fmt(_RED, "FACE", msg))
    if exc:
        _logger.exception(exc)


def log_fingerprint(msg: str):
    _logger.info(_fmt(_MAGENTA, "FINGERPRINT", msg))

def log_fingerprint_error(msg: str, exc: Exception | None = None):
    _logger.error(_fmt(_RED, "FINGERPRINT", msg))
    if exc:
        _logger.exception(exc)


def log_system(msg: str):
    _logger.info(_fmt(_CYAN, "SYSTEM", msg))

def log_system_error(msg: str, exc: Exception | None = None):
    _logger.error(_fmt(_RED, "SYSTEM", msg))
    if exc:
        _logger.exception(exc)
