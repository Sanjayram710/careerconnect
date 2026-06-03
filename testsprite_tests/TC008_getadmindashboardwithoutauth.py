import requests

def test_getadmindashboardwithoutauth():
    base_url = "http://localhost:8080"
    url = f"{base_url}/admin/dashboard"
    try:
        response = requests.get(url, timeout=30, allow_redirects=False)
        # Expect either 401 Unauthorized or a redirect to auth flow (3xx)
        assert response.status_code in (401, 302, 303, 307, 308), \
            f"Expected HTTP 401 or redirect, got {response.status_code}"
        # If redirect, location header should be present and point to login or auth
        if response.status_code in (302, 303, 307, 308):
            location = response.headers.get("Location", "")
            assert location, "Redirect response missing Location header"
            assert any(keyword in location.lower() for keyword in ["login", "auth"]), \
                f"Redirect Location header does not indicate authentication flow: {location}"
    except requests.RequestException as e:
        assert False, f"Request to /admin/dashboard failed: {e}"

test_getadmindashboardwithoutauth()