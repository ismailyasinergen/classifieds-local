import uuid
from django import forms
from django.db.models import Q
from .models import PromotionProduct


class PurchaseForm(forms.Form):
    product = forms.ModelChoiceField(label="Demo paketi", queryset=PromotionProduct.objects.none())
    key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, actor=None, **kwargs):
        super().__init__(*args, **kwargs)
        products = Q(enabled=True)
        if self.is_bound and actor is not None:
            try:
                key = self.fields["key"].clean(self.data.get("key"))
            except forms.ValidationError:
                pass
            else:
                # Historical exact retries remain valid after a package is disabled.
                products |= Q(purchase__owner=actor, purchase__key=key)
        self.fields["product"].queryset = PromotionProduct.objects.filter(products).distinct().order_by("pk")
        self.fields["product"].label_from_instance = lambda p: f"{p.name} · {p.amount} {p.currency} · {p.duration_seconds // 3600} saat (sentetik)"
        if not self.is_bound:
            self.initial["key"] = uuid.uuid4()