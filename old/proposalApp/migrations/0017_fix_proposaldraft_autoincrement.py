from django.db import migrations, connection

def fix_autoincrement(apps, schema_editor):
    # Tables we want to fix (add more if needed)
    tables = [
        apps.get_model("proposalApp", "ProposalDraft")._meta.db_table,
    ]

    with connection.cursor() as c:
        for tbl in tables:
            # Ensure the 'id' column is AUTO_INCREMENT (INT)
            c.execute(f"SHOW COLUMNS FROM `{tbl}` LIKE 'id'")
            col = c.fetchone()  # Field, Type, Null, Key, Default, Extra
            if not col:
                continue
            field, coltype, null, key, default, extra = col
            # If it's not auto_increment, make it so (keep INT; no type change)
            if "auto_increment" not in (extra or ""):
                c.execute(f"ALTER TABLE `{tbl}` MODIFY COLUMN `id` INT NOT NULL AUTO_INCREMENT")

            # Compute next id = MAX(id)+1
            c.execute(f"SELECT COALESCE(MAX(id), 0) + 1 FROM `{tbl}`")
            next_id = c.fetchone()[0] or 1

            # Set AUTO_INCREMENT to next_id
            c.execute(f"ALTER TABLE `{tbl}` AUTO_INCREMENT = %s", [int(next_id)])

class Migration(migrations.Migration):
    dependencies = [
        # replace with your last migration
        ('proposalApp', '0016_discount_stackable'),
    ]
    operations = [
        migrations.RunPython(fix_autoincrement, migrations.RunPython.noop),
    ]
