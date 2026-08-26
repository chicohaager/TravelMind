"""`position_nur_ort` heisst jetzt `position_unsicher`

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-26

Migration 0007 nannte die Spalte `position_nur_ort`, weil das Kriterium damals
nur SIEDLUNGSTREFFER kannte. Der erste Trockenlauf gegen die echten Daten
zeigte noch am selben Tag, dass das zu eng ist: die Suchkette lieferte fuer
ein Kloster einen FLUSS, fuer eine Festung eine BAECKEREI und fuer ein
Restaurant ein TAL — alles keine Gemeinden, alles genauso falsch.

Das Kriterium deckt jetzt beides ab, und der alte Name wuerde in die Irre
fuehren: er verspraeche "es ist die Gemeinde", wo in Wahrheit steht "diese
Position gehoert nicht nachweislich zu diesem Namen".

Umbenannt statt erklaert, weil die Spalte zum Zeitpunkt dieser Migration
ueberall NULL ist (gemessen: 0 von 32 Zeilen gesetzt). Ein irrefuehrender
Feldname haelt sich sonst jahrelang.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("places", "position_nur_ort", new_column_name="position_unsicher")


def downgrade() -> None:
    op.alter_column("places", "position_unsicher", new_column_name="position_nur_ort")
