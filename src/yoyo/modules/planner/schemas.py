from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator


class CreateItineraryRequest(BaseModel):
    user_id: str | None = None
    city_code: str = "beijing"
    title: str | None = None
    questionnaire_submission_id: str | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)


class ItineraryVersionRead(BaseModel):
    id: str
    version_no: int
    status: str
    planner_input: dict[str, Any]
    plan: dict[str, Any]


class ItineraryRead(BaseModel):
    id: str
    user_id: str | None
    city_code: str
    title: str | None
    status: str
    current_version_id: str | None
    version: ItineraryVersionRead


class RouteEditRequest(BaseModel):
    operation: Literal["replace_stop", "remove_stop", "reorder_stops", "shorten_route"]
    target_stop_id: str | None = None
    target_stop_name: str | None = None
    replacement_stop_id: str | None = None
    replacement_stop_name: str | None = None
    ordered_stop_ids: list[str] = Field(default_factory=list)
    target_stop_count: int | None = None
    created_by: str = "planner_edit_api"

    @model_validator(mode="after")
    def validate_operation_fields(self) -> Self:
        if self.operation in {"replace_stop", "remove_stop"}:
            if self.target_stop_id is None and self.target_stop_name is None:
                raise ValueError("target stop is required")

        if self.operation == "replace_stop":
            if self.replacement_stop_id is None and self.replacement_stop_name is None:
                raise ValueError("replacement stop is required")

        if self.operation == "reorder_stops" and not self.ordered_stop_ids:
            raise ValueError("ordered_stop_ids is required")

        if self.operation == "shorten_route" and self.target_stop_count is None:
            raise ValueError("target_stop_count is required")

        return self
