from django.shortcuts import render
from django.contrib import messages
import requests
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# List of known countries and Indian states to reject
INVALID_LOCATIONS = {
    # Countries
    "india", "pakistan", "bangladesh", "nepal", "china", "usa", "uk",
    "australia", "canada", "france", "germany", "japan", "russia",
    "brazil", "mexico", "italy", "spain", "afghanistan", "iran",
    # Indian States & UTs
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
    "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan",
    "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
    "uttarakhand", "west bengal", "delhi", "jammu and kashmir", "ladakh",
    "puducherry", "chandigarh", "lakshadweep", "andaman and nicobar",
    "dadra and nagar haveli", "daman and diu",
}


def is_valid_city(city: str, api_data: dict) -> tuple[bool, str]:
    """
    Validates whether the API response corresponds to a city-level location.
    Returns (is_valid: bool, error_message: str)
    """
    city_lower = city.strip().lower()

    # Rule 1: Reject if input is a known country or state
    if city_lower in INVALID_LOCATIONS:
        return False, f'"{city}" is a country or state, not a city. Please enter a specific city name.'

    # Rule 2: Use OpenWeather's location type — reject if it's not a city/town/village
    # The API returns a "sys" block and a location name; for countries the name matches country
    api_name = api_data.get("name", "").lower()
    country_code = api_data.get("sys", {}).get("country", "")

    # Rule 3: If API returned name matches a known invalid location, reject it
    if api_name in INVALID_LOCATIONS:
        return False, f'"{city}" resolved to a non-city location. Please enter a valid city name.'

    # Rule 4: Check population / location type via "coord" sanity — skip, too complex.
    # Instead, check if the returned name is suspiciously different (API redirected to a region)
    # e.g. user typed "andhra pradesh" but API returned "Hyderabad" — that case is fine.
    # But if user typed "india" and API returned "India" — reject it.
    if api_name == country_code.lower():
        return False, f'"{city}" appears to be a country. Please enter a specific city.'

    return True, ""


# Home page with welcome message
def homepage(request):
    return render(request, 'weatherapp/home.html')


def home(request):
    # Default fallback image
    image_url = "https://images.pexels.com/photos/414171/pexels-photo-414171.jpeg"

    if request.method == 'POST' and 'city' in request.POST:
        city = request.POST['city'].strip().title()
    else:
        city = 'Indore'

    # Dynamic Unsplash image (no API key needed)
    image_url = f"https://source.unsplash.com/1600x900/?{city},weather"

    # Weather API config
    api_key = os.getenv("API_KEY")
    weather_url = (
        f'https://api.openweathermap.org/data/2.5/weather'
        f'?q={city}&appid={api_key}&units=metric'
    )

    try:
        # --- Fetch weather data ---
        response = requests.get(weather_url, timeout=10)
        data = response.json()

        # Check if API returned a valid response
        if data.get("cod") != 200:
            messages.error(request, f'City "{city}" was not found. Please check the spelling.')
            raise Exception("City not found by API")

        # --- City-level validation ---
        valid, error_msg = is_valid_city(city, data)
        if not valid:
            messages.error(request, error_msg)
            raise Exception("Invalid location type")

        # --- Extract weather data ---
        description = data['weather'][0]['description']
        icon        = data['weather'][0]['icon']
        temp        = data['main']['temp']
        humidity    = data['main']['humidity']
        wind        = data['wind']['speed']
        day         = datetime.date.today()

        return render(request, 'weatherapp/index.html', {
            'description':        description,
            'icon':               icon,
            'temp':               temp,
            'day':                day,
            'city':               city,
            'humidity':           humidity,
            'wind':               wind,
            'exception_occurred': False,
            'image_url':          image_url,
        })

    except Exception:
        day = datetime.date.today()
        # Only add a generic fallback message if no specific one was already added
        storage = messages.get_messages(request)
        existing = [str(m) for m in storage]
        storage.used = False  # Reset so messages still render in template
        if not existing:
            messages.error(request, 'City data is not available. Please try a valid city name.')

        return render(request, 'weatherapp/index.html', {
            'description':        'clear sky',
            'icon':               '01d',
            'temp':               25,
            'day':                day,
            'city':               'Indore',
            'humidity':           '--',
            'wind':               '--',
            'exception_occurred': True,
            'image_url':          image_url,
        })


def features(request):
    return render(request, 'weatherapp/features.html')

def about(request):
    return render(request, 'weatherapp/about.html')

def demo(request):
    return render(request, 'weatherapp/demo.html')