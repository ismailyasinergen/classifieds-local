"""Report the read-only v324 listing-detail asset extraction boundary."""

import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from listings.listing_detail_asset_boundary_v324 import (
    audit_listing_detail_asset_boundary_v324,
)


class Command(BaseCommand):
    help = (
        "Audit listing-detail inline asset blocks, source contracts, and CSP "
        "cutover blockers without modifying files or data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Emit deterministic machine-readable JSON.",
        )
        parser.add_argument(
            "--fail-on-blockers",
            action="store_true",
            help="Return a command error while cutover blockers remain.",
        )

    def handle(self, *args, **options):
        backend_dir = settings.BASE_DIR
        report = audit_listing_detail_asset_boundary_v324(
            template_path=(
                backend_dir
                / "listings"
                / "templates"
                / "listings"
                / "listing_detail.html"
            ),
            backend_dir=backend_dir,
        )

        if options["json_output"]:
            self.stdout.write(
                json.dumps(
                    report.as_dict(),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        else:
            self.stdout.write(
                "Listing-detail asset boundary v324: "
                f"styles={len(report.style_blocks)} "
                f"scripts={len(report.script_blocks)} "
                "template_dependent="
                f"{report.template_dependent_block_count} "
                f"inline_handlers={len(report.inline_event_handlers)} "
                f"source_contract_tests={len(report.source_contract_tests)} "
                "mechanically_extractable="
                f"{str(report.mechanically_extractable).lower()} "
                f"cutover_ready={str(report.cutover_ready).lower()} "
                f"strict_csp_ready={str(report.strict_csp_ready).lower()} "
                "read_only=true"
            )
            self.stdout.write(
                "planned_css="
                + report.as_dict()["planned_css_asset"]
            )
            self.stdout.write(
                "planned_js="
                + report.as_dict()["planned_js_asset"]
            )
            for code in report.blocker_codes:
                self.stdout.write(f"blocker code={code}")

        if options["fail_on_blockers"] and not report.cutover_ready:
            raise CommandError(
                "Listing-detail asset cutover blockers remain: "
                + ", ".join(report.blocker_codes)
            )
