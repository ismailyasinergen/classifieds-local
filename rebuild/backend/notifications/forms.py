import json

from django import forms
from django.core.exceptions import ValidationError

from listings.search.parsing import search_spec_from_dict, search_spec_to_dict, search_querystring


class SearchNameForm(forms.Form):
    name = forms.CharField(label="Arama adı", min_length=1, max_length=80, strip=True)


class SaveSearchForm(SearchNameForm):
    spec = forms.CharField(widget=forms.HiddenInput, max_length=32768)

    def clean_spec(self):
        try:
            spec = search_spec_from_dict(json.loads(self.cleaned_data["spec"]))
            search_querystring(spec)
            return search_spec_to_dict(spec)
        except (ValueError, TypeError, RecursionError, ValidationError):
            raise ValidationError("Arama ölçütleri geçersiz. Arama ekranından yeniden kaydedin.") from None
