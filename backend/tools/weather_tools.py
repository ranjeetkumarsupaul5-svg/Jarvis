import requests


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(location: str):
    """
    Get current weather for a city/location.
    """

    try:
        location = (location or "").strip()

        if not location:
            return {
                "success": False,
                "message": "Please provide a location.",
                "data": None,
                "error": "Location is required."
            }

        # Step 1: Convert city name to coordinates
        geo_response = requests.get(
            GEOCODING_URL,
            params={
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json"
            },
            timeout=10
        )

        geo_response.raise_for_status()
        geo_data = geo_response.json()

        results = geo_data.get("results", [])

        if not results:
            return {
                "success": False,
                "message": f"I could not find {location}.",
                "data": None,
                "error": "Location not found."
            }

        place = results[0]

        latitude = place["latitude"]
        longitude = place["longitude"]

        # Step 2: Get current weather
        weather_response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "is_day,"
                    "precipitation,"
                    "rain,"
                    "showers,"
                    "snowfall,"
                    "weather_code,"
                    "cloud_cover,"
                    "wind_speed_10m,"
                    "wind_direction_10m"
                ),
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "timezone": "auto"
            },
            timeout=10
        )

        weather_response.raise_for_status()
        weather_data = weather_response.json()

        current = weather_data.get("current", {})

        data = {
            "location": place.get("name", location),
            "country": place.get("country"),
            "latitude": latitude,
            "longitude": longitude,
            "timezone": weather_data.get("timezone"),
            "temperature_c": current.get("temperature_2m"),
            "humidity_percent": current.get("relative_humidity_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "is_day": current.get("is_day"),
            "precipitation_mm": current.get("precipitation"),
            "rain_mm": current.get("rain"),
            "showers_mm": current.get("showers"),
            "snowfall_cm": current.get("snowfall"),
            "weather_code": current.get("weather_code"),
            "cloud_cover_percent": current.get("cloud_cover"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "wind_direction": current.get("wind_direction_10m"),
            "time": current.get("time")
        }

        return {
            "success": True,
            "message": f"Weather retrieved for {data['location']}.",
            "data": data,
            "error": None
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "message": "Weather service is currently unavailable.",
            "data": None,
            "error": str(e)
        }

    except Exception as e:
        return {
            "success": False,
            "message": "Unable to get weather information.",
            "data": None,
            "error": str(e)
        }