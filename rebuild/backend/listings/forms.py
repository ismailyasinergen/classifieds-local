from django import forms
from catalog.models import AttributeSchema, Category
from catalog.validation import normalize_attribute_value
from .validation import normalize_draft_content


class CategoryForm(forms.Form):
    category = forms.ChoiceField(label="İlan kategorisi", choices=())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = {item.pk: item for item in Category.objects.all()}
        available = set(AttributeSchema.objects.values_list("category_id", flat=True))
        choices = []
        for item in categories.values():
            if item.pk not in available:
                continue
            labels, seen, node = [], set(), item
            while node is not None and node.pk not in seen:
                seen.add(node.pk)
                labels.append(node.name)
                node = categories.get(node.parent_id)
            choices.append((item.pk, " › ".join(reversed(labels))))
        self.fields["category"].choices = [("", "Kategori seçin"), *sorted(choices, key=lambda pair: pair[1])]

    def clean_category(self):
        return int(self.cleaned_data["category"])


class DraftForm(forms.Form):
    edit_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
    title = forms.CharField(label="İlan başlığı", max_length=200, required=False)
    description = forms.CharField(label="Açıklama", max_length=20000, required=False,
                                  widget=forms.Textarea(attrs={"rows": 6}))
    price = forms.DecimalField(label="Fiyat", max_digits=18, decimal_places=2, min_value=0,
                               required=False, help_text="Boş bırakırsanız taslak olarak kaydedilir.")
    currency = forms.CharField(label="Para birimi", max_length=3, required=False, help_text="Örneğin TRY, EUR veya USD.")
    location = forms.CharField(label="Konum", max_length=160, required=False,
                               help_text="Şehir veya semt; özel adresinizi yazmayın.")

    def __init__(self, *args, revision, **kwargs):
        self.revision = revision
        initial = {name: getattr(revision, name) for name in ("title", "description", "price", "currency", "location")}
        initial["edit_version"] = revision.edit_version
        self.rules = revision.attribute_schema.definition["fields"]
        for name, rule in self.rules.items():
            value = revision.attributes.get(name, "")
            if rule["type"] == "boolean" and type(value) is bool:
                value = "true" if value else "false"
            initial[f"attr_{name}"] = value
        kwargs.setdefault("initial", initial)
        super().__init__(*args, **kwargs)
        for name, rule in self.rules.items():
            help_parts = []
            if rule.get("required"):
                help_parts.append("İncelemeye göndermek için gereklidir.")
            if rule.get("unit"):
                help_parts.append(rule["unit"])
            if "min" in rule:
                help_parts.append(f"En az {rule['min']}.")
            if "max" in rule:
                help_parts.append(f"En fazla {rule['max']}.")
            common = {"label": rule.get("label", name.replace("_", " ").capitalize()),
                      "required": False, "help_text": " ".join(help_parts)}
            if rule["type"] == "boolean":
                field = forms.ChoiceField(choices=[("", "Seçilmedi"), ("true", "Evet"), ("false", "Hayır")], **common)
            elif rule.get("options"):
                option_rule = {key: value for key, value in rule.items() if key != "options"}
                choices = [(str(normalize_attribute_value(name=name, rule=option_rule, value=value)), str(value))
                           for value in rule["options"]]
                field = forms.ChoiceField(choices=[("", "Seçilmedi"), *choices], **common)
            else:
                field = forms.CharField(**common)
                if rule["type"] in ("integer", "decimal"):
                    field.widget.attrs["inputmode"] = "numeric" if rule["type"] == "integer" else "decimal"
            self.fields[f"attr_{name}"] = field

    def clean(self):
        values = super().clean()
        attributes = {}
        for name, rule in self.rules.items():
            key = f"attr_{name}"
            value = values.get(key, "")
            if value == "":
                continue
            if rule["type"] == "boolean":
                value = value == "true"
            try:
                attributes[name] = normalize_attribute_value(name=name, rule=rule, value=value)
            except forms.ValidationError as error:
                self.add_error(key, error.messages)
        if not self.errors:
            content = {name: values[name] for name in ("title", "description", "price", "currency", "location")}
            content["attributes"] = attributes
            try:
                self.content = normalize_draft_content(schema=self.revision.attribute_schema, content=content)
            except forms.ValidationError as error:
                add_service_errors(self, error)
        return values


class UploadForm(forms.Form):
    image = forms.FileField(label="Fotoğraf seçin", widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
                            help_text="JPEG, PNG veya WebP. En çok 10 MiB, 20 megapiksel ve ilan başına 10 fotoğraf.")


def add_service_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            target = field if field in form.fields else None
            for item in errors:
                form.add_error(target, item)
    else:
        form.add_error(None, error)
