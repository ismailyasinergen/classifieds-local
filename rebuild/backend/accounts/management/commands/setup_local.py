import re
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Explicitly prepare the local brand and development catalog; never modifies user authentication data."

    def add_arguments(self, parser):
        parser.add_argument("--domain", default="127.0.0.1:8088")

    def handle(self, *args, **options):
        domain = options["domain"]
        if not settings.DEBUG or not re.fullmatch(r"(?:127\.0\.0\.1|localhost)(?::[0-9]{1,5})?", domain):
            raise CommandError("Bu kurulum yalnız yerel geliştirme adresleri için kullanılabilir.")
        Site.objects.update_or_create(pk=settings.SITE_ID, defaults={"name": "Classifieds Local", "domain": domain})
        Site.objects.clear_cache()
        call_command("seed_catalog", stdout=self.stdout)
        self.stdout.write("Classifieds Local yerel kurulumu hazır.")
