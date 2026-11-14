"""Runs the three e-invoice tools against an API host. Usage:

    python tests/einvoice_check.py <e-invoice.xml> [<zugferd.pdf>]

Environment: GLYPHCALL_TEST_KEY (any text against a local server without a paywall) and, for a local or staging
server, GLYPHCALL_TEST_BASE (for example http://localhost:8801). Without GLYPHCALL_TEST_BASE it calls the live API.
Works without dify_plugin installed: a small stand-in supplies Tool and the message makers.
"""

import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import dify_plugin  # noqa: F401
except Exception:
    sdk = types.ModuleType("dify_plugin")

    class Tool:
        pass

    sdk.Tool = Tool
    sdk.ToolProvider = type("ToolProvider", (), {})
    entities = types.ModuleType("dify_plugin.entities")
    tool_entities = types.ModuleType("dify_plugin.entities.tool")
    tool_entities.ToolInvokeMessage = tuple
    for name, module in {"dify_plugin": sdk, "dify_plugin.entities": entities, "dify_plugin.entities.tool": tool_entities}.items():
        sys.modules[name] = module

import tools._client as client  # noqa: E402
from tools.create_einvoice import CreateEinvoiceTool, invoice_object  # noqa: E402
from tools.einvoice_to_json import EinvoiceToJsonTool  # noqa: E402
from tools.validate_einvoice import ValidateEinvoiceTool  # noqa: E402

if os.environ.get("GLYPHCALL_TEST_BASE"):
    client.BASE_URL = os.environ["GLYPHCALL_TEST_BASE"].rstrip("/")


class FakeFile:
    def __init__(self, path: Path):
        self.filename = path.name
        self.blob = path.read_bytes()
        self.mime_type = ""


def make(cls):
    tool = cls.__new__(cls)
    tool.runtime = types.SimpleNamespace(credentials={"api_key": os.environ.get("GLYPHCALL_TEST_KEY", "")})
    tool.create_json_message = lambda value: ("json", value)
    tool.create_text_message = lambda value: ("text", value)
    tool.create_blob_message = lambda blob, meta=None: ("blob", {"bytes": len(blob), **(meta or {})})
    return tool


def run(cls, **parameters):
    return dict(make(cls)._invoke(parameters))


def expect(condition: bool, what: str) -> None:
    print(("ok   " if condition else "FAIL ") + what)
    if not condition:
        expect.failed += 1


expect.failed = 0

INVOICE = {
    "number": "RE-2026-0042", "issueDate": "2026-11-14", "dueDate": "2026-12-14", "buyerReference": "04011000-12345-06",
    "seller": {"name": "Muster Software GmbH", "vatId": "DE123456789", "street": "Hauptstrasse 1", "postCode": "10115", "city": "Berlin", "country": "DE",
               "contactName": "Erika Muster", "phone": "+49 30 1234567", "email": "rechnung@muster-software.example"},
    "buyer": {"name": "Kunde AG", "street": "Marktplatz 5", "postCode": "20095", "city": "Hamburg", "country": "DE"},
    "lines": [{"name": "Beratung", "quantity": 8, "unit": "HUR", "unitPrice": 120, "vatRate": 19}],
    "payment": {"iban": "DE02120300000000202051", "terms": "Zahlbar innerhalb von 30 Tagen"},
}


