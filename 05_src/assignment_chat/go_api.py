import os
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# 1. Load API Key
# --------------------------------------------------

secrets_path = Path(__file__).resolve().parent.parent / ".secrets"

load_dotenv(secrets_path, override=True)

GO_API_KEY = os.getenv("GO_API_KEY")

print("GO API key loaded:", bool(GO_API_KEY))


# --------------------------------------------------
# 2. GO Transit API Configuration
# --------------------------------------------------

GO_API_URL = (
    "https://api.openmetrolinx.com/"
    "OpenDataAPI/api/V1/Gtfs/Feed/VehiclePosition"
)


# --------------------------------------------------
# 3. Retrieve GO Transit Vehicle Data
# --------------------------------------------------

def get_go_train():

    if not GO_API_KEY:
        return {"error": "GO_API_KEY is not configured"}

    try:
        response = requests.get(
            GO_API_URL,
            params={"key": GO_API_KEY},
            timeout=20
        )

        print("GO API HTTP Status:", response.status_code, flush=True)

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):
            return {"error": "Unexpected API response format"}

        # Support common GTFS response structures
        entities = data.get("entity", data.get("Entity", []))

        if not isinstance(entities, list):
            return {"error": "Vehicle entity list is missing"}

        vehicles = []

        for entity in entities:

            vehicle = entity.get(
                "vehicle",
                entity.get("Vehicle", {})
            )

            if not isinstance(vehicle, dict):
                continue

            position = vehicle.get(
                "position",
                vehicle.get("Position", {})
            )

            if not isinstance(position, dict):
                continue

            vehicle_info = vehicle.get(
                "vehicle",
                vehicle.get("Vehicle", {})
            )

            trip = vehicle.get(
                "trip",
                vehicle.get("Trip", {})
            )

            if not isinstance(vehicle_info, dict):
                vehicle_info = {}

            if not isinstance(trip, dict):
                trip = {}

            vehicles.append({
                "vehicle_id": vehicle_info.get(
                    "id",
                    vehicle_info.get("Id", "Unknown")
                ),
                "trip_id": trip.get(
                    "tripId",
                    trip.get("TripId", "Unknown")
                ),
                "route_id": trip.get(
                    "routeId",
                    trip.get("RouteId", "Unknown")
                ),
                "latitude": position.get(
                    "latitude",
                    position.get("Latitude")
                ),
                "longitude": position.get(
                    "longitude",
                    position.get("Longitude")
                )
            })

        # Extract optional feed timestamp
        header = data.get("header", data.get("Header", {}))

        if not isinstance(header, dict):
            header = {}

        timestamp = header.get(
            "timestamp",
            header.get("Timestamp")
        )

        return {
            "timestamp": timestamp,
            "total_vehicles": len(vehicles),
            "vehicles": vehicles
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"GO API request failed: {e}"}

    except ValueError as e:
        return {"error": f"Invalid API response: {e}"}

    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


# --------------------------------------------------
# 4. Test API Independently
# --------------------------------------------------

if __name__ == "__main__":

    result = get_go_train()

    if "error" in result:
        print("ERROR:", result["error"])

    else:
        print("Total vehicles:", result["total_vehicles"])
        print("Feed timestamp:", result["timestamp"])
        print("Sample vehicles:")

        for vehicle in result["vehicles"][:5]:
            print(vehicle)
