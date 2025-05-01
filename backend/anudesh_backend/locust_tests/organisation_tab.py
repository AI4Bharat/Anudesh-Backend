class OrganisationAPIs:
    def __init__(self, client, token):
        self.client = client
        self.token = token

    def get_workspace(self):
        """
        Simulates a GET request to the /workspaces/ endpoint to fetch workspace details.
        """
        self.client.get(
            "/workspaces",
            headers={"Authorization": f"JWT {self.token}"},
        )

    def get_members(self):
        """
        Simulates a GET request to the /organizations/1/users/ endpoint to fetch members
        """
        self.client.get(
            "/organizations/1/users/", headers={"Authorization": f"JWT {self.token}"}
        )

    def get_invites(self):
        """
        Simulates a GET request to the /users/invite/pending_users/?organisation_id=1 endpoint to fetch invites
        """
        self.client.get(
            "/users/invite/pending_users/?organisation_id=1",
            headers={"Authorization": f"JWT {self.token}"},
        )

    def put_organisation_settings(self):
        """
        Simulates a PUT request to the /organizations/1/ endpoint to update organisation
        """
        self.client.put(
            "/organizations/1",
            data={"title": "Anudesh Locust Test"},
            headers={"Authorization": f"JWT {self.token}"},
        )
