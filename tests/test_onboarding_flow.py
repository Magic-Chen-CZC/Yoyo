import pytest
from httpx import AsyncClient
from sqlalchemy import select

from yoyo.db.models.guest import GuestUser
from yoyo.db.models.profile import UserProfile


@pytest.mark.asyncio
async def test_guest_session_and_questionnaire_flow_persist_profile(
    client: AsyncClient, db_session
) -> None:
    guest_response = await client.post("/api/v1/guest/sessions")
    assert guest_response.status_code == 201
    guest_data = guest_response.json()["data"]
    assert guest_data["status"] == "active"
    assert guest_data["guest_user_id"]
    assert guest_data["anonymous_token"]

    guest_user = await db_session.get(GuestUser, guest_data["guest_user_id"])
    assert guest_user is not None

    flow_response = await client.get("/api/v1/questionnaire/flows/current")
    assert flow_response.status_code == 200
    flow_data = flow_response.json()["data"]
    assert flow_data["version"] == "v1"
    assert flow_data["question_count"] == 7

    submission_response = await client.post(
        "/api/v1/questionnaire/submissions",
        json={
            "user_id": guest_data["guest_user_id"],
            "role_choice": "history_scholar",
            "answers": {
                "preferred_language": "en",
                "interests": ["history", "architecture"],
                "travel_style": "focused",
                "walking_preference": "moderate",
                "audience_type": "solo",
                "answer_length_preference": "long",
            },
        },
    )
    assert submission_response.status_code == 201
    submission_data = submission_response.json()["data"]
    assert submission_data["payload"]["flow_version"] == "v1"
    assert submission_data["payload"]["role_choice"] == "history_scholar"
    assert submission_data["payload"]["answers"]["guide_role"] == "history_scholar"

    profile = await db_session.get(UserProfile, guest_data["guest_user_id"])
    assert profile is not None
    assert profile.guide_style_preference == "NT"
    assert profile.travel_style == "focused"
    assert profile.audience_type == "solo"
    assert profile.profile_source == "questionnaire_flow"
    assert profile.profile_version == "v1"


@pytest.mark.asyncio
async def test_questionnaire_rejects_missing_answers(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/questionnaire/submissions",
        json={
            "user_id": "guest-x",
            "role_choice": "balanced_storyteller",
            "answers": {
                "preferred_language": "en",
                "interests": ["history"],
            },
        },
    )
    assert response.status_code == 422
