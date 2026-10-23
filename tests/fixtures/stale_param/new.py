def fetch_users(session, retries=3):
    for _ in range(retries):
        response = session.get("/users")
        if response.ok:
            return [u for u in response.json() if u["active"]]
    return []
