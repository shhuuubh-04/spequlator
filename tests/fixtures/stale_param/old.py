def fetch_users(session, timeout=30):
    response = session.get("/users", timeout=timeout)
    return [u for u in response.json() if u["active"]]
