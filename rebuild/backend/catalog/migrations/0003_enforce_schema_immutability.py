# Empty migration proposed by Django 5.2.18 --dry-run, then authored via Bridge write.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_alter_attributeschema_options_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION catalog_reject_schema_mutation() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'AttributeSchema rows are immutable; insert a new version'
                        USING ERRCODE = '23514';
                END;
                $$;
                CREATE TRIGGER catalog_schema_immutable
                    BEFORE UPDATE OR DELETE ON catalog_attributeschema
                    FOR EACH ROW EXECUTE FUNCTION catalog_reject_schema_mutation();
            """,
            reverse_sql="""
                DROP TRIGGER catalog_schema_immutable ON catalog_attributeschema;
                DROP FUNCTION catalog_reject_schema_mutation();
            """,
        ),
    ]
