import requests

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

def test_getgoogleloginredirect():
    try:
        response = requests.get(f"{BASE_URL}/google/login", allow_redirects=False, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to /google/login failed: {e}"

    assert response.status_code in (301, 302, 303, 307, 308), \
        f"Expected redirect status code from /google/login, got {response.status_code}"
    location = response.headers.get("Location", "")
    assert location.startswith("https://accounts.google.com/") or "accounts.google.com" in location, \
        f"Expected redirect to Google OAuth consent flow URL, got Location header: {location}"

test_getgoogleloginredirect()