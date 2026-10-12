from uuid import uuid4

from django import forms


class MessageForm(forms.Form):
    body = forms.CharField(label="Mesajın", strip=False, widget=forms.Textarea(attrs={
        "rows": 6, "aria-describedby": "message-help", "autocomplete": "off",
    }))
    client_token = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["client_token"] = uuid4()

    # Normalization and Unicode limits belong to the mutation service.
    # Browser maxlength measures UTF-16 rather than Unicode code points.


def add_service_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)
    conflict = any(item.code == "token_conflict" for item in getattr(error, "error_list", []))
    if conflict:
        data = form.data.copy()
        data["client_token"] = str(uuid4())
        form.data = data
    return 409 if conflict else 400
