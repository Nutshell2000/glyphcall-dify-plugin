from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import ApiError
from tools._run import answer, einvoice_call, refuse


def summary(result: dict[str, Any]) -> str:
    """A short readable verdict: what an LLM or a person reads first."""
    errors = result.get("errors") or []
    warnings = result.get("warnings") or []
    head = "Valid" if result.get("valid") else f"Not valid: {len(errors)} error(s)"
    lines = [f"{head} ({result.get('standard', 'e-invoice')}, {result.get('rulesChecked', 0)} rules checked)."]
    for finding in [*errors, *warnings][:40]:
        where = f" [{finding.get('location')}]" if finding.get("location") else ""
        lines.append(f"- {finding.get('rule')} ({finding.get('level')}){where}: {finding.get('message')} Fix: {finding.get('fix')}")
    if result.get("notChecked"):
        lines.append("Not checked: " + ", ".join(str(x) for x in result["notChecked"]) + ".")
    lines.append("This is a subset of the business rules, not the official KoSIT validator.")
    return "\n".join(lines)


class ValidateEinvoiceTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        profile = str(tool_parameters.get("profile") or "auto").lower()
        params = {"profile": profile} if profile in ("xrechnung", "en16931") else {}
        try:
            result = einvoice_call(self, "/einvoice/validate", params, tool_parameters)
        except ApiError as e:
            raise refuse(e) from e
        yield from answer(self, result, summary(result))
