import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from langchain_core.tools import tool


SECRETS = Path(__file__).resolve().parent.parent / ".secrets"
load_dotenv(SECRETS, override=True)

ALERTS_URL = (
    "https://api.openmetrolinx.com/OpenDataAPI"
    "/api/V1/ServiceUpdate/ServiceAlert/All"
)


def extract_alerts(payload):
    """Extract alert records from common Metrolinx JSON wrappers."""

    if isinstance(payload, list):
        return payload

    if not isinstance(payload, dict):
        raise ValueError("Unexpected API response type")

    # Some API responses wrap records in a Messages object.
    for key in ("Messages", "messages", "Alerts", "alerts"):
        if key in payload:
            value = payload[key]

            if isinstance(value, list):
                return value

            if isinstance(value, dict):
                for nested_key in (
                    "Message", "message", "Alert", "alert"
                ):
                    if nested_key in value:
                        nested = value[nested_key]
                        if isinstance(nested, list):
                            return nested
                        if isinstance(nested, dict):
                            return [nested]

                if not value:
                    return []

                raise ValueError(
                    f"Unrecognized nested alert structure: {key}"
                )

            raise ValueError(
                f"Unexpected value for {key}: {type(value).__name__}"
            )

    # Some endpoints wrap the actual result in a root object.
    for key in ("ServiceAlerts", "ServiceAlert", "data", "Data"):
        if key in payload:
            return extract_alerts(payload[key])

    if not payload:
        return []

    raise ValueError(
        "Unrecognized alert response structure. "
        f"Top-level keys: {list(payload.keys())}"
    )


def get_service_alerts(line="all"):
    """Retrieve and optionally filter GO Transit service alerts."""

    api_key = os.getenv("GO_API_KEY")

    if not api_key:
        return {
            "status": "error",
            "message": "GO_API_KEY is missing."
        }

    try:
        response = requests.get(
            ALERTS_URL,
            params={"key": api_key},
            headers={"Accept": "application/json"},
            timeout=20
        )

        print(
            "SERVICE ALERT API STATUS:",
            response.status_code,
            flush=True
        )

        response.raise_for_status()

        if not response.content:
            return {
                "status": "unavailable",
                "message": "The API returned an empty response."
            }

        payload = response.json()

        alerts = extract_alerts(payload)

        # Normalize each record for a consistent output.
        normalized = []

        for alert in alerts:
            if isinstance(alert, dict):
                normalized.append(alert)
            elif isinstance(alert, str):
                normalized.append({"message": alert})

        # Optional line filtering
        requested_line = (line or "all").strip()

        if requested_line.lower() != "all":
            search_term = requested_line.casefold()

            filtered = [
                alert
                for alert in normalized
                if search_term in json.dumps(
                    alert, ensure_ascii=False
                ).casefold()
            ]

        else:
            filtered = normalized

        # Return a limited sample to avoid huge LLM prompts.
        return {
            "status": "success",
            "requested_line": requested_line,
            "total_alerts": len(normalized),
            "matching_alerts": len(filtered),
            "alerts": filtered[:10],
            "truncated": len(filtered) > 10,
            "source": ALERTS_URL,
            "note": (
                "Results are based on the API response at request "
                "time. Filtering uses text matching and may miss "
                "alerts identified only by route codes. "
                "No matching alerts does not guarantee "
                "that service is operating normally."
            )
        }

    except requests.RequestException as error:
        return {
            "status": "error",
            "message": f"Metrolinx API request failed: {error.__class__.__name__}"
        }

    except (ValueError, TypeError) as error:
        return {
            "status": "error",
            "message": f"Could not parse alerts: {error}"
        }


@tool
def check_go_service_alerts(line: str = "all") -> str:
    """
    Check GO Transit service alerts using the Metrolinx API.

    Use when a user asks about service alerts,
    disruptions, or general delay announcements.

    Args:
        line: GO Transit line name, such as
              Lakeshore West, Kitchener, or all.

    Returns:
        JSON containing service alert information.
    """

    result = get_service_alerts(line)
    return json.dumps(result, ensure_ascii=False, default=str)


if __name__ == "__main__":
    result = get_service_alerts("all")

    print(json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
        default=str
    ))
