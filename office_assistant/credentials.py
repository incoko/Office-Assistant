"""Small credential store with Windows DPAPI protection.

The normal JSON state stores only credential references. On Windows, secrets are
protected for the current user by CryptProtectData; no plaintext API key is
written to the state file. Non-Windows development uses process memory only.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
from pathlib import Path
import secrets


class CredentialError(RuntimeError):
    pass


class CredentialStore:
    def __init__(self, root: Path):
        self.root = root / "credentials"
        self.root.mkdir(parents=True, exist_ok=True)
        self._memory: dict[str, str] = {}

    def put(self, value: str, reference: str | None = None) -> str:
        if not value:
            return reference or ""
        reference = reference or secrets.token_hex(12)
        if not _IS_WINDOWS:
            self._memory[reference] = value
            return reference
        encrypted = _dpapi_protect(value.encode("utf-8"))
        self._path(reference).write_bytes(encrypted)
        return reference

    def get(self, reference: str | None) -> str | None:
        if not reference:
            return None
        if not _IS_WINDOWS:
            return self._memory.get(reference)
        path = self._path(reference)
        if not path.exists():
            return None
        return _dpapi_unprotect(path.read_bytes()).decode("utf-8")

    def delete(self, reference: str | None) -> None:
        if not reference:
            return
        self._memory.pop(reference, None)
        path = self._path(reference)
        if path.exists():
            path.unlink()

    def _path(self, reference: str) -> Path:
        if not reference or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in reference):
            raise CredentialError("invalid credential reference")
        return self.root / f"{reference}.bin"


_IS_WINDOWS = __import__("sys").platform == "win32"


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi_protect(data: bytes) -> bytes:
    if not _IS_WINDOWS:
        raise CredentialError("Windows DPAPI is unavailable")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    source = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    input_blob = _Blob(len(data), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    output_blob = _Blob()
    if not crypt32.CryptProtectData(ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _dpapi_unprotect(data: bytes) -> bytes:
    if not _IS_WINDOWS:
        raise CredentialError("Windows DPAPI is unavailable")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    source = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    input_blob = _Blob(len(data), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    output_blob = _Blob()
    if not crypt32.CryptUnprotectData(ctypes.byref(input_blob), None, None, None, None, 0, ctypes.byref(output_blob)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)
