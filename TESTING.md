# Backend API Testing Document

_~ Dhaval J Prasad (software engineer intern)_

This document outlines the testing strategy, setup, and execution guidelines for backend API testing using. It covers end-to-end testing of the api endpoints for the web applications like Anudesh, Shoonya and Chitralekha. This document is for developers, QA engineers and product managers.

## Technology Used

Python Programming

## Test Environment Setup

1. You don't need to setup anything as environment for this, everything comes with base DJANGO REST package

2. You might need env. values, which are missing, and they are as follows:

   - FLOWER_ADDRESS="flower"
   - FLOWER_PORT="5555"
   - FLOWER_USERNAME="anudesh"
   - FLOWER_PASSWORD="flower123"
   - FRONTEND_URL=''
   - CELERY_BROKER_URL="redis://redis:6379/0"
   - REDIS_HOST="redis"
   - REDIS_PORT="6379"
   - DEFAULT_CELERY_LOCK_TIMEOUT="60"

3. Not adding will only give warning, there's no error because of this

## Writing Tests & Executing them

1. Create a `<tests>` folder inside `<backend/<backend_name>>`

2. Initiate python scripts by adding the file `__init__.py`

3. Create a file for certain-type of tests, like test_auth.py. Make sure the name starts with test, as it will be used by cmd to know that they need to run the test written in this file

4. Once done, run the cmd: `docker-compose -f docker-compose-dev.yml exec web python manage.py test --noinput`

5. This will print the output of test-results in your terminal

## Examples

![Test Auth Example](<**![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXfFDJfUUCFmLdFZQxNNrABIlHyFM19BugUl7T9Qj8trponlDkUGG5fmWPYQ5sqRJ7dW0t2U1UDuov6_r2RHJAf7Z1bu1Q1OR3U5iJwDnerbciK2-cr49yE4oLBScXhEMBHCFoQbgg?key=1bAbMCqj5IwHyeeFiA_zqe7r)**>)

This is an example of test_auth.py file

For more information and examples, visit: https://docs.djangoproject.com/en/5.1/topics/testing/overview/

---

# Backend Stress-Testing Document

_~ Dhaval J Prasad (software engineer intern)_

This document outlines the testing strategy, setup, and execution guidelines for backend stress-testing using Locust. It covers end-to-end load testing of the api endpoints for the web applications like Anudesh, Shoonya and Chitralekha. This document is for developers, QA engineers and product managers.

## Technology Used

Python Programming

## Test Environment Setup

1. Navigate to the root directory of the Project and boot up the virtual environment, using terminal command: **WIN:** `.\venv\Scripts\activate` | **MAC:** `source venv/bin/activate`

2. Install locust by using the terminal command: `pip install locust`

3. To verify the installation, run terminal command: `locust --version`, this will print out the version of locust installed in the project.

4. If you see something like, "locust 2.x.x" for version of locust, you've successfully installed the locust

## Test Structure & Organization

- **File Structure:** In the root folder, navigate to "backend/<proejct_name>". For example: backend/anudesh_backend

- **Test Naming Convention:** Create a file named locustfile.py in the navigated directory in the above step. This file will act as default entry point for Locust

## Writing & Maintaining Tests

1. Use clear and descriptive test names.

2. Avoid hardcoded values.

3. Use assertions effectively.

4. Keep tests isolated.

## Examples

Here is an example on how locustfile.py file looks along with code comments:

![Locustfile Example](<**![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXdoGzHB7PJThtEWmUqJsXC8hcKvPVeneI4Y_btNF0dsj2y7wKcqscplyjBHxbmNoS0uZsG8ni6zElgLLCWCjH-RkEQ7KGo8qxojYQdVzyaWSxGtHylq083HNxmuc_z8bSra8eVq-A?key=9K5k0aXUON09JnEgaWCVRZg1)**>)

(This is how you should write code in basic locustfile.py)

-> always write the login function in order to get bearer token to make other API calls

## Running Tests

### Using the Web Interface

1. Once you're done writing tests for stress-testing different API endpoints. Navigate your terminal to the directory where you've defined your Locustfile.py

2. Run terminal command: `locust -f locustfile.py --host=http://localhost:8000` to start stress-testing

3. After running this, open URL: http://localhost:8089/ in your local browser, and you can define concurrent users and total users to start stress-testing

After navigating to http://localhost:8089/, you'll get a UI something like:

![Locust UI]()**![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXf7BCcZgWcyLAdfd7_Q1pYWensXAUBWK-GJZ5IOlRPXIfmYgHwc-YwSgcr4RNSmAkNBethXzUondBHqILOgR6Ie1AvknjaZMLtmfU_w8kn2TkXm2yvceQqrAENHfrbNYRgxYiMnpg?key=9K5k0aXUON09JnEgaWCVRZg1)**

Define both the params as per your requirements, and hit START

![Locust Charts](<**![](https://lh7-rt.googleusercontent.com/docsz/AD_4nXc8KNZrSXseou5fzVvKF9JFKaVbHWjdiJMrWqTUr1bO6LS-0IUGyciBDiNHnSfiwMGQoL5FYJikR5DHi-I-f_XTULDPmiN4qZpPZUjnwXcDQJAmie8ciKrJvPkF5dYwfncljAYKqw?key=9K5k0aXUON09JnEgaWCVRZg1)**>)

Once you run the test, you'll see charts like these to get better benchmark data

### Running Headless (Terminal-Only Mode)

Locust can also be run entirely from the command line without using the web interface. This is useful for:

- CI/CD pipelines
- Automated testing
- Server environments without a browser
- Predefined test scenarios

To run Locust in headless mode, use the following command structure:

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 5m
```

Command-line parameters:

- `-f locustfile.py`: Specify the locust file to use
- `--host=http://localhost:8000`: Specify the host to load test
- `--headless`: Run in headless mode (no web UI)
- `-u 100` or `--users=100`: Number of concurrent users to simulate
- `-r 10` or `--spawn-rate=10`: Rate at which users are spawned (users per second)
- `-t 5m` or `--run-time=5m`: How long the test should run (e.g., 5m for 5 minutes, 30s for 30 seconds)

Additional useful options:

- `--csv=results`: Save results to CSV files with the prefix "results"
- `--only-summary`: Only print the summary statistics
- `--stop-timeout=10`: Stop the test after 10 seconds of inactivity
- `--expect-workers=4`: Expect 4 worker processes to connect before starting

Example for a quick 30-second test with 50 users:

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 50 -r 10 -t 30s --csv=quick_test
```

Example for a detailed distributed load test:

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 1000 -r 20 -t 10m --csv=stress_test --expect-workers=4
```

## Analyzing Results

When running in headless mode with the `--csv` option, Locust will generate multiple CSV files:

- `results_stats.csv`: Contains request statistics
- `results_failures.csv`: Contains data about failed requests
- `results_stats_history.csv`: Contains the timeline of request statistics
- `results_exceptions.csv`: Contains data about exceptions that occurred

These files can be imported into data analysis tools or spreadsheets for further analysis and visualization.
