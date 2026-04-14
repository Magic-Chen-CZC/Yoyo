from enum import Enum as PythonEnum

from sqlalchemy import Enum


def db_enum(enum_cls: type[PythonEnum], *, name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )
