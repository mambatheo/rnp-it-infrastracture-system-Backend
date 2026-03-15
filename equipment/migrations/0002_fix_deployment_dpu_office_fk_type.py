"""
Fix deployment.issued_to_dpu_office_id column type from bigint → uuid.

The DPUOffice model was updated to use a UUIDField primary key, but the
deployment table still has the old bigint FK column. This migration uses
raw SQL to safely cast/alter that column to match.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('equipment', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # ── Forward: alter bigint → uuid ──────────────────────────────────
            sql="""
                ALTER TABLE deployment
                    ALTER COLUMN issued_to_dpu_office_id
                    TYPE uuid USING issued_to_dpu_office_id::text::uuid;
            """,
            # ── Reverse: alter uuid → bigint (best-effort, data may be lost) ─
            reverse_sql="""
                ALTER TABLE deployment
                    ALTER COLUMN issued_to_dpu_office_id
                    TYPE bigint USING NULL;
            """,
        ),
    ]
