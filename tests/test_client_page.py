def test_client_page_is_served_at_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Дневник смен" in response.text
