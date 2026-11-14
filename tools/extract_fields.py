from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError
from tools._run import answer, clean_fields, document_call, refuse


class ExtractFieldsTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        fields = clean_fields(tool_parameters.get("fields"))
        try:
            if not fields:
                raise ApiError("Name at least one field to extract, for example: contract_date, parties, notice_period")
            result = document_call(self, "/document/extract", {"fields": fields}, tool_parameters)
        except ApiError as e:
            raise refuse(e) from e
        yield from answer(self, {
            "data": result.get("data", {}),
            "missing": result.get("missing", []),
            "file_type": result.get("type"),
            "truncated": bool(result.get("truncated")),
        })
