"""
Esup-Pod - Tests for authentication views.

This module validates the different authentication flows provided by the API,
including standard JWT login, Shibboleth-based authentication, and OIDC flows.
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ..conf import AuthConfig
from ..models import Owner

User = get_user_model()


class LoginViewTests(APITestCase):
    """
    Test suite for standard JWT authentication (token obtain pair).
    """

    def setUp(self):
        """
        Initializes a test user and their associated owner profile.
        """
        self.username = "testuser"
        # ggignore-start
        # gitguardian:ignore
        self.password = "testpass123"  # nosec
        # ggignore-end
        self.user = User.objects.create_user(
            username=self.username, password=self.password
        )
        Owner.objects.get_or_create(user=self.user)
        self.url = reverse("token_obtain_pair")

    def test_login_success(self):
        """
        Tests that valid credentials return both access and refresh JWT tokens.
        """
        data = {"username": self.username, "password": self.password}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_failure(self):
        """
        Tests that invalid credentials result in an unauthorized response.
        """
        data = {"username": self.username, "password": "wrongpassword"}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ShibbolethLoginViewTests(APITestCase):
    """
    Test suite for Shibboleth-based single sign-on flows.
    """

    def setUp(self):
        """
        Sets up the URL for the Shibboleth token obtain pair endpoint.
        """
        self.url = reverse("token_obtain_pair_shibboleth")
        self.remote_user_header = "REMOTE_USER"

    def test_shibboleth_success(self):
        """
        Tests that providing the correct Shibboleth headers results in user creation (if needed)
        and a successful JWT token issuance.
        """
        headers = {
            "REMOTE_USER": "shibuser",
            "HTTP_SHIBBOLETH_MAIL": "shib@example.org",
            "HTTP_X_SHIBBOLETH_SECURE": "from-sp",
        }
        response = self.client.get(self.url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(username="shibuser").exists())

    def test_shibboleth_missing_header(self):
        """
        Tests that authentication fails when the REMOTE_USER header is missing.
        """
        headers = {
            "HTTP_X_SHIBBOLETH_SECURE": "from-sp",
        }
        response = self.client.get(self.url, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch(
        "src.apps.authentication.services.providers.shibboleth.auth_settings",
        new_callable=lambda: AuthConfig(
            remote_user_header="REMOTE_USER",
            shib_secure_header="HTTP_X_SECURE",
            shib_secure_value="secret",
        ),
    )
    def test_shibboleth_security_check_fail(self, mock_settings):
        """
        Tests that access is forbidden when optional security headers (like X-SECURE)
        do not match the expected values.
        """
        headers = {
            "HTTP_REMOTE_USER": "shibuser",
        }
        response = self.client.get(self.url, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OIDCLoginViewTests(APITestCase):
    """
    Test suite for OpenID Connect (OIDC) authentication flows.
    """

    def setUp(self):
        """
        Sets up the URL for the OIDC token exchange endpoint.
        """
        self.url = reverse("token_obtain_pair_oidc")

    @patch("requests.post")
    @patch("requests.get")
    @patch(
        "src.apps.authentication.services.providers.oidc.auth_settings",
        new_callable=lambda: AuthConfig(
            use_oidc=True,
        ),
    )
    def test_oidc_success(self, mock_settings, mock_get, mock_post):
        """
        Mocks the full OIDC flow:
        1. Trading an auth code for an access token via the provider's token endpoint.
        2. Fetching user info from the provider's userinfo endpoint.
        3. Issuing local JWTs for the identified user.
        """
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "fake_access_token"}
        mock_token_resp.status_code = 200
        mock_post.return_value = mock_token_resp

        mock_user_resp = MagicMock()
        mock_user_resp.json.return_value = {
            "preferred_username": "oidcuser",
            "email": "oidc@example.org",
            "given_name": "OIDC",
            "family_name": "User",
        }
        mock_user_resp.status_code = 200
        mock_get.return_value = mock_user_resp

        data = {"code": "auth_code", "redirect_uri": "http://localhost/callback"}
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(username="oidcuser").exists())


class OwnerPictureTests(APITestCase):
    """
    Test suite for managing an owner's profile picture.
    """

    def setUp(self):
        """
        Initializes a test user and an image for upload.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.user = User.objects.create_user(username="picuser", password="picpassword")
        self.owner, _ = Owner.objects.get_or_create(user=self.user)
        self.client.force_authenticate(user=self.user)

        # Build the URL by appending 'picture/' to the owner detail URL
        owner_detail_url = reverse("owner-detail", args=[self.owner.id])
        self.url = f"{owner_detail_url}picture/"

        self.image_content = b"fake_image_content"
        self.uploaded_pic = SimpleUploadedFile(
            "test_pic.jpg", self.image_content, content_type="image/jpeg"
        )

    def test_upload_and_delete_picture(self):
        """
        Tests that an authenticated user can upload a picture and then delete it.
        """
        # 1. Upload the picture
        response = self.client.patch(
            self.url, {"picture": self.uploaded_pic}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.owner.refresh_from_db()
        self.assertTrue(bool(self.owner.userpicture))

        # 2. Delete the picture
        delete_response = self.client.delete(self.url)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.owner.refresh_from_db()
        self.assertFalse(bool(self.owner.userpicture))


class QueryParameterJWTAuthenticationTests(APITestCase):
    """Test suite for QueryParameterJWTAuthentication."""

    def test_authenticate_with_query_parameter(self):
        """Test authentication via token in query parameter."""
        from src.apps.authentication.authentication import QueryParameterJWTAuthentication
        from rest_framework.test import APIRequestFactory
        from rest_framework_simplejwt.tokens import AccessToken

        user = User.objects.create_user(username="jwtuser", password="jwtpassword")
        token = str(AccessToken.for_user(user))

        from rest_framework.request import Request

        factory = APIRequestFactory()

        # Test 1: Header auth works (standard JWT)
        request_header = Request(factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}"))
        authenticator = QueryParameterJWTAuthentication()
        res = authenticator.authenticate(request_header)
        self.assertIsNotNone(res)
        self.assertEqual(res[0], user)

        # Test 2: Token in query params works
        request_query = Request(factory.get("/", {"token": token}))
        res_query = authenticator.authenticate(request_query)
        self.assertIsNotNone(res_query)
        self.assertEqual(res_query[0], user)

        # Test 3: Invalid token in query params returns None
        request_invalid = Request(factory.get("/", {"token": "invalid_token"}))
        res_invalid = authenticator.authenticate(request_invalid)
        self.assertIsNone(res_invalid)

        # Test 4: No token/headers returns None
        request_none = Request(factory.get("/"))
        res_none = authenticator.authenticate(request_none)
        self.assertIsNone(res_none)
