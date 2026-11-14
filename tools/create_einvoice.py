import json
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError, post_json
from tools._run import refuse

FORMATS = ("xrechnung", "xrechnung-ubl", "zugferd", "ubl")

# The names extract_invoice returns, mapped to the names the e-invoice writer reads.
SUPPLIER_TO_SELLER = {
    "supplier_name": "seller_name",
    "supplier_vat_number": "seller_vat_number",
    "supplier_address": "seller_address",
    "customer_name": "buyer_name",
    "customer_vat_number": "buyer_vat_number",
    "subtotal": "net_amount",
    "tax_amount": "vat_amount",
    "total": "total_amount",
}


def invoice_object(raw: Any) -> dict[str, Any]:
    """The invoice as a dict, from a dict, a JSON string, or the whole answer of extract_invoice."""
    value = raw
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text[4:] if text.lower().startswith("json") else text
        try:
            value = json.loads(text)
        except ValueError as e:
            raise ApiError("The invoice is not valid JSON. Give an object with number, issueDate, seller, buyer and lines.") from e
    if not isinstance(value, dict):
        raise ApiError("The invoice must be a JSON object with number, issueDate, seller, buyer and lines.")
    if isinstance(value.get("invoice"), dict) and "lines" not in value and "number" not in value:
        value = value["invoice"]
    return {SUPPLIER_TO_SELLER.get(k, k): v for k, v in value.items()}


class CreateEinvoiceTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        chosen = str(tool_parameters.get("format") or "xrechnung").lower()
        try:
            if chosen not in FORMATS:
                raise ApiError("The format must be one of: " + ", ".join(FORMATS))
            invoice = invoice_object(tool_parameters.get("invoice"))
            result = post_json(self.runtime.credentials.get("api_key", ""), "/einvoice/create", {"invoice": invoice, "format": chosen})
        except ApiError as e:
            raise refuse(e) from e
        xml = result.get("xml") if isinstance(result.get("xml"), str) else ""
        yield self.create_json_message(result)
        yield self.create_text_message(xml)
        if xml:
            name = str(result.get("filename") or "invoice.xml")
            yield self.create_blob_message(blob=xml.encode("utf-8"), meta={"mime_type": "application/xml", "filename": name})
