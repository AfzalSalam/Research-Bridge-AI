from uuid import uuid4

from tests.test_mentor_discovery import mentor_client  # noqa: F401


def test_saved_research_exact_selection_and_owner_isolation(mentor_client):  # noqa: F811
    client = mentor_client
    response = client.post(
        "/api/v1/discovery/papers", json={"query": "machine learning", "limit": 30}
    )
    assert response.status_code == 200
    paper = response.json()["papers"][0]
    author = paper["authors"][0]
    endpoint = f"/api/v1/research/papers/{paper['id']}"
    retrieved = client.get(endpoint)
    assert retrieved.status_code == 200
    assert retrieved.json()["lastVerifiedAt"].endswith("Z")
    saved = client.put(
        endpoint,
        json={
            "note": "Read the evaluation carefully",
            "collection": "Reading",
            "authorIds": [author["id"]],
        },
    )
    assert saved.status_code == 200
    assert (
        client.put(endpoint, json={}).json()["note"] == "Read the evaluation carefully"
    )
    assert len(client.get("/api/v1/research/papers").json()) == 1
    selected = client.get(f"{endpoint}/authors/{author['id']}")
    assert selected.status_code == 200
    assert selected.json()["supportingPapers"][0]["id"] == paper["id"]
    assert client.get(f"{endpoint}/authors/{uuid4()}").status_code == 422
    draft = client.post(
        "/api/v1/outreach/drafts",
        json={
            "query": "unrelated query does not trigger another search",
            "mentorId": author["id"],
            "paperIds": [paper["id"]],
            "generationPreference": "deterministic",
        },
    )
    assert draft.status_code == 201, draft.text
    draft_id = draft.json()["id"]
    contact = f"/api/v1/research/drafts/{draft_id}/recipient"
    assert (
        client.put(
            contact, json={"email": "prof@example.edu", "expectedVersion": 1}
        ).status_code
        == 422
    )
    assert (
        client.put(
            contact,
            json={
                "email": "prof@example.edu",
                "expectedVersion": 1,
                "manuallyConfirmed": True,
            },
        ).status_code
        == 204
    )
    assert (
        client.get(f"/api/v1/outreach/drafts/{draft_id}").json()["recipientContact"]
        == "prof@example.edu"
    )
    assert (
        client.put(
            contact,
            json={
                "email": "prof@example.edu",
                "expectedVersion": 1,
                "manuallyConfirmed": True,
            },
        ).status_code
        == 409
    )
    client.headers.update({"Authorization": "Bearer mentor-user-b"})
    assert client.get("/api/v1/research/papers").json() == []
    assert client.get("/api/v1/research/drafts").json() == []
    assert (
        client.put(
            contact,
            json={
                "email": "prof@example.edu",
                "expectedVersion": 2,
                "manuallyConfirmed": True,
            },
        ).status_code
        == 404
    )
