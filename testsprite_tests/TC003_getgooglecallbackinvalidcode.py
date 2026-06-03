import requests

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

def test_getgooglecallbackinvalidcode():
    invalid_code = "invalid_or_expired_code"
    params = {"code": invalid_code}
    try:
        response = requests.get(f"{BASE_URL}/google/callback", params=params, timeout=TIMEOUT, allow_redirects=False)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"
    
    # Expecting an error response indicating authentication failure (could be 400, 401, or a redirect to login)
    # Check status code for unauthorized or bad request or redirect to login
    assert response.status_code in (400, 401, 302), f"Unexpected status code: {response.status_code}"

    # If redirect, location should be to a login page or error page
    if response.status_code == 302:
        location = response.headers.get("Location", "")
        assert "/login" in location or "/google/login" in location, f"Unexpected redirect location: {location}"
    else:
        # If JSON or text response, verify presence of error message or authentication failure indication
        content = response.text.lower()
        assert ("error" in content or "unauthorized" in content or "invalid" in content or "failed" in content), \
            f"Expected authentication failure message not found in response content: {content}"

test_getgooglecallbackinvalidcode()