from django.db import models
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="children",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        if self.parent:
            return f"{self.parent} > {self.name}"
        return self.name

    def get_absolute_url(self):
        return reverse("categories:category_detail", kwargs={"slug": self.slug})

    def get_descendant_ids(self):
        ids = [self.id]

        for child in self.children.all():
            ids.extend(child.get_descendant_ids())

        return ids

    def approved_listing_count(self):
        from listings.models import Listing

        return Listing.objects.filter(
            category_id__in=self.get_descendant_ids(),
            status=Listing.Status.APPROVED,
        ).count()
