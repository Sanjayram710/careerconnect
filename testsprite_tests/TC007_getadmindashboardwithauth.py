import requests

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

def test_getadmindashboardwithauth():
    session = requests.Session()
    try:
        # Authenticate as admin using helper login route
        login_resp = session.get(f"{BASE_URL}/test/login-admin", timeout=TIMEOUT)
        assert login_resp.status_code == 200, f"Admin login failed with status {login_resp.status_code}"

        # Access the admin dashboard with authenticated session
        dashboard_resp = session.get(f"{BASE_URL}/admin/dashboard", timeout=TIMEOUT)
        assert dashboard_resp.status_code == 200, f"Expected 200 OK, got {dashboard_resp.status_code}"
        content_type = dashboard_resp.headers.get("Content-Type", "")
        assert "application/json" in content_type or "text/html" in content_type, "Unexpected content type"
        # Additional validate presence of expected dashboard content keyword
        assert any(keyword in dashboard_resp.text.lower() for keyword in ["admin dashboard", "placements", "students", "management"]), "Admin dashboard content not found"

    finally:
        # Logout or clear session to clean up if available
        try:
            session.get(f"{BASE_URL}/test/logout", timeout=TIMEOUT)
        except Exception:
            pass

test_getadmindashboardwithauth()