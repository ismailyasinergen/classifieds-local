from django.core.exceptions import ValidationError
from django.db import models
from .validation import validate_schema_definition


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class ImmutableSchemaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Kayıtlı şema değiştirilemez; yeni sürüm oluşturun.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Kayıtlı şema değiştirilemez; yeni sürüm oluşturun.")

    def delete(self):
        raise ValidationError("Kayıtlı şema silinemez.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValidationError("Kayıtlı şema değiştirilemez.")
        objs = list(objs)
        for obj in objs:
            obj.full_clean()
        return super().bulk_create(objs, **kwargs)


class AttributeSchema(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="attribute_schemas")
    version = models.PositiveIntegerField()
    definition = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = ImmutableSchemaQuerySet.as_manager()

    class Meta:
        ordering = ["category_id", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["category", "version"], name="catalog_schema_category_version_unique"),
            models.CheckConstraint(condition=models.Q(version__gte=1), name="catalog_schema_positive_version"),
        ]

    def clean(self):
        super().clean()
        validate_schema_definition(self.definition)

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Kayıtlı şema değiştirilemez; yeni sürüm oluşturun.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Kayıtlı şema silinemez.")

    def __str__(self):
        return f"{self.category_id} / v{self.version}"
