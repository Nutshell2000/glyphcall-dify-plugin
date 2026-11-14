# Glyphcall Documents: invoice and document extraction

Read invoices, receipts and other documents into JSON inside a Dify workflow or agent, and convert documents to Markdown. No template per supplier: you get the same keys back whatever the layout or language.

Glyphcall is the document API of SpellzCode. This plugin is a thin client for it; the source is at https://github.com/Nutshell2000/glyphcall-dify-plugin.

## Tools

| Tool | What it returns |
|---|---|
| **Extract invoice data** | supplier and customer names, VAT numbers, invoice number, invoice and due dates, currency, subtotal, tax, total, IBAN, payment reference and every line item (description, quantity, unit price, amount). Optional: checks the supplier's EU VAT number in VIES. |
| **Extract fields from a document** | The fields you name, as one JSON object. Rows work too: `line_items[description,quantity,amount]`. For contracts, purchase orders, delivery notes, forms, reports. |
| **Document to Markdown** | Word with headings, lists and tables, Excel sheet by sheet, PowerPoint slide by slide, the text of a PDF, scanned PDFs and photos by OCR. |
| **Check an EU VAT number** | Valid or not in the EU's VIES register, with the registered name and address when the country shares them. |

Files: PDF, DOCX, XLSX, PPTX, PNG, JPEG, WebP. Up to 10 MB (images 3 MB). Each tool takes a file from the workflow or the public URL of one.

## Setup

1. Get an API key at https://tools.funwords.eu/credits (pay once from $1, or a plan from $9 a month; credits do not expire).
2. In Dify open **Plugins**, install **Glyphcall Documents**, choose **Authorize** and paste the key.
3. Add a tool to a workflow or an agent.

Connection: the plugin calls `https://tools.funwords.eu` over HTTPS. Nothing else is contacted.

## Example: invoices from an upload to rows

1. **Start** node with a file variable `invoice`.
2. **Extract invoice data** with *Invoice file* = `invoice`. Switch on *Check the supplier's EU VAT number* if you pay EU suppliers.
3. Use `json[0].invoice` in the next node: write a row to a sheet, post to your accounting system, or ask an LLM to code it to an account.

A value the document does not state comes back as `null` and is listed under `missing`. Nothing is guessed.

```json
{
  "invoice": {
    "supplier_name": "DEMO - Sliced Invoices",
    "invoice_number": "INV-3337",
    "invoice_date": "January 25, 2016",
    "due_date": "January 31, 2016",
    "subtotal": 85,
    "tax_amount": 8.5,
    "total": 93.5,
    "line_items": [{ "description": "Web Design", "quantity": 1, "unit_price": 85, "amount": 85 }]
  },
  "missing": ["supplier_vat_number", "currency", "iban"],
  "file_type": "pdf",
  "truncated": false
}
```

## Price

Charged to your key per successful call; a file that cannot be read and any failed call cost nothing.

| Call | Price |
|---|---|
| Extract invoice data, Extract fields | $0.03 |
| Document to Markdown | $0.005 |
| Check an EU VAT number (also when switched on inside Extract invoice data) | $0.01 |

So the $9 plan reads about 500 invoices a month.

## Limits

- An AI model reads the file: check amounts and dates that matter before you act on them.
- Extraction reads the first 24,000 characters of a file, and at most three pages of a scanned PDF.
- Old `.doc`, `.xls` and `.ppt` files and password-protected files are refused; save them in the current format first.
- Not tested on a self-hosted Dify behind a firewall that blocks outbound HTTPS.

## Privacy

Files are processed in memory for the request and are not stored or logged. See [PRIVACY.md](PRIVACY.md).

## Support

spellz111122@gmail.com, or open an issue at https://github.com/Nutshell2000/glyphcall-dify-plugin/issues
