import os
from locust import HttpUser, task, between
from locust_tests.organisation_tab import OrganisationAPIs


class UserBehavior(HttpUser):
    wait_time = between(1, 5)
    host = os.environ.get("API_URL", "http://localhost:8000")

    def on_start(self):
        print(os.environ.get("TEST_EMAIL", ""), "Email")
        print(os.environ.get("TEST_EMAIL_PASSWORD", ""), "Password")
        response = self.client.post(
            "/users/auth/jwt/create",
            json={
                "email": os.environ.get("TEST_EMAIL", ""),
                "password": os.environ.get("TEST_EMAIL_PASSWORD", ""),
            },
        )
        if response.status_code == 200:
            self.token = response.json().get("access")
            self.organisation_apis = OrganisationAPIs(
                self.client, self.token
            )  # ✅ instance
        else:
            self.token = None

    @task
    def fetch_account_details(self):
        self.client.get(
            "/users/account/me/fetch/",
            headers={"Authorization": f"JWT {self.token}"},
        )

    @task
    def get_workspace_task(self):
        self.organisation_apis.get_workspace()

    @task
    def get_members_task(self):
        self.organisation_apis.get_members()

    @task
    def get_invite_task(self):
        self.organisation_apis.get_invites()

    @task
    def get_organisation_settings(self):
        self.organisation_apis.put_organisation_settings()


# @task
# def get_profile(self):
#     """
#     Simulates a GET request to fetch the user's profile.
#     Assumes the user is authenticated, which may require session handling or token headers.
#     """
#     self.client.get("/user/profile/")

# @task
# def fetch_reports(self):
#     """
#     Simulates a GET request to fetch reports.
#     Useful for testing how the system performs under high report-fetching load.
#     """
#     self.client.get("/reports/")
