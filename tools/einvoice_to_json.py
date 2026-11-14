from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError
from tools._run import answer, einvoice_call, refuse


class EinvoiceToJsonTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            result = einvoice_call(self, "/einvoice/to-json", {}, tool_parameters)
        except ApiError as e:
            raise refuse(e) from e
        yield from answer(self, result)
