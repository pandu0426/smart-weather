from django.shortcuts import render
from django.contrib import messages
import requests
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

from .constants import INVALID_LOCATIONS


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
    import requests
    import os
    import datetime
    from django.http import JsonResponse
    from django.shortcuts import render

    # Detect AJAX request (via header or query param)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.GET.get('ajax') == '1'

    if request.method == 'POST' and 'city' in request.POST:
        city = request.POST['city'].strip().title()
    elif request.GET.get('city'):
        city = request.GET.get('city').strip().title()
    else:
        city = 'Indore'

    # Dynamic Unsplash image
    image_url = f"https://images.unsplash.com/featured/1600x900/?{city},weather"
    api_key = os.getenv("API_KEY")
    weather_url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'

    try:
        response = requests.get(weather_url, timeout=10)
        data = response.json()

        if data.get("cod") != 200:
            raise Exception("City not found")

        # --- Fetch 5-Day Forecast ---
        forecast_url = f'https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric'
        f_response = requests.get(forecast_url, timeout=10)
        f_data = f_response.json()
        
        forecast_list = []
        if f_data.get("cod") == "200":
            # Extract one forecast per day (approx. 12:00 PM)
            seen_dates = []
            for entry in f_data.get('list', []):
                dt = datetime.datetime.fromtimestamp(entry['dt'])
                date_str = dt.strftime("%Y-%m-%d")
                # Pick the forecast closest to noon, and avoid duplicate days
                if date_str not in seen_dates and dt.hour >= 12:
                    forecast_list.append({
                        'day': dt.strftime("%a"),
                        'temp': round(entry['main']['temp']),
                        'icon': entry['weather'][0]['icon'],
                        'desc': entry['weather'][0]['description']
                    })
                    seen_dates.append(date_str)
            # Ensure we only have 5 days
            forecast_list = forecast_list[:5]

        # --- City-level validation ---
        from .views import is_valid_city
        valid, error_msg = is_valid_city(city, data)
        if not valid:
            raise Exception(error_msg)

        weather_data = {
            'description': data['weather'][0]['description'],
            'icon':        data['weather'][0]['icon'],
            'temp':        data['main']['temp'],
            'humidity':    data['main']['humidity'],
            'wind':        data['wind']['speed'],
            'city':        city,
            'day':         datetime.date.today().strftime("%B %d, %Y"),
            'image_url':   image_url,
            'forecast':    forecast_list,
            'success':     True
        }

        if is_ajax:
            return JsonResponse(weather_data)
        
        return render(request, 'weatherapp/index.html', weather_data)

    except Exception as e:
        error_data = {
            'success': False,
            'error': str(e) if "City not found" in str(e) or "not a city" in str(e) else "City data not available.",
            'city': city,
            'day': datetime.date.today().strftime("%B %d, %Y"),
            'image_url': image_url,
        }
        if is_ajax:
            return JsonResponse(error_data)
        
        # Fallback for direct page load errors
        return render(request, 'weatherapp/index.html', {**error_data, 'exception_occurred': True})


def features(request):
    return render(request, 'weatherapp/features.html')

def about(request):
    return render(request, 'weatherapp/about.html')

def demo(request):
    return render(request, 'weatherapp/demo.html')

def city_suggestions(request):
    import requests
    import os
    from django.http import JsonResponse
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    api_key = os.getenv("API_KEY")
    # Increase limit to 20 to find more regional matches
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=20&appid={api_key}"
    
    try:
        response = requests.get(geo_url, timeout=5)
        data = response.json()
        
        indian_suggestions = []
        other_suggestions = []
        
        for item in data:
            name = item.get('name')
            state = item.get('state')
            country = item.get('country')
            
            location = f"{name}"
            if state:
                location += f", {state}"
            location += f", {country}"
            
            if country == 'IN':
                indian_suggestions.append(location)
            else:
                other_suggestions.append(location)
        
        # Combine results: India first, then the rest
        final_suggestions = indian_suggestions + other_suggestions
        return JsonResponse(final_suggestions[:10], safe=False)
    except Exception:
        return JsonResponse([], safe=False)
