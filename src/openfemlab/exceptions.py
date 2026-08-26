"""Exception hierarchy shared by all OpenFEMLab subpackages."""

from __future__ import annotations

__all__ = ["OpenFEMLabError", "ModelError", "ElementError", "SolverError"]


class OpenFEMLabError(Exception):
    """Base class for every error raised by OpenFEMLab."""


class ModelError(OpenFEMLabError):
    """Invalid model definition (unknown nodes, DOFs, duplicate ids, ...)."""


class ElementError(OpenFEMLabError):
    """Invalid element definition or degenerate element geometry."""


class SolverError(OpenFEMLabError):
    """The requested analysis cannot be carried out."""
