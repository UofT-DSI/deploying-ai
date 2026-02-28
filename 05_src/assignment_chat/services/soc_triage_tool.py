# services/soc_triage_tool.py — Service 3: SOC Alert Triage (Function Calling)

import re
import json
from config import client, CHAT_MODEL

# --- Tool definition exposed to the LLM ---
SOC_TRIAGE_TOOL = {
    "type": "function",
    "name": "ms_alert_triage",
    "description": (
        "Parses a Microsoft Defender or Sentinel alert, extracts IOCs and key fields, "
        "and returns a category-based triage checklist."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "alert_text": {
                "type": "string",
                "description": "The raw alert text or JSON snippet from Microsoft Defender/Sentinel.",
            }
        },
        "required": ["alert_text"],
    },
}

# --- Category-based checklist templates ---
CHECKLISTS = {
    "phishing": [
        "Isolate the email from the mailbox.",
        "Block the sender and any URLs at the email gateway.",
        "Check if the user clicked any links or submitted credentials.",
        "Search mail logs for similar messages sent to other users.",
        "Reset credentials if compromise is suspected.",
        "Confirm URL/domain is blocked across security controls.",
    ],
    "malware": [
        "Isolate the affected endpoint immediately.",
        "Capture a memory dump and preserve logs.",
        "Identify the malware family (hash lookup, sandbox).",
        "Check for lateral movement from the affected host.",
        "Scan other endpoints for the same IOCs.",
        "Remediate: remove malware, patch vulnerability, reimage if needed.",
    ],
    "credential_access": [
        "Identify which credentials may have been exposed.",
        "Force password reset for affected accounts.",
        "Check for unusual authentication events (new locations, times).",
        "Look for LSASS access or mimikatz-style tooling.",
        "Review privileged account activity.",
        "Enable MFA if not already in place.",
    ],
    "persistence": [
        "Identify the persistence mechanism (registry, scheduled task, service).",
        "Remove the persistence entry.",
        "Check for related payloads dropped on disk.",
        "Review similar hosts for the same artefacts.",
        "Validate the host is clean post-remediation.",
    ],
    "lateral_movement": [
        "Map the source and destination hosts.",
        "Isolate affected systems.",
        "Review authentication logs (WMI, RDP, SMB).",
        "Identify the account used and reset credentials.",
        "Scope the full blast radius.",
    ],
    "default": [
        "Triage the alert severity and confirm it is not a false positive.",
        "Identify affected users, devices, and assets.",
        "Contain the threat if active.",
        "Preserve logs and evidence.",
        "Escalate if scope is unclear or high severity.",
    ],
}


def _extract_iocs(text: str) -> dict:
    """Use regex to extract common IOCs from alert text."""
    return {
        "ips":     re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text),
        "domains": re.findall(r"\b(?:[a-zA-Z0-9\-]+\.)+(?:com|net|org|ru|io|uk|gov|edu|xyz|info)\b", text),
        "urls":    re.findall(r"https?://[^\s\"']+", text),
        "hashes":  re.findall(r"\b[a-fA-F0-9]{32,64}\b", text),
        "emails":  re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text),
    }


def _detect_category(text: str) -> str:
    """Detect alert category from keywords."""
    t = text.lower()
    if any(k in t for k in ["phishing", "malicious url", "email", "spam"]):
        return "phishing"
    if any(k in t for k in ["malware", "ransomware", "trojan", "virus", "worm"]):
        return "malware"
    if any(k in t for k in ["credential", "lsass", "mimikatz", "dump", "password"]):
        return "credential_access"
    if any(k in t for k in ["persistence", "registry", "scheduled task", "autorun"]):
        return "persistence"
    if any(k in t for k in ["lateral movement", "wmi", "rdp", "smb", "pass-the-hash"]):
        return "lateral_movement"
    return "default"


def ms_alert_triage(alert_text: str) -> dict:
    """
    Parse a Microsoft alert and return structured triage data.
    This is the function the LLM calls via function calling.
    """
    iocs      = _extract_iocs(alert_text)
    category  = _detect_category(alert_text)
    checklist = CHECKLISTS.get(category, CHECKLISTS["default"])

    return {
        "category":         category,
        "iocs":             iocs,
        "triage_checklist": checklist,
    }


def run_soc_triage(alert_text: str, context: str) -> str:
    """
    Send alert to LLM with the SOC triage tool available.
    Uses the responses API with tools (function calling).
    """

    # First LLM call — may call the tool
    response = client.responses.create(
        model=CHAT_MODEL,
        input=f"{context}\n\nUser: Please triage this alert:\n\n{alert_text}",
        tools=[SOC_TRIAGE_TOOL],
    )

    # Check if the model called the tool
    tool_call = next(
        (item for item in response.output if item.type == "function_call"),
        None,
    )

    if tool_call:
        args        = json.loads(tool_call.arguments)
        tool_result = ms_alert_triage(args["alert_text"])

        # Second LLM call — format the tool result into a nice response
        followup_prompt = (
            f"{context}\n\n"
            f"The ms_alert_triage tool returned:\n{json.dumps(tool_result, indent=2)}\n\n"
            f"Write a clear SOC mentor response: summarise what happened, "
            f"list the extracted IOCs, and present the triage checklist step by step."
        )
        final = client.responses.create(
            model=CHAT_MODEL,
            input=followup_prompt,
        )
        return final.output_text

    # Model responded directly without calling the tool
    return response.output_text