# Privacy

This plugin sends data to one service only: the Glyphcall document API at `https://tools.funwords.eu`, run by SpellzCode.

## What is sent

- The file you give a tool (or the public URL of a file), and the field names you ask for.
- For the VAT check: the VAT number. The API forwards that number to the European Commission's VIES service to get the answer.
- Your API key, in the `Authorization` header over HTTPS. The key is never put in a URL.

## What happens to it

- A file sent in a request is held in memory for that request only. It is not stored, cached or logged by the API.
- The text of a document is read by an AI model hosted on Cloudflare Workers AI to find the fields. It is not used to train models.
- The API keeps a count of calls per key for billing, and standard request logs without file contents.
- The plugin itself stores nothing and writes no logs with your data. Dify stores your API key as an encrypted credential.

## What is not collected

No analytics, no tracking, no contact details. The plugin does not read anything in your Dify workspace other than the inputs you pass to its tools.

## Your documents

Invoices and other documents can contain personal or financial data. Send only documents you are allowed to process, and check amounts and dates that matter before acting on them: an AI model reads the file.

Full policy of the service: https://tools.funwords.eu/privacy
Contact: spellz111122@gmail.com
