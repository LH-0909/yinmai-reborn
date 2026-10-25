"""Rebuild artwork slices and ornament-only frames from eight local references.

Usage: python scripts/rebuild_ui_assets.py [--source-dir folder]
No remote image requests; no frontend component rewrites.
"""
from pathlib import Path
import runpy
S=Path(__file__).resolve().parent
for name in ['extract_reference_ui.py','finalize_reference_masks.py','refine_ui_surfaces.py',
             'refine_ui_art_layers.py','extract_reference_icons.py','refine_mobile_art.py','refine_history_art.py','extract_panel_frames.py']:
    runpy.run_path(str(S/name),run_name='__main__')
