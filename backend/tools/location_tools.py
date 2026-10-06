import requests

IP_LOCATION_URL = "https://ipwho.is/"


def get_location():
    """
    Get approximate current location using the public IP address.
    """
    try:
        response = requests.get(
            IP_LOCATION_URL,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        return {
            "success": True,
            "message": "Location retrieved successfully.",
            "data": {
                "ip": data.get("ip"),
                "city": data.get("city"),
                "region": data.get("region"),
                "country": data.get("country") or data.get("country_name") or "India",
                "country_code": data.get("country_code"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "timezone": data.get("timezone"),
                "postal": data.get("postal")
            },
            "error": None
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "message": "Location service is currently unavailable.",
            "data": None,
            "error": str(e)
        }

    except Exception as e:
        return {
            "success": False,
            "message": "Unable to get location information.",
            "data": None,
            "error": str(e)
        }