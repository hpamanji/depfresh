"""Format-preserving manifest editors, one family per module.

Where :mod:`depfresh.parsers` reads manifests, editors write a single
dependency's new version back into the manifest's raw text, leaving all other
formatting (comments, whitespace, ordering) untouched.
"""

from depfresh.editors.base import EditResult, Editor

__all__ = ["EditResult", "Editor"]
