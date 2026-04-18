from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator


class CreateItineraryRequest(BaseModel):
    user_id: str | None = None
    city_code: str = "beijing"
    title: str | None = None
    questionnaire_submission_id: str | None = None
    entry_type: Literal["template", "manual_poi", "ai_recommendation_selected", "starter_default"] = "starter_default"
    template_id: str | None = None
    selected_poi_ids: list[str] = Field(default_factory=list)
    preferences: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_entry_requirements(self) -> Self:
        if self.entry_type == "template" and self.template_id is None:
            raise ValueError("template_id is required for template entry")
        if self.entry_type == "manual_poi" and not self.selected_poi_ids:
            raise ValueError("selected_poi_ids is required for manual_poi entry")
        return self


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
    operation: Literal["replace_stop", "remove_stop", "reorder_stops", "shorten_route", "add_stop", "optimize_route"]
    target_stop_id: str | None = None
    target_stop_name: str | None = None
    replacement_stop_id: str | None = None
    replacement_stop_name: str | None = None
    add_stop_id: str | None = None
    add_stop_name: str | None = None
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

        if self.operation == "add_stop":
            if self.add_stop_id is None and self.add_stop_name is None:
                raise ValueError("add stop is required")

        if self.operation == "reorder_stops" and not self.ordered_stop_ids:
            raise ValueError("ordered_stop_ids is required")

        if self.operation == "shorten_route" and self.target_stop_count is None:
            raise ValueError("target_stop_count is required")

        provided_fields = {
            "target_stop_id": self.target_stop_id is not None,
            "target_stop_name": self.target_stop_name is not None,
            "replacement_stop_id": self.replacement_stop_id is not None,
            "replacement_stop_name": self.replacement_stop_name is not None,
            "add_stop_id": self.add_stop_id is not None,
            "add_stop_name": self.add_stop_name is not None,
            "ordered_stop_ids": bool(self.ordered_stop_ids),
            "target_stop_count": self.target_stop_count is not None,
        }
        allowed_fields = {
            "replace_stop": {
                "target_stop_id",
                "target_stop_name",
                "replacement_stop_id",
                "replacement_stop_name",
            },
            "remove_stop": {"target_stop_id", "target_stop_name"},
            "reorder_stops": {"ordered_stop_ids"},
            "shorten_route": {"target_stop_count"},
            "add_stop": {"add_stop_id", "add_stop_name"},
            "optimize_route": set(),
        }
        unexpected_fields = [
            field_name
            for field_name, is_provided in provided_fields.items()
            if is_provided and field_name not in allowed_fields[self.operation]
        ]
        if unexpected_fields:
            raise ValueError(
                f"{', '.join(unexpected_fields)} not allowed for {self.operation}"
            )

        return self
