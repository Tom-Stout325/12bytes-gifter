from django.db import migrations


def drop_legacy_profile_columns(apps, schema_editor):
    """
    Drop legacy columns that still exist in the production Postgres DB
    but are no longer in the Django model.

    On SQLite (local dev), do nothing so the migration runs without errors.
    """
    if schema_editor.connection.vendor != "postgresql":
        # Local dev likely using SQLite – skip.
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE accounts_profile
            DROP COLUMN IF EXISTS avatar_choice,
            DROP COLUMN IF EXISTS created_at;
            """
        )


def restore_legacy_profile_columns(apps, schema_editor):
    """
    Reverse migration for Postgres only. On SQLite this is a no-op.
    """
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE accounts_profile
            ADD COLUMN IF NOT EXISTS avatar_choice varchar(255) NOT NULL DEFAULT '';
            """
        )
        cursor.execute(
            """
            ALTER TABLE accounts_profile
            ADD COLUMN IF NOT EXISTS created_at timestamp with time zone NOT NULL DEFAULT NOW();
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        # keep whatever was already here, e.g.:
        ("accounts", "0006_alter_profile_options_remove_profile_avatar_choice_and_more"),
    ]

    operations = [
        migrations.RunPython(
            drop_legacy_profile_columns,
            restore_legacy_profile_columns,
        ),
    ]

