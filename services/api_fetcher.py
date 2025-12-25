import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from .cache_service import get_cached_data, set_cached_data
import threading


api_semaphore = threading.Semaphore(6)

# Images fixes
FIXED_HOTEL_IMAGE = "https://images.unsplash.com/photo-1566073771259-6a8506099945?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&h=600&q=80"
FIXED_RESTAURANT_IMAGE = "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&h=600&q=80"
FIXED_ACTIVITY_IMAGE = "https://images.unsplash.com/photo-1540541338287-41700207dee6?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&h=600&q=80"
FIXED_CITY_IMAGE = "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&h=600&q=80"

def get_city_coordinates(city_name: str):
    cache_key = f"coords_{city_name.lower().replace(' ', '_')}"
    
    cached_data = get_cached_data(cache_key)
    if cached_data:
        return cached_data
    
    known_coords = {
        'paris': (48.8566, 2.3522), 'tunis': (36.8065, 10.1815),
        'london': (51.5074, -0.1278), 'new york': (40.7128, -74.0060),
        'tokyo': (35.6762, 139.6503), 'dubai': (25.2048, 55.2708),
        'rome': (41.9028, 12.4964), 'madrid': (40.4168, -3.7038),
        'marseille': (43.2965, 5.3698), 'lyon': (45.7640, 4.8357),
        'nice': (43.7102, 7.2620), 'berlin': (52.5200, 13.4050),
        'amsterdam': (52.3676, 4.9041), 'barcelona': (41.3851, 2.1734),
        'lisbon': (38.7223, -9.1393), 'prague': (50.0755, 14.4378),
        'vienna': (48.2082, 16.3738), 'athens': (37.9838, 23.7275),
        'istanbul': (41.0082, 28.9784), 'cairo': (30.0444, 31.2357),
        'doha': (25.2854, 51.5310), 'singapore': (1.3521, 103.8198),
        'sydney': (-33.8688, 151.2093), 'melbourne': (-37.8136, 144.9631),
        'montreal': (45.5017, -73.5673), 'toronto': (43.6532, -79.3832),
        'vancouver': (49.2827, -123.1207)
    }
    
    city_lower = city_name.lower().strip()
    
    for city_key, coords in known_coords.items():
        if city_key in city_lower or city_lower in city_key:
            set_cached_data(cache_key, coords, ttl=86400)
            return coords
    
    try:
        with api_semaphore:
            url = f"https://nominatim.openstreetmap.org/search"
            params = {'q': city_name, 'format': 'json', 'limit': 1}
            headers = {'User-Agent': 'TravelPlannerApp/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code == 200 and response.json():
                data = response.json()[0]
                lat = float(data['lat'])
                lon = float(data['lon'])
                coords = (lat, lon)
                set_cached_data(cache_key, coords, ttl=86400)
                return coords
        
        coords = (48.8566, 2.3522)
        set_cached_data(cache_key, coords, ttl=3600)
        return coords
        
    except Exception:
        coords = (48.8566, 2.3522)
        set_cached_data(cache_key, coords, ttl=3600)
        return coords

def get_country_code_for_city(city_name):
    city_country_mapping = {
        'paris': 'fr', 'lyon': 'fr', 'marseille': 'fr', 'nice': 'fr', 'lille': 'fr',
        'tunis': 'tn', 'sousse': 'tn', 'hammamet': 'tn',
        'london': 'gb', 'manchester': 'gb', 'birmingham': 'gb',
        'new york': 'us', 'los angeles': 'us', 'chicago': 'us', 'miami': 'us',
        'madrid': 'es', 'barcelona': 'es', 'valencia': 'es',
        'rome': 'it', 'milan': 'it', 'venice': 'it',
        'berlin': 'de', 'munich': 'de', 'hamburg': 'de',
        'amsterdam': 'nl', 'rotterdam': 'nl',
        'dubai': 'ae', 'abu dhabi': 'ae',
        'tokyo': 'jp', 'osaka': 'jp',
        'singapore': 'sg',
        'montreal': 'ca', 'toronto': 'ca', 'vancouver': 'ca',
        'sydney': 'au', 'melbourne': 'au'
    }
    
    city_lower = city_name.lower()
    for city_key, country_code in city_country_mapping.items():
        if city_key in city_lower or city_lower in city_key:
            return country_code
    
    return 'fr'

def fetch_api_with_semaphore(url, params=None, headers=None, timeout=10):
    with api_semaphore:
        return requests.get(url, params=params, headers=headers, timeout=timeout)

def fetch_all_data_concurrent(preferences):
    from .weather_service import get_weather
    from .flights_service import search_flights
    from .hotels_service import search_hotels
    from .restaurants_service import search_restaurants
    from .activities_service import search_activities
    
    origin = preferences.get("origin", "TUN")
    destination = preferences.get("destination")
    depart_date = preferences.get("depart_date")
    return_date = preferences.get("return_date")
    
    if not destination:
        return {}
    
    results = {}
    
    def fetch_weather():
        try:
            return get_weather(destination, depart_date, return_date)
        except Exception as e:
            print("Erreur météo pour {destination}: {e}")
            return {}
    
    def fetch_flights():
        try:
            return search_flights(origin, destination, depart_date, return_date)
        except Exception as e:
            print("Erreur vols pour {origin}→{destination}: {e}")
            return []
    
    def fetch_hotels():
        try:
            checkin = depart_date 
            checkout = return_date
            return search_hotels(destination, checkin, checkout)
        except Exception as e:
            print("Erreur hôtels pour {destination}: {e}")
            return []
    
    def fetch_restaurants():
        try:
            return search_restaurants(destination)
        except Exception as e:
            print("Erreur restaurants pour {destination}: {e}")
            return []
    
    def fetch_activities():
        try:
             return search_activities(destination)
        except Exception as e:
            print("Erreur activités pour {destination}: {e}")
            return []
    
    #n7esb temps d'exutions
    start_time = datetime.now()
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_key = {
            executor.submit(fetch_weather): "weather",
            executor.submit(fetch_flights): "flights", 
            executor.submit(fetch_hotels): "hotels",
            executor.submit(fetch_restaurants): "restaurants",
            executor.submit(fetch_activities): "activities"
        }
        
       #n7esb compteur pour le suivi
        completed = 0
        total = len(future_to_key)
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            completed += 1
            
            try:
                results[key] = future.result(timeout=30)  # Timeout 30s
            except Exception as e:
                print("Erreur API")
    
    
    time_api = (datetime.now() - start_time).total_seconds()
    print(f"Temps total API pour {destination}: {time_api:.2f}s")
    
    return ensure_results_complete(results, preferences)

def ensure_results_complete(results, preferences):
    required_keys = ["weather", "flights", "hotels", "restaurants", "activities"]
    
    for key in required_keys:
        if key not in results:
            results[key] = [] 
    return results