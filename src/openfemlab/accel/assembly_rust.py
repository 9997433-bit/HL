"""Optional Rust-backed assembly kernels (GAP-13 spike)."""

from __future__ import annotations

__all__ = ["rust_assembly_available"]


def rust_assembly_available() -> bool:
    """Return whether the ``openfemlab_asm`` PyO3 extension is importable."""
    try:
        import openfemlab_asm  # noqa: F401
    except ImportError:
        return False
    return True
