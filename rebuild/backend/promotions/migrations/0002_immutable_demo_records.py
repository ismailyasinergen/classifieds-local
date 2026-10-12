from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("promotions", "0001_initial")]
    operations = [migrations.RunSQL(
        sql="""
        CREATE FUNCTION promotions_immutable_record() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Promotion snapshot and demo evidence are immutable';
        END;
        $$;
        CREATE TRIGGER promotions_purchase_immutable BEFORE UPDATE OR DELETE ON promotions_purchase
            FOR EACH ROW EXECUTE FUNCTION promotions_immutable_record();
        CREATE TRIGGER promotions_evidence_immutable BEFORE UPDATE OR DELETE ON promotions_demoevidence
            FOR EACH ROW EXECUTE FUNCTION promotions_immutable_record();
        """,
        reverse_sql="""
        DROP TRIGGER promotions_evidence_immutable ON promotions_demoevidence;
        DROP TRIGGER promotions_purchase_immutable ON promotions_purchase;
        DROP FUNCTION promotions_immutable_record();
        """,
    )]