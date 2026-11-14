"""Runs every tool against the live API. Needs GLYPHCALL_TEST_KEY in the environment and a sample file path as argv[1].

Works with or without dify_plugin installed: without it, a small stand-in supplies Tool and the message makers.
"""

import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import dify_plugin  # noqa: F401
    REAL_SDK = True
except Exception:  # the SDK is not installable everywhere; the tools only need these names
    REAL_SDK = False
    sdk = types.ModuleType("dify_plugin")

    class Tool:
        def create_json_message(self, value):
            return ("json", value)

        def create_text_message(self, value):
            return ("text", value)

    class ToolProvider:
        pass

    sdk.Tool = Tool
    sdk.ToolProvider = ToolProvider
    entities = types.ModuleType("dify_plugin.entities")
    tool_entities = types.ModuleType("dify_plugin.entities.tool")
    tool_entities.ToolInvokeMessage = tuple
    errors = types.ModuleType("dify_plugin.errors")
    tool_errors = types.ModuleType("dify_plugin.errors.tool")

    class ToolProviderCredentialValidationError(Exception):
        pass

    tool_errors.ToolProviderCredentialValidationError = ToolProviderCredentialValidationError
    for name, module in {
        "dify_plugin": sdk, "dify_plugin.entities": entities, "dify_plugin.entities.tool": tool_entities,
        "dify_plugin.errors": errors, "dify_plugin.errors.tool": tool_errors,
    }.items():
        sys.modules[name] = module

from provider.glyphcall import GlyphcallProvider  # noqa: E402
from tools.check_vat_number import CheckVatNumberTool  # noqa: E402
from tools.document_to_markdown import DocumentToMarkdownTool  # noqa: E402
from tools.extract_fields import ExtractFieldsTool  # noqa: E402
from tools.extract_invoice import ExtractInvoiceTool  # noqa: E402
from tools._run import clean_fields  # noqa: E402


class FakeFile:
    def __init__(self, path: Path, mime: str = ""):
        self.filename = path.name
        self.blob = path.read_bytes()
        self.mime_type = mime


def make(cls, key):
    tool = cls.__new__(cls)
    tool.runtime = types.SimpleNamespace(credentials={"api_key": key})
    if REAL_SDK:
        tool.create_json_message = lambda value: ("json", value)
        tool.create_text_message = lambda value: ("text", value)
    return tool


def run(tool, params):
    return dict(tool._invoke(params))


def main() -> int:
    key = os.environ.get("GLYPHCALL_TEST_KEY", "").strip()
    sample = Path(sys.argv[1])
    failures = 0

    def check(name, ok, detail=""):
        nonlocal failures
        print(("PASS " if ok else "FAIL ") + name + (f": {detail}" if detail else ""))
        failures += 0 if ok else 1

    cleaned = clean_fields("Invoice Number, total\nline_items[ description, unit price ]")
    check("field cleaning", cleaned == "Invoice_Number,total,line_items[description,unit_price]", cleaned)

    provider = GlyphcallProvider.__new__(GlyphcallProvider)
    try:
        provider._validate_credentials({"api_key": key})
        check("good key accepted", True)
    except Exception as e:
        check("good key accepted", False, str(e))
    try:
        provider._validate_credentials({"api_key": "adt_not_a_real_key"})
        check("bad key refused", False)
    except Exception as e:
        check("bad key refused", key not in str(e), str(e))

    out = run(make(ExtractInvoiceTool, key), {"file": FakeFile(sample), "check_vat": True, "extra_fields": "payment terms"})
    invoice = out["json"]["invoice"]
    check("invoice number", invoice.get("invoice_number") == "INV-3337", str(invoice.get("invoice_number")))
    check("invoice total", str(invoice.get("total")) in ("93.5", "93.50"), str(invoice.get("total")))
    check("line items", isinstance(invoice.get("line_items"), list) and len(invoice["line_items"]) >= 1, str(invoice.get("line_items"))[:120])
    check("vat check reported", "supplier_vat_check" in out["json"], str(out["json"].get("supplier_vat_check"))[:160])
    print("     invoice keys:", sorted(invoice.keys()))

    out = run(make(ExtractFieldsTool, key), {"file": [FakeFile(sample, "application/octet-stream")], "fields": "invoice_number, customer_name"})
    check("fields from a list of files", out["json"]["data"].get("invoice_number") == "INV-3337", str(out["json"]["data"]))

    out = run(make(DocumentToMarkdownTool, key), {"file": FakeFile(sample), "format": "markdown", "max_chars": 2000})
    check("markdown text", "INV-3337" in out["text"], out["text"][:100].replace("\n", " "))
    print("     text result keys:", sorted(out["json"].keys()))

    out = run(make(DocumentToMarkdownTool, key), {"url": "https://calibre-ebook.com/downloads/demos/demo.docx"})
    check("docx by URL", len(out["text"]) > 200, out["text"][:80].replace("\n", " "))

    out = run(make(CheckVatNumberTool, key), {"vat_number": "SE 556703748501"})
    check("vat number", "valid" in out["json"], str(out["json"])[:200])

    for label, tool, params in (
        ("no file refused", ExtractFieldsTool, {"fields": "a"}),
        ("no fields refused", ExtractFieldsTool, {"file": FakeFile(sample), "fields": " "}),
        ("bad key on a tool", DocumentToMarkdownTool, None),
    ):
        try:
            if params is None:
                run(make(tool, "adt_not_a_real_key"), {"file": FakeFile(sample)})
            else:
                run(make(tool, key), params)
            check(label, False, "no error raised")
        except Exception as e:
            check(label, key not in str(e), str(e))

    print("SDK:", "real dify_plugin" if REAL_SDK else "stand-in")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
