from django import forms

from .models import Listing


OPTIONAL_ATTRIBUTE_FIELDS = [
    "brand",
    "model_name",
    "model_year",
    "mileage",
    "fuel_type",
    "transmission",
    "color",
    "condition",
    "warranty",
    "accepts_exchange",
]


class ListingForm(forms.ModelForm):
    brand = forms.CharField(label="Brand", required=False, max_length=80)
    model_name = forms.CharField(label="Model / Series", required=False, max_length=120)
    model_year = forms.IntegerField(label="Year", required=False, min_value=1900, max_value=2100)
    mileage = forms.IntegerField(label="Mileage / KM", required=False, min_value=0)
    fuel_type = forms.ChoiceField(
        label="Fuel Type",
        required=False,
        choices=[
            ("", "---------"),
            ("gasoline", "Gasoline"),
            ("diesel", "Diesel"),
            ("hybrid", "Hybrid"),
            ("electric", "Electric"),
            ("lpg", "LPG"),
            ("other", "Other"),
        ],
    )
    transmission = forms.ChoiceField(
        label="Transmission",
        required=False,
        choices=[
            ("", "---------"),
            ("manual", "Manual"),
            ("automatic", "Automatic"),
            ("semi_automatic", "Semi-automatic"),
            ("other", "Other"),
        ],
    )
    color = forms.CharField(label="Color", required=False, max_length=80)
    condition = forms.ChoiceField(
        label="Condition",
        required=False,
        choices=[
            ("", "---------"),
            ("new", "New"),
            ("used", "Used"),
            ("damaged", "Damaged"),
            ("other", "Other"),
        ],
    )
    warranty = forms.BooleanField(label="Warranty", required=False)
    accepts_exchange = forms.BooleanField(label="Accepts Exchange", required=False)

    class Meta:
        model = Listing
        fields = [
            "title",
            "description",
            "price",
            "category",
            "location",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        saved_attributes = getattr(self.instance, "attributes", None) or {}
        for field_name in OPTIONAL_ATTRIBUTE_FIELDS:
            if field_name in saved_attributes:
                self.fields[field_name].initial = saved_attributes[field_name]

        self.order_fields([
            "title",
            "description",
            "price",
            "category",
            "location",
            *OPTIONAL_ATTRIBUTE_FIELDS,
        ])

    def save(self, commit=True):
        instance = super().save(commit=False)
        attributes = dict(getattr(instance, "attributes", None) or {})

        for field_name in OPTIONAL_ATTRIBUTE_FIELDS:
            attributes.pop(field_name, None)
            value = self.cleaned_data.get(field_name)

            if isinstance(value, bool):
                if value:
                    attributes[field_name] = value
            elif value not in (None, ""):
                attributes[field_name] = value

        instance.attributes = attributes

        if commit:
            instance.save()
            self.save_m2m()

        return instance
