import requests

BASE_URL = "http://localhost:8080"
TIMEOUT = 30

def test_getrootindexredirect():
    session = requests.Session()

    # Unauthenticated request to /
    resp = session.get(f"{BASE_URL}/", allow_redirects=False, timeout=TIMEOUT)
    assert resp.status_code in (302, 303, 307, 308) or resp.status_code == 200, f"Unexpected status code for unauthenticated root request: {resp.status_code}"
    if resp.status_code in (302, 303, 307, 308):
        location = resp.headers.get("Location", "")
        assert location, "Redirect response missing Location header"
        assert any(p in location for p in ["/login", "/google/login", "/auth", "/welcome"]), f"Unexpected redirect location for unauthenticated root: {location}"


test_getrootindexredirect()
