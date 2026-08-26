"""Orte duerfen eine unbekannte Position haben; 0/0 wird geheilt

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-26

Bis hierher waren `places.latitude` und `places.longitude` NOT NULL. "Position
unbekannt" liess sich damit gar nicht ausdruecken, und eine fehlgeschlagene
Geokodierung wurde als 0.0/0.0 gespeichert — die Null-Insel im Golf von
Guinea. Auf der Karte war das nicht als Luecke erkennbar, sondern als Ort im
Atlantik: bei Zoomstufe 18 einfarbig blauer Ozean, alle Marker exakt
uebereinander.

Diese Migration macht beide Spalten nullable und setzt bestehende 0/0-Paare
auf NULL. Die Schranke 0.001 Grad entspricht rund 111 Metern um den
Nullpunkt — dort liegt kein Reiseort absichtlich.

Beim Zurueckrollen muessen die Spalten wieder NOT NULL werden. Damit das
gelingt, bekommen Orte ohne Position dabei zwangslaeufig wieder 0/0 — der
alte Zustand, mit allem was daran falsch war. Das ist keine Nachlaessigkeit,
sondern die einzige Moeglichkeit, die alte Bedingung ueberhaupt herzustellen.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 0.001 Grad ~ 111 m. Dieselbe Schranke wie in utils/geocoding.py.
NULL_INSEL = "ABS(latitude) < 0.001 AND ABS(longitude) < 0.001"


def upgrade() -> None:
    op.alter_column("places", "latitude", existing_type=sa.Float(), nullable=True)
    op.alter_column("places", "longitude", existing_type=sa.Float(), nullable=True)

    # Bestehende Ersatzwerte heilen: was auf der Null-Insel liegt, hat in
    # Wahrheit keine Position.
    op.execute(
        sa.text(
            f"UPDATE places SET latitude = NULL, longitude = NULL WHERE {NULL_INSEL}"
        )
    )


def downgrade() -> None:
    # NOT NULL laesst sich nur wiederherstellen, wenn kein NULL mehr dasteht.
    op.execute(
        sa.text(
            "UPDATE places SET latitude = 0.0, longitude = 0.0 "
            "WHERE latitude IS NULL OR longitude IS NULL"
        )
    )
    op.alter_column("places", "latitude", existing_type=sa.Float(), nullable=False)
    op.alter_column("places", "longitude", existing_type=sa.Float(), nullable=False)
