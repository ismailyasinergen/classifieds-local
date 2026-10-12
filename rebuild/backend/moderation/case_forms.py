from uuid import uuid4
from django import forms
from .case_inputs import LISTING_REASONS, MESSAGE_REASONS


class AppealForm(forms.Form):
    explanation = forms.CharField(label="Açıklama", max_length=2000, widget=forms.Textarea(attrs={"rows": 5}),
        help_text="Kişisel belge, parola veya doğrulama kodu paylaşmayın.")
    client_token = forms.UUIDField(initial=uuid4, widget=forms.HiddenInput)


class ReportForm(AppealForm):
    reason_code = forms.ChoiceField(label="Bildirim nedeni")
    field_order = ["reason_code", "explanation", "client_token"]

    def __init__(self, *args, target_type, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reason_code"].choices = LISTING_REASONS if target_type == "listing" else MESSAGE_REASONS


class ReportDecisionForm(forms.Form):
    action = forms.ChoiceField(label="Karar")
    reason = forms.CharField(label="Kullanıcıya gösterilecek gerekçe", max_length=2000, widget=forms.Textarea(attrs={"rows": 5}))
    expected_public_revision_id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    ends_at = forms.DateTimeField(label="Kısıt bitiş zamanı", required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        help_text="Mesajlaşma kısıtı için gelecekteki yerel tarih ve saat.")

    def __init__(self, *args, target_type, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["action"].choices = [("no_action", "İşlem yok"),
            ("hide_listing", "İlanı gizle") if target_type == "listing" else ("restrict_messaging", "Mesajlaşmayı kısıtla")]
        if target_type == "listing":
            self.fields["ends_at"].widget = forms.HiddenInput()


class AppealDecisionForm(forms.Form):
    outcome = forms.ChoiceField(label="İtiraz kararı", choices=[("uphold", "Kararı koru"), ("revoke", "Yaptırımı geri al")])
    reason = forms.CharField(label="Kullanıcıya gösterilecek gerekçe", max_length=2000, widget=forms.Textarea(attrs={"rows": 5}))
