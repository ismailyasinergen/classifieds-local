from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """
    Allows login with either username or email.

    This fixes local demo login confusion where test users may use email-style
    usernames, while Django's default AuthenticationForm labels the field as
    username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        login_value = username or kwargs.get("username")
        if not login_value or not password:
            return None

        UserModel = get_user_model()

        user = None

        try:
            user = UserModel.objects.get(username__iexact=login_value)
        except UserModel.DoesNotExist:
            try:
                user = UserModel.objects.get(email__iexact=login_value)
            except UserModel.DoesNotExist:
                return None
            except UserModel.MultipleObjectsReturned:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
