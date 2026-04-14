# 这个文件负责把问答需要的上下文打包在一起。
# 你可以把它理解成：把“用户问题 + 语言 + 请求上下文 + 会话上下文”装进一个盒子里。
from typing import Any


def build_context(
    query: str,
    language: str,
    request_context: dict[str, Any],
    session_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "query": query,
        "language": language,
        "request_context": request_context,
        "session_context": session_context or {},
    }
