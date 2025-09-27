"""Compatibility shim exposing enhanced Phase 1 configuration helpers."""

from app.core.config import RAGPresets, Settings, apply_preset, settings

__all__ = ["Settings", "settings", "RAGPresets", "apply_preset"]
