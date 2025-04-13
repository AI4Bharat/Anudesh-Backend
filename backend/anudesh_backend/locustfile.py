from locust import HttpUser, task, between


# This class defines the behavior of a simulated user in your test
class UserBehavior(HttpUser):
    # Each user waits between 1 to 5 seconds between two consecutive tasks
    wait_time = between(1, 5)

    # Base URL of the backend server (change if testing on staging or production)
    host = "http://localhost:8000"

    def on_start(self):
        """
        This runs when a simulated user starts.
        We log in here and store the JWT token for future requests.
        """
        response = self.client.post(
            "/users/auth/jwt/create",
            json={
                "email": "test_annotator1@anudesh.org",
                "password": "anudesh_admin@123",
            },
        )

        if response.status_code == 200:
            self.token = response.json().get("access")
            print("Login successful! Token:", self.token)
        else:
            self.token = None
            print("Login failed!", response.text)

    @task
    def fetch_account_details(self):
        """
        Simulates a Get request to the /users/account/me/fetch/ endpoint, typically used to get user details.
        """
        self.client.get(
            "/users/account/me/fetch/",
            headers={"Authorization": f"JWT {self.token}"},
        )


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
