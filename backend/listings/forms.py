from django import forms

from .attribute_schema import (
    get_all_attribute_definitions,
    get_attribute_definitions_for_category,
    get_attribute_field_name,
    get_attribute_key_from_field_name,
    get_category_schema_by_id,
    get_known_attribute_keys,
    parse_boolean,
)
from .models import Listing


BASE_LISTING_FIELDS = [
    "title",
    "description",
    "price",
    "category",
    "location",
]


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = BASE_LISTING_FIELDS
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["price"].disabled = True
            self.fields["price"].help_text = (
                "Price changes require a separate review and confirmation."
            )

        self.base_field_names = list(BASE_LISTING_FIELDS)
        self.attribute_field_names = []
        self.category_schema_by_id = get_category_schema_by_id()

        saved_attributes = getattr(self.instance, "attributes", None) or {}

        for attribute in get_all_attribute_definitions():
            field_name = get_attribute_field_name(attribute["key"])
            field = self._build_attribute_field(attribute)

            if attribute["key"] in saved_attributes:
                value = saved_attributes[attribute["key"]]

                if attribute.get("input_type") == "boolean":
                    parsed = parse_boolean(value)
                    if parsed is True:
                        field.initial = "true"
                    elif parsed is False:
                        field.initial = "false"
                else:
                    field.initial = value

            self.fields[field_name] = field
            self.attribute_field_names.append(field_name)

        self.order_fields([*BASE_LISTING_FIELDS, *self.attribute_field_names])

    def _build_attribute_field(self, attribute):
        attrs = {
            "data-schema-keys": ",".join(attribute.get("schema_keys", [])),
            "data-local-category-slugs": ",".join(attribute.get("local_category_slugs", [])),
        }

        label = attribute.get("label", attribute["key"].replace("_", " ").title())

        if attribute.get("input_type") == "boolean":
            field = forms.ChoiceField(
                label=label,
                required=False,
                choices=[
                    ("", "---------"),
                    ("true", "Yes"),
                    ("false", "No"),
                ],
            )
        else:
            field = forms.CharField(
                label=label,
                required=False,
                max_length=180,
            )

            if attribute.get("input_type") == "number":
                attrs["inputmode"] = "decimal"

        field.widget.attrs.update(attrs)
        return field

    def _selected_category(self, instance):
        category = getattr(instance, "category", None)

        if category:
            return category

        category_id = self.cleaned_data.get("category") or self.data.get("category")

        return category_id if hasattr(category_id, "slug") else None

    def save(self, commit=True):
        instance = super().save(commit=False)
        attributes = dict(getattr(instance, "attributes", None) or {})

        for key in get_known_attribute_keys():
            attributes.pop(key, None)

        selected_attribute_definitions = get_attribute_definitions_for_category(instance.category)

        for attribute in selected_attribute_definitions:
            key = attribute["key"]
            field_name = get_attribute_field_name(key)
            value = self.cleaned_data.get(field_name)

            if attribute.get("input_type") == "boolean":
                parsed = parse_boolean(value)
                if parsed is not None:
                    attributes[key] = parsed
            elif value not in (None, ""):
                attributes[key] = value

        instance.attributes = attributes

        if commit:
            instance.save()
            self.save_m2m()

        return instance
