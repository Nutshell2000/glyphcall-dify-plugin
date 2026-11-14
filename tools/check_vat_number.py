from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError, call
from tools._run import answer, refuse


class CheckVatNumberTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        vat = "".join(str(tool_parameters.get("vat_number") or "").split()).upper()
        try:
            if not vat:
                raise ApiError("Give a VAT number with its two-letter country prefix, for example SE556703748501")
            result = call(self.runtime.credentials.get("api_key", ""), "/vat/validate", {"vat": vat})
        except ApiError as e:
            raise refuse(e) from e
        yield from answer(self, result)
