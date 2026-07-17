from __future__ import annotations

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def backfill_listing_price_history_v275(
    apps,
    schema_editor,
):
    Listing = apps.get_model(
        "listings",
        "Listing",
    )
    ListingPriceHistory = apps.get_model(
        "listings",
        "ListingPriceHistory",
    )

    using = schema_editor.connection.alias
    pending = []

    queryset = (
        Listing.objects
        .using(using)
        .all()
        .order_by("pk")
    )

    for listing in queryset.iterator(
        chunk_size=500,
    ):
        pending.append(
            ListingPriceHistory(
                listing_id=listing.pk,
                previous_price=None,
                new_price=listing.price,
                changed_at=listing.created_at,
            )
        )

        if len(pending) >= 500:
            (
                ListingPriceHistory
                .objects
                .using(using)
                .bulk_create(
                    pending,
                    batch_size=500,
                )
            )
            pending.clear()

    if pending:
        (
            ListingPriceHistory
            .objects
            .using(using)
            .bulk_create(
                pending,
                batch_size=500,
            )
        )


def remove_listing_price_history_v275(
    apps,
    schema_editor,
):
    ListingPriceHistory = apps.get_model(
        "listings",
        "ListingPriceHistory",
    )

    (
        ListingPriceHistory
        .objects
        .using(schema_editor.connection.alias)
        .all()
        .delete()
    )


class Migration(migrations.Migration):
    dependencies = [
        (
            "listings",
            "0016_savedsearchnotificationauditevent",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="ListingPriceHistory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "previous_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "new_price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                    ),
                ),
                (
                    "changed_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        editable=False,
                    ),
                ),
                (
                    "listing",
                    models.ForeignKey(
                        on_delete=(
                            django.db.models.deletion.CASCADE
                        ),
                        related_name="price_history",
                        to="listings.listing",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "-changed_at",
                    "-pk",
                ],
                "indexes": [
                    models.Index(
                        fields=[
                            "listing",
                            "-changed_at",
                        ],
                        name="lst_price_hist_lc_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(
                            previous_price__isnull=True,
                        ),
                        fields=("listing",),
                        name="lst_price_hist_base_uniq",
                    ),
                ],
            },
        ),
        migrations.RunPython(
            backfill_listing_price_history_v275,
            remove_listing_price_history_v275,
        ),
    ]
