from django import forms


class StorefrontForm(forms.Form):
    name = forms.CharField(label="Vitrin adı", min_length=1, max_length=80)
    intro = forms.CharField(label="Tanıtım metni", max_length=2000, required=False,
                           widget=forms.Textarea(attrs={"rows": 6}),
                           help_text="Yayımlamayı seçtiğiniz düz metin; en fazla 2000 karakter.")


class StorefrontEditForm(StorefrontForm):
    edit_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)


class StorefrontVersionForm(forms.Form):
    edit_version = forms.IntegerField(min_value=1, widget=forms.HiddenInput)
