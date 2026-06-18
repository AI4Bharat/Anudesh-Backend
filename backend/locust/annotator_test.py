from locust import HttpUser, task, between

class AnudeshUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        # ---- LOGIN ----
        login_payload = {
            "email": "test_annotator1@anudesh.org",
            "password": "anudesh-admin@123"
        }

        headers = {"Content-Type": "application/json"}

        with self.client.post(
            "/users/auth/jwt/create",
            json=login_payload,
            headers=headers,
            catch_response=True
        ) as response:

            if response.status_code == 200:
                self.token = response.json().get("access")

                # Save auth headers for later tasks
                self.auth_headers = {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                }
                print("Login successful:", self.auth_headers)

                response.success()
            else:
                self.auth_headers = None  # Prevent crash
                response.failure("Login failed")

    @task
    def full_user_flow(self):
        # ---- SAFETY CHECK TO PREVENT CRASH ----
        if not self.auth_headers:
            return  # Skip task if login failed

        project_id = 4267
        workspace_id = 69
        pull_count = 10

        # -------------------------
        # STEP 1: Get all projects
        # -------------------------
        with self.client.get(
            "/projects/projects_list/optimized/",
            headers=self.auth_headers,
            catch_response=True
        ) as response:

            if response.status_code == 200:
                response.success()
            else:
                response.failure("Failed to fetch projects")
                return

        # --------------------------------
        # STEP 2: Get specific project info
        # --------------------------------
        self.client.get(
            f"/projects/{project_id}/",
            headers=self.auth_headers
        )

        # -----------------------------------------------
        # STEP 3: Get task list (unlabeled tasks)
        # -----------------------------------------------
        task_url = (
            f"/task/?project_id={project_id}"
            f"&page=1"
            f"&records=100"
            f"&annotation_status=[%22unlabeled%22]"
        )

        with self.client.get(
            task_url,
            headers=self.auth_headers,
            catch_response=True
        ) as task_res:

            if task_res.status_code == 200:
                try:
                    task_data = task_res.json()
                    initial_count = task_data.get("count", 0)
                except Exception:
                    task_res.failure("Invalid JSON in task list response")
                    return

                task_res.success()

            else:
                task_res.failure("Failed to fetch initial task list")
                return

        # Step 4: Get workspace members
        self.client.get(f"/workspaces/{workspace_id}/members/", headers=self.auth_headers)

        # Step 5: Pull new tasks
        pull_payload = {"num_tasks": pull_count}
        with self.client.post(f"/projects/{project_id}/assign_new_tasks/", json=pull_payload, headers=self.auth_headers, catch_response=True) as pull_res:
            if pull_res.status_code == 200:
                pull_res.success()
            else:
                pull_res.failure("Failed to assign new tasks")
                return

        # Optional delay to allow backend to update
        time.sleep(2)

        # Step 6: Check new task count
        with self.client.get(task_url, headers=self.auth_headers, catch_response=True) as final_res:
            if final_res.status_code == 200:
                new_count = final_res.json().get("count", 0)
                added = new_count - initial_count
                # Step 3: initial_count from Get task list (unlabeled tasks)
                if added == pull_count:
                    final_res.success()
                    print(f"✅ Successfully pulled {added} new tasks.")
                else:
                    final_res.failure(f"❌ Expected {pull_count} new tasks, got {added}.")
            else:
                final_res.failure("Failed to fetch updated task list")