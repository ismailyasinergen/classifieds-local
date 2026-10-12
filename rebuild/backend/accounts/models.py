import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        if not isinstance(email, str):
            raise ValidationError({"email": "Geçerli bir e-posta adresi girin."})
        return email.strip().lower()

    def create_user(self, email, password=None, **extra_fields):
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields["is_staff"] is not True or extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Private account identity; email is never a public contact field."""
    username = None
    email = models.EmailField(unique=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
            models.CheckConstraint(condition=models.Q(email__regex=r"\S"), name="accounts_user_email_not_blank"),
        ]

    def clean(self):
        super().clean()
        self.email = User.objects.normalize_email(self.email)
        validate_email(self.email)

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class SecurityEvent(models.Model):
    """Append-only application audit; allauth success signals can be post-commit."""
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=32, choices=[
        ("activated", "Etkinleştirme"), ("used", "Başarılı doğrulama"),
        ("failed", "Başarısız doğrulama"), ("removed", "Cihaz kaldırma"),
        ("recovery_regenerated", "Kurtarma kodlarını yenileme"),
    ])
    method = models.CharField(max_length=32, choices=[
        ("totp", "Doğrulama uygulaması"), ("recovery_codes", "Kurtarma kodu"),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Güvenlik kaydı değiştirilemez.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Güvenlik kaydı silinemez.")


class Storefront(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(User, on_delete=models.PROTECT, related_name="storefront")
    draft_name = models.CharField(max_length=80)
    draft_intro = models.TextField(blank=True, max_length=2000)
    published_name = models.CharField(max_length=80, blank=True)
    published_intro = models.TextField(blank=True, max_length=2000)
    is_published = models.BooleanField(default=False)
    edit_version = models.PositiveBigIntegerField(default=1)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(edit_version__gte=1), name="storefront_version_positive"),
            models.CheckConstraint(condition=models.Q(draft_name__regex=r"\S"), name="storefront_draft_name_present"),
            models.CheckConstraint(condition=models.Q(is_published=False) | (
                models.Q(published_name__regex=r"\S") & models.Q(published_at__isnull=False)),
                name="storefront_public_snapshot_present"),
        ]
