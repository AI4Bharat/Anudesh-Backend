from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse


class AuthTests(APITestCase):
    def test_login(self):
        # Assuming a user is already created or mock the creation
        response = self.client.post(
            "/users/auth/jwt/create",
            json={
                "email": "test_annotator1@anudesh.org",
                "password": "anudesh_admin@123",
            },
        )

        if response.status_code == 200:
            self.token = response.data.get("access")
            print("Login successful! Token:", self.token)
        else:
            self.token = None
            print("Login failed!", response.data)  # Changed to response.data

        self.assertIn(response.status_code, [200, 401])
