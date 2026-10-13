"""Estilo visual compartido para los selectores interactivos (questionary).

En un módulo propio para que el menú principal y el asistente de informes
puedan importarlo sin crear un ciclo entre ellos (el menú abre el asistente,
así que el asistente no puede depender del módulo del menú).
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
