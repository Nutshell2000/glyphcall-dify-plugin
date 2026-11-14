"""Shared plumbing for the tools: read the inputs, call the API, turn a refusal into a readable error."""

import json
import re
from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError, call, one_file, post_json

INVOICE_FIELDS = (
    "supplier_name,supplier_vat_number,supplier_address,customer_name,customer_vat_number,"
    "invoice_number,invoice_date,due_date,currency,subtotal,tax_amount,total,iban,payment_reference,"
    "line_items[description,quantity,unit_price,amount]"
)


def clean_fields(raw: Any) -> str:
    """Field names as the API takes them: comma separated, brackets kept for row keys."""
    text = re.sub(r"\s*([,\[\]])\s*", r"\1", str(raw or "").replace("\n", ","))
    parts: list[str] = []
    depth = 0
    current = ""
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    parts.append(current)
    return ",".join(p.strip().replace(" ", "_") for p in parts if p.strip())


def document_call(tool: Tool, path: str, params: dict[str, Any], tool_parameters: dict[str, Any]) -> dict[str, Any]:
    file = one_file(tool_parameters.get("file"))
    url = str(tool_parameters.get("url") or "").strip()
    if file is None and not url:
        raise ApiError("Give a file, or the public http(s) URL of one.")
    return call(tool.runtime.credentials.get("api_key", ""), path, params, file=file, url=url)


def answer(tool: Tool, result: dict[str, Any], text: str | None = None) -> Generator[ToolInvokeMessage, None, None]:
    yield tool.create_json_message(result)
    yield tool.create_text_message(text if text is not None else json.dumps(result, ensure_ascii=False, indent=2))


def refuse(e: ApiError) -> Exception:
    return Exception(str(e))


def einvoice_call(tool: Tool, path: str, params: dict[str, Any], tool_parameters: dict[str, Any]) -> dict[str, Any]:
    """An e-invoice as a file (XML, or the PDF with the XML inside), as XML text, or as a public URL."""
    key = tool.runtime.credentials.get("api_key", "")
    file = one_file(tool_parameters.get("file"))
    if file is not None:
        return call(key, path, params, file=file)
    xml = str(tool_parameters.get("xml") or "").strip()
    if xml:
        if not xml.startswith("<"):
            raise ApiError("The XML text does not start with '<'. Give the e-invoice XML, a file, or a URL.")
        return post_json(key, path, {"xml": xml}, params)
    url = str(tool_parameters.get("url") or "").strip()
    if not url:
        raise ApiError("Give the e-invoice as a file, as XML text, or as the public http(s) URL of one.")
    return call(key, path, params, url=url)
