from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools._client import ApiError, check_key


class GlyphcallProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            check_key(credentials.get("api_key", ""))
        except ApiError as e:
            raise ToolProviderCredentialValidationError(str(e)) from e
