"""Orte merken sich, ob ihre Position ortsgenau oder objektgenau ist

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-26

Am 2026-08-26 an 16 Orten einer echten Reise gemessen: **9** Positionen waren
Gemeindemittelpunkte, nicht die genannte Sache. Der Geocoder faellt am Ende
seiner Suchkette auf den blossen Ortsnamen zurueck, und dessen Koordinaten
sahen bis dahin genauso aus wie ein echter Fund. Auf der Karte war
"Aussichtspunkt Repušnica" nicht von "Terme Jezerčica" zu unterscheiden —
beide ein Punkt, beide ohne Vorbehalt.

Drei Zustaende, und die Unterscheidung ist der Zweck:

    NULL   ungeprueft — Altbestand oder mitgebrachte Koordinaten
    TRUE   ortsgenau  — gefunden wurde die SIEDLUNG, nicht die Sache
    FALSE  objektgenau — der gesuchte Gegenstand selbst wurde gefunden

Bewusst kein Default auf FALSE: das hiesse "objektgenau" fuer jeden Altbestand
und waere eine Zusicherung ohne Pruefung. NULL sagt ehrlich, dass es niemand
weiss.

Beim Zurueckrollen faellt nur die Spalte weg; Positionen bleiben unberuehrt.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("places", sa.Column("position_nur_ort", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "position_nur_ort")
