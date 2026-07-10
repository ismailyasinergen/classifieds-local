from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError

V182_CATEGORY_HIERARCHY_SAFEGUARDS_MARKER = "V182_CATEGORY_HIERARCHY_SAFEGUARDS"


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

    def _iter_parent_chain_v182(self):
        """Yield parent categories while guarding against malformed in-memory cycles."""
        seen = set()
        parent = self.parent

        while parent is not None:
            parent_key = parent.pk if parent.pk is not None else id(parent)
            if parent_key in seen:
                raise ValidationError(
                    {"parent": "Category hierarchy contains a cycle."}
                )

            seen.add(parent_key)
            yield parent
            parent = parent.parent

    def clean(self):
        """Validate category hierarchy safety before admin/model form saves.

        V182_CATEGORY_HIERARCHY_CLEAN_METHOD
        """
        super().clean()

        if self.pk is not None and self.parent_id == self.pk:
            raise ValidationError(
                {"parent": "A category cannot be its own parent."}
            )

        for ancestor in self._iter_parent_chain_v182():
            if self.pk is not None and ancestor.pk == self.pk:
                raise ValidationError(
                    {"parent": "Category hierarchy cannot contain a cycle."}
                )
