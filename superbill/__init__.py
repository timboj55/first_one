"""Automatic superbills for PracticeQ (IntakeQ) clients.

Pipeline: completed appointments + invoices + diagnoses  ->  superbill data  ->  PDF  ->  the
client's Files tab in PracticeQ (replacing the previous superbill). See docs/SUPERBILL_SETUP.md.
"""

from .build import SuperbillData, build_superbill
from .render import render_pdf
from .sync import SuperbillSync

__all__ = ["SuperbillData", "SuperbillSync", "build_superbill", "render_pdf"]
