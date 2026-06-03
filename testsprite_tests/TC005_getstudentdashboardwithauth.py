import requests

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

def test_TC005_getstudentdashboardwithoutauth():
    # Access student dashboard without authentication
    resp = requests.get(f"{BASE_URL}/student/dashboard", timeout=TIMEOUT)
    assert resp.status_code == 401 or resp.status_code == 302, f"Expected 401 unauthorized or redirect but got {resp.status_code}"

test_TC005_getstudentdashboardwithoutauth()