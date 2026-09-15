"""
utils/flet_dnd.py - Forwarding shim for flet_dnd module.
"""
try:
    from flet_dnd import FletDropTarget, FletDnD, setup_flet_dnd, _find_window_hwnds
except ImportError:
    from src.flet_dnd import FletDropTarget, FletDnD, setup_flet_dnd, _find_window_hwnds

# Alias for backwards compat
COMDropTarget = FletDropTarget

__all__ = ["COMDropTarget", "FletDropTarget", "FletDnD", "setup_flet_dnd", "_find_window_hwnds"]
