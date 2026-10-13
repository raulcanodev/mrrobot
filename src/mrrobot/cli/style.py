"""Shared visual style for the interactive selectors (questionary).

Kept in its own module so the main menu and the report wizard can both
import it without creating a cycle between them (the menu opens the
wizard, so the wizard can't depend on the menu's module).
"""

from __future__ import annotations

from questionary import Style

QUESTIONARY_STYLE = Style(
    [
        ("qmark", "fg:#2ecc71 bold"),
        ("question", "bold"),
        ("pointer", "fg:#2ecc71 bold"),
        ("highlighted", "fg:#2ecc71 bold"),
        ("selected", "fg:#2ecc71"),
        ("answer", "fg:#2ecc71 bold"),
    ]
)
