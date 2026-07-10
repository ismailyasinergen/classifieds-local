from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from categories.models import Category
from categories.seed_taxonomy_v183 import (
    V183_CATEGORY_SEED_TAXONOMY_MARKER,
    build_category_seed_plan_v183,
    summarize_category_seed_plan_v183,
)


V183_CATEGORY_SEED_COMMAND_MARKER = "V183_CATEGORY_SEED_COMMAND_DRY_RUN_FIRST"


@dataclass(frozen=True)
class SeedResultV183:
    created: int
    updated: int
    unchanged: int
    planned: int


class Command(BaseCommand):
    help = "Seed the pilot marketplace category taxonomy. Defaults to dry-run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the seed plan. Without this flag the command only performs a dry run.",
        )

    def handle(self, *args, **options):
        apply_changes = bool(options.get("apply"))
        records = build_category_seed_plan_v183()
        summary = summarize_category_seed_plan_v183(records)

        self.stdout.write(V183_CATEGORY_SEED_COMMAND_MARKER)
        self.stdout.write(V183_CATEGORY_SEED_TAXONOMY_MARKER)
        self.stdout.write(
            "Plan: "
            f"{summary['total']} categories "
            f"({summary['roots']} roots, "
            f"{summary['children']} children, "
            f"{summary['grandchildren']} grandchildren, "
            f"max depth {summary['max_depth']})"
        )

        if not apply_changes:
            for record in records:
                existing = Category.objects.filter(slug=record.slug).first()
                action = "unchanged" if existing else "create"
                self.stdout.write(
                    f"DRY-RUN {action}: depth={record.depth} "
                    f"slug={record.slug} parent={record.parent_slug or '-'} "
                    f"name={record.name}"
                )
            self.stdout.write("Dry run complete. Re-run with --apply to write changes.")
            return

        try:
            result = self._apply_seed_plan(records)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Applied category seed plan: "
                f"planned={result.planned}, "
                f"created={result.created}, "
                f"updated={result.updated}, "
                f"unchanged={result.unchanged}"
            )
        )

    @transaction.atomic
    def _apply_seed_plan(self, records) -> SeedResultV183:
        categories_by_slug: dict[str, Category] = {
            category.slug: category for category in Category.objects.all()
        }

        created = 0
        updated = 0
        unchanged = 0

        for record in records:
            parent = None
            if record.parent_slug:
                parent = categories_by_slug.get(record.parent_slug)
                if parent is None:
                    raise CommandError(
                        f"Parent `{record.parent_slug}` for `{record.slug}` is missing."
                    )

            category = categories_by_slug.get(record.slug)
            if category is None:
                category = Category(name=record.name, slug=record.slug, parent=parent)
                category.full_clean()
                category.save()
                categories_by_slug[record.slug] = category
                created += 1
                continue

            changed = False
            if category.name != record.name:
                category.name = record.name
                changed = True
            if category.parent_id != (parent.pk if parent else None):
                category.parent = parent
                changed = True

            if changed:
                category.full_clean()
                category.save()
                updated += 1
            else:
                unchanged += 1

        return SeedResultV183(
            created=created,
            updated=updated,
            unchanged=unchanged,
            planned=len(records),
        )
