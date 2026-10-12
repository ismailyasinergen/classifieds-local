from django.contrib.postgres.indexes import GinIndex, OpClass
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models

from listings.search.expressions import folded_location_v1, folded_title_v1, search_vector_v1


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0002_alter_listing_options_alter_listingrevision_options_and_more"),
    ]

    # These versioned factories are frozen migration dependencies. New search
    # semantics must use new factories/classes and a separate migration.
    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name="listingrevision",
            index=GinIndex(search_vector_v1(), name="search_document_v1_gin",
                           condition=models.Q(status="approved")),
        ),
        migrations.AddIndex(
            model_name="listingrevision",
            index=GinIndex(OpClass(folded_title_v1(), name="gin_trgm_ops"),
                           name="search_title_v1_trgm", condition=models.Q(status="approved")),
        ),
        migrations.AddIndex(
            model_name="listingrevision",
            index=GinIndex(OpClass(folded_location_v1(), name="gin_trgm_ops"),
                           name="search_location_v1_trgm", condition=models.Q(status="approved")),
        ),
    ]
