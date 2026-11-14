import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError, call
from tools._run import INVOICE_FIELDS, answer, clean_fields, document_call, refuse


class ExtractInvoiceTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        fields = INVOICE_FIELDS
        extra = clean_fields(tool_parameters.get("extra_fields"))
        if extra:
            fields = f"{fields},{extra}"
        try:
            result = document_call(self, "/document/extract", {"fields": fields}, tool_parameters)
            data = result.get("data") if isinstance(result.get("data"), dict) else {}
            invoice: dict[str, Any] = {
                "invoice": data,
                "missing": result.get("missing", []),
                "file_type": result.get("type"),
                "truncated": bool(result.get("truncated")),
            }
            if tool_parameters.get("check_vat"):
                invoice["supplier_vat_check"] = self._vat_check(data.get("supplier_vat_number"))
        except ApiError as e:
            raise refuse(e) from e
        yield from answer(self, invoice)

    def _vat_check(self, number: Any) -> dict[str, Any]:
        """A second, separately priced call. A failed check is reported, never raised: the invoice was read."""
        # Invoices print the number with spaces, dots and a trailing label ("NL810433941B01BTW").
        vat = re.sub(r"(BTW|VAT|TVA|MWST|UST|IVA)$", "", re.sub(r"[^A-Z0-9]", "", str(number or "").upper()))
        if not vat:
            return {"checked": False, "reason": "the invoice states no supplier VAT number"}
        try:
            checked = call(self.runtime.credentials.get("api_key", ""), "/vat/validate", {"vat": vat})
        except ApiError as e:
            return {"checked": False, "vat": vat, "reason": str(e)}
        return {"checked": True, **checked}
