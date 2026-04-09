from typing import Any


def success_response(data: Any, message: str = "success", code: int = 0) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "data": data,
    }
