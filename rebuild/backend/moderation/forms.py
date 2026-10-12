from django import forms


class ReviewForm(forms.Form):
    expected_public_revision_id = forms.IntegerField(required=False, min_value=1, widget=forms.HiddenInput)
    action = forms.ChoiceField(label="İnceleme kararı", choices=[("approve", "Onayla ve yayımla"), ("reject", "Düzeltme iste")])
    reason = forms.CharField(label="Karar gerekçesi", max_length=2000, widget=forms.Textarea(attrs={"rows": 4}),
                             help_text="İlan sahibinin göreceği açık bir gerekçe yazın.")
