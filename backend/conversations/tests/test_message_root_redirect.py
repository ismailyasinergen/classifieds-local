from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class MessageRootRedirectTests(TestCase):
    password = "Testpass12345"

    def setUp(self):
        User = get_user_model()
        username_field = User.USERNAME_FIELD

        kwargs = {username_field: "message-root-buyer@classifieds.local"}
        if username_field != "email" and any(field.name == "email" for field in User._meta.fields):
            kwargs["email"] = "message-root-buyer@classifieds.local"

        self.user = User.objects.create_user(password=self.password, **kwargs)
        self.client = Client(HTTP_HOST="localhost")

    def test_messages_root_redirects_to_inbox_for_anonymous_user(self):
        response = self.client.get("/messages/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("conversations:inbox"))

    def test_messages_root_redirects_to_inbox_for_logged_in_user(self):
        self.client.force_login(self.user)

        response = self.client.get("/messages/")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("conversations:inbox"))

    def test_inbox_route_still_requires_login(self):
        response = self.client.get(reverse("conversations:inbox"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_logged_in_user_can_open_inbox(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("conversations:inbox"))

        self.assertEqual(response.status_code, 200)
