import requests

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

def test_getstudentdashboardwithoutauth():
    url = f"{BASE_URL}/student/dashboard"
    try:
        response = requests.get(url, timeout=TIMEOUT, allow_redirects=False)
    except requests.RequestException as e:
        assert False, f"Request to {url} failed with exception: {e}"

    # Accept either 401 Unauthorized or a redirect (3xx) to auth flow
    assert response.status_code in (401, 302, 303, 307, 308), (
        f"Expected status code 401 or redirect to auth, got {response.status_code}"
    )
    # If redirect, verify Location header includes typical login/auth path hints
    if response.status_code in (302, 303, 307, 308):
        location = response.headers.get("Location", "")
        assert any(s in location for s in ["/google/login", "/login", "/auth", "/student/login"]), (
            f"Redirect Location header does not indicate authentication flow: {location}"
        )

test_getstudentdashboardwithoutauth()