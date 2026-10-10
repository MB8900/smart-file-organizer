"""Single source of truth for the app's identity and version."""

from __future__ import annotations

APP_NAME = "Smart File Organizer"
__version__ = "1.1.0"
RELEASE_DATE = "2026-10-10"

AUTHOR = "Marber (MB8900)"
REPO_URL = "https://github.com/MB8900/smart-file-organizer"

LICENSE_NAME = "PolyForm Noncommercial 1.0.0"
LICENSE_URL = "https://polyformproject.org/licenses/noncommercial/1.0.0"
LICENSE_SUMMARY = (
    "Libero da usare, studiare, modificare e redistribuire per qualsiasi "
    "scopo non commerciale. L'uso commerciale non è concesso."
)

THIRD_PARTY = [
    ("CustomTkinter", "MIT"),
    ("Send2Trash", "BSD-3-Clause"),
    ("pypdf", "BSD-3-Clause"),
    ("python-docx", "MIT"),
    ("Pillow", "MIT-CMU"),
    ("requests", "Apache-2.0"),
]
