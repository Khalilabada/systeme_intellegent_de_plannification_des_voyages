# services/restaurants_service.py - VERSION SIMPLIFIÉE ET CORRIGÉE
import random
from config import Config
from .cache_service import get_cached_data, set_cached_data
from .api_fetcher import get_city_coordinates

FIXED_RESTAURANT_IMAGE = "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&h=600&q=80"

def search_restaurants(city_name):
    cache_key = f"restaurants_{city_name.lower().replace(' ', '_')}"
    cached = get_cached_data(cache_key)
    if cached is not None:
        return cached
    location = normalize_city_for_serpapi(city_name)
    if hasattr(Config, 'SERP_API_KEY') and Config.SERP_API_KEY:
        try:
            from serpapi import GoogleSearch
            
            params = {
                "engine": "google_local",
                "q": f"restaurants {location}",
                "location": location,
                "hl": "fr",
                "gl": get_country_code(city_name),
                "type": "search",
                "num": 10,
                "api_key": Config.SERP_API_KEY
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "error" not in results:
                restaurants = parse_serpapi_results(results, city_name)
                if restaurants:
                    set_cached_data(cache_key, restaurants, ttl=3600)
                    return restaurants
            
        except Exception as e:
            print(f"Erreur SerpAPI: {e}")
    
   
    set_cached_data(cache_key, restaurants, ttl=3600)
    
    return restaurants

def normalize_city_for_serpapi(city_name):
    mapping = {
        'algerie': 'Algiers, Algeria',
        'algérie': 'Algiers, Algeria',
        'alger': 'Algiers, Algeria',
        'tunisie': 'Tunis, Tunisia',
        'tunis': 'Tunis, Tunisia',
        'maroc': 'Casablanca, Morocco',
        'morocco': 'Casablanca, Morocco',
        'france': 'Paris, France',
        'paris': 'Paris, France',
        'espagne': 'Madrid, Spain',
        'spain': 'Madrid, Spain',
        'italie': 'Rome, Italy',
        'italy': 'Rome, Italy',
        'angleterre': 'London, England',
        'england': 'London, England'
    }
    
    city_lower = city_name.lower().strip()
    for key, value in mapping.items():
        if key in city_lower:
            return value
    
    return city_name

def get_country_code(city_name):
    city_lower = city_name.lower()
    
    if any(c in city_lower for c in ['paris', 'lyon', 'marseille', 'france']):
        return 'fr'
    elif any(c in city_lower for c in ['tunis', 'tunisie']):
        return 'tn'
    elif any(c in city_lower for c in ['alger', 'algérie', 'algerie']):
        return 'dz'
    elif any(c in city_lower for c in ['casablanca', 'maroc', 'morocco']):
        return 'ma'
    elif any(c in city_lower for c in ['madrid', 'espagne', 'spain']):
        return 'es'
    elif any(c in city_lower for c in ['rome', 'italie', 'italy']):
        return 'it'
    elif any(c in city_lower for c in ['london', 'angleterre', 'england']):
        return 'gb'
    else:
        return 'fr'

def parse_serpapi_results(results, city_name):
    restaurants = []
    local_results = results.get("local_results", [])
    if not local_results:
        local_results = results.get("organic_results", [])
    
    for result in local_results[:10]:
        try:
            name = result.get("title", "").strip()
            if not name:
                continue
            address = result.get("address", city_name)
            rating = float(result.get("rating", 0)) or round(random.uniform(3.5, 4.8), 1)
            reviews = int(result.get("reviews", 0)) or random.randint(10, 500)
            price = result.get("price", "€€")
            description = result.get("description", "")
            cuisine = extract_cuisine(description, name)
            
            # Photo
            photo = FIXED_RESTAURANT_IMAGE
            photos = result.get("photos", [])
            if photos and isinstance(photos, list) and len(photos) > 0:
                first_photo = photos[0]
                if isinstance(first_photo, dict):
                    photo = first_photo.get("image", FIXED_RESTAURANT_IMAGE)
                elif isinstance(first_photo, str):
                    photo = first_photo
            
            restaurant = {
                "name": name,
                "rating": rating,
                "reviews": reviews,
                "cuisine": cuisine[:3],
                "price": price,
                "address": address,
                "photo": photo,
                "phone": result.get("phone", ""),
                "website": result.get("website", ""),
                "hours": result.get("hours", "Ouvert aujourd'hui"),
                "description": description[:100] + "..." if len(description) > 100 else description,
                "source": "serpapi"
            }
            
            restaurants.append(restaurant)
            
        except Exception as e:
            print(f"⚠️  Erreur parsing restaurant: {e}")
            continue
    
    return restaurants

def extract_cuisine(description, name):
    """Extraire le type de cuisine simplement"""
    text = f"{name} {description}".lower()
    
    cuisine_keywords = {
        'française': ['française', 'french', 'bistrot', 'brasserie'],
        'italienne': ['italienne', 'italian', 'pizza', 'pasta'],
        'asiatique': ['asiatique', 'chinoise', 'japonaise', 'sushi', 'thaï'],
        'tunisienne': ['tunisienne', 'couscous', 'tajine'],
        'algérienne': ['algérienne', 'couscous', 'tajine'],
        'marocaine': ['marocaine', 'couscous', 'tajine'],
        'libanaise': ['libanaise', 'shawarma', 'falafel'],
        'mexicaine': ['mexicaine', 'tacos', 'burrito'],
        'burger': ['burger', 'hamburger'],
        'pizzeria': ['pizzeria', 'pizza'],
        'crêperie': ['crêperie', 'crêpe'],
        'kebab': ['kebab', 'doner'],
        'vegan': ['vegan', 'végétarien']
    }
    
    cuisines = []
    for cuisine_type, keywords in cuisine_keywords.items():
        if any(keyword in text for keyword in keywords):
            cuisines.append(cuisine_type)
    
    return cuisines[:3] if cuisines else ['International']

