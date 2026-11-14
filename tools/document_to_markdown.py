from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError
from tools._run import answer, document_call, refuse


def _text_of(result: dict[str, Any]) -> str:
    for name in ("markdown", "text", "content"):
        value = result.get(name)
        if isinstance(value, str):
            return value
    return ""


class DocumentToMarkdownTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        output = "text" if str(tool_parameters.get("format") or "markdown").lower() == "text" else "markdown"
        params: dict[str, Any] = {"format": output}
        try:
            limit = int(tool_parameters.get("max_chars") or 0)
        except (TypeError, ValueError):
            limit = 0
        if limit:
            params["maxChars"] = max(1000, min(200000, limit))
        try:
            result = document_call(self, "/document/text", params, tool_parameters)
        except ApiError as e:
            raise refuse(e) from e
        yield from answer(self, result, _text_of(result))
