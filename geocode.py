import aiohttp

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"


async def get_street_name(latitude: float, longitude: float) -> str:
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "accept-language": "uz,ru,en",
    }
    headers = {"User-Agent": "HoneymoonUzBot/1.0"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                NOMINATIM_URL, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return "Ko'cha nomi topilmadi"
                data = await resp.json()
    except Exception:
        return "Ko'cha nomi topilmadi"

    address = data.get("address", {})
    street = (
        address.get("road")
        or address.get("street")
        or address.get("pedestrian")
        or address.get("residential")
        or address.get("footway")
    )
    if street:
        return street

    display = data.get("display_name", "")
    if display:
        return display.split(",")[0].strip()

    return "Ko'cha nomi topilmadi"
