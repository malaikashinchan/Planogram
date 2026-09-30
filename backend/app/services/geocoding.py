"""
Reverse geocoding using OpenStreetMap Nominatim.
"""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from backend.app.core.config import settings


def reverse_geocode(
    latitude: float,
    longitude: float,
) -> dict[str, str | None]:

    import time
    # Nominatim requires max 1 request/second
    time.sleep(1.1)

    params = urlencode(
        {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "addressdetails": 1,
        }
    )

    url = f"{settings.NOMINATIM_BASE_URL}/reverse?{params}"

    request = Request(
        url,
        headers={
            "User-Agent": settings.NOMINATIM_USER_AGENT,
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

    except (HTTPError, URLError, TimeoutError) as e:
        print(f"[Geocoding] Reverse geocode failed for ({latitude}, {longitude}): {e}")
        return {
            "address": None,
            "pincode": None,
        }

    address = data.get("address", {})

    return {
        "address": data.get("display_name"),
        "pincode": address.get("postcode"),
    }