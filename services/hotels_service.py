# services/hotels_service.py
from datetime import datetime, timedelta
from .cache_service import get_cached_data, set_cached_data
from .api_fetcher import get_city_coordinates, get_country_code_for_city, FIXED_HOTEL_IMAGE

def search_hotels(city_name, checkin_date=None, checkout_date=None):
    if not checkin_date:
        checkin_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if not checkout_date:
        checkout_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    cache_key = f"hotels_{city_name}_{checkin_date}_{checkout_date}"
    
    cached_data = get_cached_data(cache_key)
    if cached_data is not None:
        return cached_data
    
    hotels = search_hotels_serpapi(city_name, checkin_date, checkout_date)
    
    if hotels:
        return set_cached_data(cache_key, hotels)
    else:
        return []

def search_hotels_serpapi(city_name, checkin_date, checkout_date):
    try:
        from serpapi import GoogleSearch
        from config import Config
    except ImportError:
        return []
    
    if not hasattr(Config, 'SERP_API_KEY') or not Config.SERP_API_KEY:
        return []
    
    try:
        country_code = get_country_code_for_city(city_name)
        
        params = {
            "engine": "google_hotels",
            "q": f"hotels in {city_name}",
            "check_in_date": checkin_date,
            "check_out_date": checkout_date,
            "adults": "2",
            "currency": "EUR",
            "gl": country_code,
            "hl": "fr",
            "api_key": Config.SERP_API_KEY
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        if "error" in results:
            return []
        
        hotels = _parse_serpapi_hotel_results(results, city_name, checkin_date, checkout_date)
        
        return hotels
        
    except Exception:
        return []

def _parse_serpapi_hotel_results(results, city_name, checkin_date, checkout_date):
    hotels = []
    
    try:
        properties = results.get("properties", [])
        if not properties:
            return []
        
        for prop in properties[:10]:
            try:
                hotel = _extract_hotel_details(prop, city_name, checkin_date, checkout_date)
                if hotel:
                    hotels.append(hotel)
            except Exception:
                continue
        
        return hotels
        
    except Exception:
        return []

def _extract_hotel_details(prop, city_name, checkin_date, checkout_date):
    try:
        name = prop.get("name", "").strip()
        if not name:
            return None
        
        address = prop.get("address", "")
        if not address:
            address = prop.get("location", "")
        
        rating = prop.get("total_score", 0)
        if not rating:
            rating = prop.get("rating", 0)
        
        reviews = prop.get("reviews", 0)
        if isinstance(reviews, str):
            try:
                reviews = int(reviews.replace(',', '').split()[0])
            except:
                reviews = 0
        
        price = 0
        price_data = prop.get("rate_per_night", {})
        if isinstance(price_data, dict):
            price = price_data.get("lowest", 0)
            if not price:
                price = price_data.get("rate", 0)
        
        if price == 0:
            price_data = prop.get("price", {})
            if isinstance(price_data, dict):
                price = price_data.get("low", 0)
        
        stars = prop.get("stars", 0)
        
        lat, lon = get_city_coordinates(city_name)
        
        photo_url = FIXED_HOTEL_IMAGE
        photos = prop.get("photos", [])
        if photos and isinstance(photos, list) and len(photos) > 0:
            first_photo = photos[0]
            if isinstance(first_photo, dict):
                photo_url = first_photo.get("thumbnail", first_photo.get("image", FIXED_HOTEL_IMAGE))
            elif isinstance(first_photo, str):
                photo_url = first_photo
        
        website = prop.get("link", "")
        if not website:
            website = prop.get("website", "")
        
        phone = prop.get("phone", "")
        
        hotel_data = {
            "id": f"hotel_{hash(name) % 1000000}",
            "name": name,
            "address": address if address else f"{city_name}",
            "rating": float(rating),
            "reviews": reviews,
            "price": price if price else 100,
            "currency": "EUR",
            "stars": stars if stars else 3,
            "photo": photo_url,
            "website": website,
            "phone": phone,
            "latitude": lat,
            "longitude": lon,
            "checkin": "14:00",
            "checkout": "12:00",
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "source": "serpapi",
            "amenities": ["WiFi gratuit", "Petit-déjeuner", "Salle de bain privée"],
            "description": f"Hôtel {name} situé à {city_name}"
        }
        
        return hotel_data
        
    except Exception:
        return None