def main() -> int:
    sample = Path(sys.argv[1])
    print(f"host: {client.BASE_URL}")

    made = run(CreateEinvoiceTool, invoice=json.dumps(INVOICE), format="xrechnung")
    xml = made["text"]
    expect(xml.startswith("<?xml") and "CrossIndustryInvoice" in xml, "create: XRechnung XML as text")
    expect(made["json"]["totals"]["grand"] == 1142.4, f"create: totals computed ({made['json']['totals']})")
    expect(made["blob"]["mime_type"] == "application/xml" and made["blob"]["filename"] == "RE-2026-0042.xml", f"create: XML as a file ({made['blob']})")

    checked = run(ValidateEinvoiceTool, xml=xml)
    expect(checked["json"]["valid"] is True and checked["json"]["profile"] == "xrechnung", "validate: what we created is valid under the XRechnung rules (XML text)")
    expect(checked["text"].startswith("Valid"), f"validate: readable verdict ({checked['text'].splitlines()[0]})")

    broken = xml.replace("<ram:GrandTotalAmount>1142.40", "<ram:GrandTotalAmount>999.00")
    bad = run(ValidateEinvoiceTool, xml=broken)
    rules = [e["rule"] for e in bad["json"]["errors"]]
    expect(bad["json"]["valid"] is False and "BR-CO-15" in rules, f"validate: a wrong total is found ({rules})")
    expect("BR-CO-15" in bad["text"] and "Fix:" in bad["text"], "validate: the verdict names the rule and the fix")

    from_file = run(ValidateEinvoiceTool, file=FakeFile(sample), profile="en16931")
    expect(from_file["json"]["valid"] is True and from_file["json"]["profile"] == "en16931", f"validate: an uploaded file, EN 16931 rules only ({sample.name})")

    read = run(EinvoiceToJsonTool, file=FakeFile(sample))
    expect(bool(read["json"]["invoice"].get("number")) and len(read["json"]["invoice"]["lines"]) >= 1, f"to JSON: number {read['json']['invoice'].get('number')}, {len(read['json']['invoice']['lines'])} line(s)")

    if len(sys.argv) > 2:
        pdf = run(EinvoiceToJsonTool, file=FakeFile(Path(sys.argv[2])))
        expect(pdf["json"]["syntax"] == "CII" and bool(pdf["json"]["invoice"].get("number")), f"to JSON: the XML inside a ZUGFeRD PDF (number {pdf['json']['invoice'].get('number')})")

    # What extract_invoice returns goes straight into create.
    extracted = {"invoice": {"supplier_name": "Coolblue B.V.", "supplier_vat_number": "NL810433941B01", "supplier_address": "Weena 664, Rotterdam", "customer_name": "Klant B.V.",
                             "invoice_number": "993548900", "invoice_date": "2014-04-19", "due_date": "2014-05-19", "currency": "EUR", "subtotal": 593.36, "tax_amount": 124.61,
                             "total": 717.97, "iban": "NL50INGB0683251309", "line_items": [{"description": "Laptop", "quantity": 1, "unit_price": 593.36, "amount": 593.36}]},
                 "missing": [], "file_type": "pdf"}
    expect(invoice_object(extracted)["seller_name"] == "Coolblue B.V.", "create: the answer of Extract invoice data is unwrapped and renamed")
    try:
        chained = run(CreateEinvoiceTool, invoice=json.dumps({**extracted["invoice"], "buyer_country": "NL"}), format="zugferd")
        expect(chained["json"]["totals"]["grand"] == 717.97 and chained["blob"]["filename"] == "factur-x.xml", f"create: a read invoice becomes a Factur-X XML ({chained['json']['totals']})")
    except Exception as e:  # noqa: BLE001
        expect(False, f"create from a read invoice: {e}")

    hybrid = run(CreateEinvoiceTool, invoice=json.dumps(INVOICE), format="zugferd-pdf")
    expect(hybrid["blob"]["mime_type"] == "application/pdf" and hybrid["blob"]["filename"] == "RE-2026-0042.pdf" and hybrid["blob"]["bytes"] > 30000, f"create: ZUGFeRD PDF as a file ({hybrid['blob']})")
    expect("pdfBase64" not in hybrid["json"], "create: the PDF is not repeated as base64 in the JSON")

    try:
        run(CreateEinvoiceTool, invoice=json.dumps({"number": "X", "seller": {"name": "A"}, "lines": []}), format="xrechnung")
        expect(False, "create: broken data should be refused")
    except Exception as e:  # noqa: BLE001
        expect("BR-16" in str(e) and "nothing was charged" in str(e), f"create: broken data is refused with rule numbers ({str(e)[:90]}...)")
    try:
        run(ValidateEinvoiceTool)
        expect(False, "validate: no input should be refused")
    except Exception as e:  # noqa: BLE001
        expect("file" in str(e), "validate: no input is refused before any call")

    print("FAILED" if expect.failed else "all passed")
    return 1 if expect.failed else 0


if __name__ == "__main__":
    sys.exit(main())
