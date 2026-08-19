from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from src.apps.authentication.authentication import QueryParameterJWTAuthentication

User = get_user_model()

class CustomAuthenticationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(username="testauth", password="password")
        self.token = AccessToken.for_user(self.user)
        self.auth = QueryParameterJWTAuthentication()

    def _get_drf_request(self, url):
        django_request = self.factory.get(url)
        return Request(django_request)

    def test_authenticate_with_query_param(self):
        request = self._get_drf_request(f"/?token={self.token}")
        result = self.auth.authenticate(request)
        self.assertIsNotNone(result)
        user, validated_token = result
        self.assertEqual(user, self.user)

    def test_authenticate_invalid_token(self):
        request = self._get_drf_request("/?token=invalid")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    def test_authenticate_no_token(self):
        request = self._get_drf_request("/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)
