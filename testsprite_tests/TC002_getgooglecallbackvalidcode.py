import requests

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

def test_getgooglecallbackvalidcode():
    session = requests.Session()
    try:
        # Step 1: Simulate student login to obtain a valid auth code via /test/login-student
        login_resp = session.get(f"{BASE_URL}/test/login-student", timeout=TIMEOUT)
        login_resp.raise_for_status()
        auth_code = login_resp.json().get("auth_code")
        assert auth_code, "No auth_code returned from /test/login-student"
        
        # Step 2: Use the valid authorization code to call /google/callback
        callback_resp = session.get(f"{BASE_URL}/google/callback", params={"code": auth_code}, allow_redirects=False, timeout=TIMEOUT)
        assert callback_resp.status_code in (302, 303), f"Expected redirect status code, got {callback_resp.status_code}"
        location = callback_resp.headers.get("Location")
        assert location == "/", f"Expected redirect location '/', got {location}"
        
        # Step 3: Follow redirect to root / to verify authenticated session established
        session.get(f"{BASE_URL}/google/callback", params={"code": auth_code}, timeout=TIMEOUT)  # establish cookie/session
        root_resp = session.get(f"{BASE_URL}/", allow_redirects=False, timeout=TIMEOUT)
        # The root / endpoint should redirect student to their portal or dashboard
        assert root_resp.status_code in (302, 303), f"Root / did not redirect, got status {root_resp.status_code}"
        assert root_resp.headers.get("Location") in ("/student/dashboard", "/admin/dashboard", "/"), "Unexpected root redirect location"
    finally:
        # Cleanup not needed as this test does not create persistent resources beyond session cookies
        session.close()

test_getgooglecallbackvalidcode()