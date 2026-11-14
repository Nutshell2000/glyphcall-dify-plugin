"""One small HTTP client for the document API. Fixed host, HTTPS only, the key goes in a header and never in a URL."""

from typing import Any

import httpx

BASE_URL = "https://tools.funwords.eu"
CREDITS_URL = f"{BASE_URL}/credits"
TIMEOUT = httpx.Timeout(120.0, connect=15.0)
MAX_FILE_BYTES = 10 * 1024 * 1024

# What the API reads, by file extension, for uploads whose type Dify did not record.
MIME_BY_EXTENSION = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "xml": "application/xml",
}


class ApiError(Exception):
    """A refusal the user can act on. The message never contains the key."""


def _headers(api_key: str) -> dict[str, str]:
    key = (api_key or "").strip()
    if not key:
        raise ApiError(f"No API key is set. Get a free one at {BASE_URL}/keys/free")
    return {"Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "glyphcall-dify-plugin/0.2.0"}


def _message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return f"HTTP {response.status_code}"
    if isinstance(body, dict):
        for name in ("error", "message", "detail", "note"):
            value = body.get(name)
            if isinstance(value, str) and value:
                return value
    return f"HTTP {response.status_code}"


def _checked(response: httpx.Response) -> dict[str, Any]:
    if response.status_code == 401:
        raise ApiError(f"The API key was not accepted. Check it, or get a free one at {BASE_URL}/keys/free")
    if response.status_code == 402:
        raise ApiError(f"This key has no credits left for this call, or it is not a valid key. Add credits or a plan at {CREDITS_URL}")
    if response.status_code == 429:
        raise ApiError("Too many calls right now. Wait a moment and run the step again. Nothing was charged.")
    if response.status_code >= 400:
        raise ApiError(f"{_message(response)} (nothing was charged)")
    try:
        body = response.json()
    except ValueError as e:
        raise ApiError("The API answered with something that is not JSON. Nothing was charged.") from e
    if not isinstance(body, dict):
        raise ApiError("The API answered with an unexpected shape. Nothing was charged.")
    return body


def check_key(api_key: str) -> dict[str, Any]:
    """Free: asks the API whether it knows this key."""
    try:
        response = httpx.get(f"{BASE_URL}/credits/balance", headers=_headers(api_key), timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise ApiError(f"Could not reach the API: {type(e).__name__}") from e
    return _checked(response)


def one_file(value: Any) -> Any:
    """Dify hands over one File, a list of them, or nothing."""
    if isinstance(value, list):
        value = value[0] if value else None
    return value


def file_parts(file: Any) -> tuple[bytes, str]:
    """The bytes and media type of a Dify File."""
    name = str(getattr(file, "filename", None) or getattr(file, "name", None) or "document")
    blob = getattr(file, "blob", None)
    if isinstance(blob, (bytearray, memoryview)):
        blob = bytes(blob)
    if not isinstance(blob, bytes) or not blob:
        raise ApiError(f"The file '{name}' is empty or could not be read from Dify.")
    if len(blob) > MAX_FILE_BYTES:
        raise ApiError(f"The file '{name}' is larger than 10 MB. Nothing was sent.")
    mime = str(getattr(file, "mime_type", None) or "")
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if extension in MIME_BY_EXTENSION and (not mime or mime == "application/octet-stream"):
        mime = MIME_BY_EXTENSION[extension]
    return blob, mime or "application/octet-stream"


def call(api_key: str, path: str, params: dict[str, Any], file: Any = None, url: str | None = None) -> dict[str, Any]:
    """Runs one tool: with an uploaded file in the POST body, or with a public URL of the file."""
    headers = _headers(api_key)
    query = {k: v for k, v in params.items() if v not in (None, "")}
    try:
        if file is not None:
            blob, mime = file_parts(file)
            name = str(getattr(file, "filename", None) or "document")
            # A multipart form with a `file` part: the one upload shape the API takes for every file type.
            response = httpx.post(f"{BASE_URL}{path}", params=query, files={"file": (name, blob, mime)}, headers=headers, timeout=TIMEOUT)
        else:
            address = (url or "").strip()
            if path.startswith(("/document/", "/einvoice/")):
                if not address.lower().startswith(("http://", "https://")):
                    raise ApiError("Give a file, or the public http(s) URL of one.")
                query["url"] = address
            response = httpx.get(f"{BASE_URL}{path}", params=query, headers=headers, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise ApiError(f"Could not reach the API: {type(e).__name__}. Nothing was charged.") from e
    return _checked(response)


def post_json(api_key: str, path: str, body: dict[str, Any], params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Runs one tool whose input is too large for a URL (an invoice, an XML text): the fields go in a JSON body."""
    headers = _headers(api_key)
    query = {k: v for k, v in (params or {}).items() if v not in (None, "")}
    try:
        response = httpx.post(f"{BASE_URL}{path}", params=query, json=body, headers=headers, timeout=TIMEOUT)
    except httpx.HTTPError as e:
        raise ApiError(f"Could not reach the API: {type(e).__name__}. Nothing was charged.") from e
    return _checked(response)
