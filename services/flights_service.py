# services/flights_service_simple.py - VERSION COMPLÈTE CORRIGÉE AVEC CALCUL DE DURÉE
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
from config import Config
from .cache_service import get_cached_data, set_cached_data
from .utils import get_airport_code

def search_flights(origin_city: str, dest_city: str, depart_date: str, return_date: Optional[str] = None, max_results: int = 10) -> List[Dict]:
    
    origin_code = get_airport_code(origin_city)
    dest_code = get_airport_code(dest_city)
    try:
        dep_date_obj = datetime.strptime(depart_date, '%Y-%m-%d')
        if return_date:
            ret_date_obj = datetime.strptime(return_date, '%Y-%m-%d')
            if ret_date_obj <= dep_date_obj:
                raise ValueError("La date de retour doit être après la date de départ")
    except ValueError as e:
        print(f"Format de date invalide: {e}")
        raise
    
    cache_key = f"flights_{origin_code}_{dest_code}_{depart_date}_{return_date}"
    
    cached = get_cached_data(cache_key)
    if cached is not None:
        print(f"Données récupérées du cache: {len(cached)} vols")
        return cached
    
    try:
        from serpapi import GoogleSearch
        
        params = {
            "engine": "google_flights",
            "departure_id": origin_code,
            "arrival_id": dest_code,
            "outbound_date": depart_date,
            "currency": "EUR",
            "hl": "fr",
            "api_key": Config.SERP_API_KEY,
            "adults": "1",
            "type": "1"  
        }
        
        if return_date and return_date.strip():
            params["return_date"] = return_date
            print(f"✈️  Recherche de vols ALLER-RETOUR: {origin_code} → {dest_code}")
            print(f"   Dates: {depart_date} → {return_date}")
        else:
            print(f"✈️  Recherche de vol ALLER SIMPLE: {origin_code} → {dest_code}")
            print(f"   Date: {depart_date}")
        
        #
        safe_params = params.copy()
        safe_params['api_key'] = '***' if safe_params.get('api_key') else None
        
        
        # Appel API
        start_time = datetime.now()
        search = GoogleSearch(params)
        results = search.get_dict()
        api_time = (datetime.now() - start_time).total_seconds()
        
        print(f"Temps API: {api_time:.2f}s")
        if "error" in results:
            error_msg = results['error']
            if "return_date" in error_msg and "type" in error_msg:
                print("💡 Astuce: Le paramètre 'type' doit toujours être '1' pour SerpAPI")
                print("   Essayez sans le paramètre 'type' si l'erreur persiste")
            
            raise ValueError(f"SerpAPI Error: {error_msg}")
        
        
        
        # Extraction des vols
        flights = extract_flights_from_response(results, origin_city, dest_city, 
                                                depart_date, return_date, max_results)
        
        if flights:
            # Cache des résultats valides
            set_cached_data(cache_key, flights, ttl=7200)  # 2 heures
            print(f"🎯 {len(flights)} vols réels extraits avec succès")
            
            
            
        return flights
        
    except ImportError:
        print("Module 'serpapi' non installé")
        print(" Installation: pip install google-search-results")
        raise
    except Exception as e:
        print(f" ERREUR CRITIQUE dans search_flights: {str(e)}")
        raise  # SANS FALLBACK - propagation de l'exception

def extract_flights_from_response(results: Dict, origin_city: str, dest_city: str, depart_date: str, return_date: Optional[str],  max_results: int) -> List[Dict]:
    
    flights = []
    flight_sources = [
        results.get("best_flights", []),
        results.get("other_flights", []),
        results.get("cheapest_flights", []),
        results.get("quickest_flights", [])
    ]

    all_flight_data = []
    for source in flight_sources:
        if source and isinstance(source, list):
            all_flight_data.extend(source)
    
    if not all_flight_data:
        print("ℹ️  Aucune donnée de vol trouvée dans la réponse")
        print(f"   Structure disponible: {list(results.keys())}")
        return flights
    
    print(f"📊 Données brutes: {len(all_flight_data)} options de vol trouvées")
    flight_counter = 0
    
    for flight_data in all_flight_data:
        if flight_counter >= max_results:
            break
            
        try:
            outbound_flight = extract_flight_details(
                flight_data, origin_city, dest_city, 
                flight_counter, depart_date, return_date, is_return=False
            )
            
            if outbound_flight:
                flights.append(outbound_flight)
                flight_counter += 1
                if return_date:
                    return_flights = extract_return_flights(flight_data, dest_city, 
                                                          origin_city, depart_date, return_date)
                    for ret_flight in return_flights:
                        if flight_counter < max_results:
                            flights.append(ret_flight)
                            flight_counter += 1
                        else:
                            break
                            
        except Exception as e:
            print(f"⚠️  Ignoré - Erreur extraction vol {flight_counter}: {e}")
            continue
    
    return flights

def extract_flight_details(flight_data: Dict, origin_city: str, dest_city: str, 
                          idx: int, depart_date: str, return_date: Optional[str], 
                          is_return: bool = False) -> Optional[Dict]:
    """
    Extrait les détails complets d'un vol depuis les données SerpAPI
    """
    try:
        # Validation des données essentielles
        flights_list = flight_data.get("flights", [])
        if not flights_list or not isinstance(flights_list, list):
            return None
        
        first_segment = flights_list[0]
        last_segment = flights_list[-1]
        
        # Extraction des informations de base
        airline_info = extract_airline_info(first_segment)
        times_info = extract_times_info(first_segment, last_segment)
        pricing_info = extract_pricing_info(flight_data)
        
        # Déterminer les dates selon le type de vol
        if is_return:
            # Vol retour - date du vol = return_date
            flight_date = return_date if return_date else depart_date
            date_label = "Retour"
        else:
            # Vol aller - date du vol = depart_date
            flight_date = depart_date
            date_label = "Départ"
        
        # 🔥 CALCUL DE LA DURÉE à partir des heures de départ et d'arrivée
        duration_info = calculate_duration_from_times(
            times_info["departure"],  # "15:10"
            times_info["arrival"]     # "19:35"
        )
        
        # Construction de l'objet vol
        flight_id = f"serpapi_{'ret' if is_return else 'out'}_{idx}_{datetime.now().strftime('%H%M%S')}"
        
        flight_details = {
            "id": flight_id,
            "airline": airline_info["name"],
            "airline_code": airline_info["code"],
            "flight_number": first_segment.get("flight_number", "N/A"),
            "departure": {
                "airport": first_segment.get("departure_airport", {}).get("name", origin_city),
                "airport_code": first_segment.get("departure_airport", {}).get("id", ""),
                "city": origin_city,
                "time": times_info["departure"],  # Heure de départ formatée "15:10"
                "date": flight_date,  # Date du vol "2023-10-03"
                "datetime": f"{flight_date}T{times_info['departure']}:00"
            },
            "arrival": {
                "airport": last_segment.get("arrival_airport", {}).get("name", dest_city),
                "airport_code": last_segment.get("arrival_airport", {}).get("id", ""),
                "city": dest_city,
                "time": times_info["arrival"],    # Heure d'arrivée formatée "19:35"
                "date": flight_date,  # Date du vol (même que départ)
                "datetime": f"{flight_date}T{times_info['arrival']}:00"
            },
            "duration": duration_info["formatted"],        # "4h25"
            "duration_minutes": duration_info["minutes"],  # 265
            "duration_hours": duration_info["hours"],      # 4
            "duration_hours_decimal": duration_info["hours_decimal"],  # 4.42
            "stops": len(flights_list) - 1,
            "stop_details": extract_stop_details(flights_list),
            "price": {
                "total": pricing_info["amount"],
                "currency": pricing_info["currency"],
                "display": f"{pricing_info['amount']:.2f}{pricing_info['currency']}",
                "breakdown": flight_data.get("price_breakdown", {})
            },
            "class": flight_data.get("travel_class", "economy").lower(),
            "baggage_allowance": extract_baggage_info(flight_data),
            "booking_link": flight_data.get("booking_link") or 
                           generate_booking_link(origin_city, dest_city, flight_date),
            "dates": {
                "date_depart": depart_date,
                "date_retour": return_date,
                "date_vol": flight_date,
                "label_date": date_label
            },
            "metadata": {
                "source": "SerpAPI",
                "is_return": is_return,
                "extracted_at": datetime.now().isoformat(),
                "data_quality": "real",
                "airline_logo": first_segment.get("airline_logo", ""),
                "deeplink": flight_data.get("flight_deeplink", ""),
                "cabin": flight_data.get("cabin", ""),
                "duration_calculated": True  # Indique que la durée a été calculée
            }
        }
        
        # Validation finale
        if not flight_details["airline"] or not flight_details["departure"]["time"]:
            return None
            
        return flight_details
        
    except Exception as e:
        print(f"⚠️  Erreur détaillée extract_flight_details: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_return_flights(flight_data: Dict, origin_city: str, 
                          dest_city: str, depart_date: str, return_date: str) -> List[Dict]:
    """
    Extrait les vols retour associés
    """
    return_flights = []
    
    try:
        return_flights_data = flight_data.get("return_flights", [])
        if not return_flights_data or not isinstance(return_flights_data, list):
            return return_flights
            
        for idx, ret_data in enumerate(return_flights_data[:2]):  # Max 2 options retour
            ret_flight = extract_flight_details(
                ret_data, origin_city, dest_city, idx, depart_date, return_date, is_return=True
            )
            if ret_flight:
                return_flights.append(ret_flight)
                
    except Exception as e:
        print(f"⚠️  Erreur extraction vols retour: {e}")
        
    return return_flights

def extract_airline_info(segment: Dict) -> Dict:
    """Extrait les informations de la compagnie aérienne"""
    airline = segment.get("airline", {})
    
    if isinstance(airline, dict):
        return {
            "name": airline.get("name", "Airline Inconnue"),
            "code": airline.get("id", "")
        }
    elif isinstance(airline, str):
        match = re.search(r'\(([A-Z0-9]{2})\)', airline)
        code = match.group(1) if match else airline[:2].upper()
        return {"name": airline, "code": code}
    else:
        return {"name": "Airline", "code": "XX"}

def extract_time_from_datetime(datetime_str: str) -> str:
    """
    Extrait uniquement l'heure (HH:MM) d'une chaîne datetime
    Formats supportés: "2023-10-03 15:10", "2023-10-03T15:10:00", "15:10", "15h10", "1510"
    """
    if not datetime_str:
        return "00:00"
    
    datetime_str = str(datetime_str).strip()
    
    # Format avec espace "2023-10-03 15:10" ou "2023-10-03 15:10:00"
    if ' ' in datetime_str:
        parts = datetime_str.split(' ')
        if len(parts) >= 2:
            time_part = parts[1]
            # Extraire HH:MM
            if ':' in time_part:
                time_parts = time_part.split(':')
                if len(time_parts) >= 2:
                    hours = time_parts[0].zfill(2)
                    minutes = time_parts[1][:2].zfill(2)  # Prendre seulement les 2 premiers chiffres
                    return f"{hours}:{minutes}"
    
    # Format ISO "2023-10-03T15:10:00"
    elif 'T' in datetime_str:
        try:
            time_part = datetime_str.split('T')[1]
            if ':' in time_part:
                time_parts = time_part.split(':')
                if len(time_parts) >= 2:
                    hours = time_parts[0].zfill(2)
                    minutes = time_parts[1][:2].zfill(2)
                    return f"{hours}:{minutes}"
        except:
            pass
    
    # Format "15:10"
    elif ':' in datetime_str and len(datetime_str) >= 4:
        parts = datetime_str.split(':')
        if len(parts) >= 2:
            hours = parts[0].zfill(2)
            minutes = parts[1][:2].zfill(2)
            return f"{hours}:{minutes}"
    
    # Format "15h10"
    elif 'h' in datetime_str.lower():
        datetime_str = datetime_str.lower().replace('h', ':')
        parts = datetime_str.split(':')
        if len(parts) >= 2:
            hours = parts[0].zfill(2)
            minutes = parts[1][:2].zfill(2)
            return f"{hours}:{minutes}"
    
    # Format "1510"
    elif len(datetime_str) == 4 and datetime_str.isdigit():
        return f"{datetime_str[:2]}:{datetime_str[2:]}"
    
    # Format "1430" (avec ou sans caractères non numériques)
    else:
        # Extraire tous les chiffres
        numbers = re.findall(r'\d+', datetime_str)
        if numbers:
            digits = ''.join(numbers)
            if len(digits) >= 4:
                return f"{digits[:2]}:{digits[2:4]}"
    
    return "12:00"  # Valeur par défaut

def extract_times_info(first_segment: Dict, last_segment: Dict) -> Dict:
    """Extrait et formate les heures de départ et d'arrivée - VERSION CORRIGÉE"""
    # Extraire les temps bruts des segments
    dep_time_raw = first_segment.get("departure_airport", {}).get("time", "")
    arr_time_raw = last_segment.get("arrival_airport", {}).get("time", "")
    
    # 🔥 UTILISER LA FONCTION pour extraire l'heure
    dep_time = extract_time_from_datetime(dep_time_raw)
    arr_time = extract_time_from_datetime(arr_time_raw)
    
    # Debug
    print(f"DEBUG - Temps départ: '{dep_time_raw}' -> '{dep_time}'")
    print(f"DEBUG - Temps arrivée: '{arr_time_raw}' -> '{arr_time}'")
    
    return {
        "departure": dep_time,  # "15:10"
        "arrival": arr_time,    # "19:35"
        "departure_raw": dep_time_raw,
        "arrival_raw": arr_time_raw
    }

def calculate_duration_from_times(departure_time: str, arrival_time: str) -> Dict:
    
    try:
       
        def time_to_minutes(time_str: str) -> int:
            if not time_str or ':' not in time_str:
                return 0
            
            try:
                parts = time_str.split(':')
                if len(parts) < 2:
                    return 0
                
                # Nettoyer les parties
                hours_str = parts[0].strip()
                minutes_str = parts[1].strip()
                
                # Extraire uniquement les chiffres
                hours_match = re.search(r'\d+', hours_str)
                minutes_match = re.search(r'\d+', minutes_str)
                
                if not hours_match or not minutes_match:
                    return 0
                
                hours = int(hours_match.group())
                minutes = int(minutes_match.group())
                
                # Validation
                if hours < 0 or hours > 23:
                    hours = 0
                if minutes < 0 or minutes > 59:
                    minutes = 0
                
                return hours * 60 + minutes
                
            except Exception as e:
                print(f"⚠️  Erreur conversion temps en minutes: {time_str}, erreur: {e}")
                return 0
        
        # Convertir les heures en minutes
        dep_minutes = time_to_minutes(departure_time)  # Ex: 15:10 → 910 minutes
        arr_minutes = time_to_minutes(arrival_time)    # Ex: 19:35 → 1175 minutes
        
        print(f"DEBUG Calcul durée: {departure_time} → {dep_minutes} min, {arrival_time} → {arr_minutes} min")
        
        # Calculer la différence
        if dep_minutes == 0 or arr_minutes == 0:
            raise ValueError("Heures invalides pour calcul de durée")
        
        duration_minutes = arr_minutes - dep_minutes
        
        # Si la durée est négative, c'est que l'arrivée est le lendemain (vol de nuit)
        if duration_minutes < 0:
            duration_minutes += 24 * 60  # Ajouter 24 heures en minutes
            print(f"DEBUG: Vol de nuit détecté, durée ajustée: {duration_minutes} min")
        
        # Calculer les heures et minutes
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        
        # Formater la durée
        formatted = f"{hours}h{minutes:02d}"
        
        print(f"DEBUG Durée calculée: {formatted} ({duration_minutes} minutes)")
        
        return {
            "minutes": duration_minutes,
            "formatted": formatted,
            "hours": hours,
            "remaining_minutes": minutes,
            "hours_decimal": round(duration_minutes / 60, 2)
        }
        
    except Exception as e:
        print(f"⚠️  Erreur calcul durée: départ={departure_time}, arrivée={arrival_time}, erreur={e}")
        
        # Retourner une durée par défaut
        return {
            "minutes": 150,
            "formatted": "2h30",
            "hours": 2,
            "remaining_minutes": 30,
            "hours_decimal": 2.5
        }

def extract_pricing_info(flight_data: Dict) -> Dict:
    """Extrait et nettoie les informations de prix"""
    price_raw = flight_data.get("price", "0")
    currency = "EUR"
    
    try:
        if isinstance(price_raw, (int, float)):
            amount = float(price_raw)
        else:
            price_str = str(price_raw).replace(',', '.')
            numbers = re.findall(r'[\d]+[.,\d]+|[\d]*[.][\d]+|[\d]+', price_str)
            
            if numbers:
                amount = float(numbers[0].replace(',', '.'))
            else:
                amount = 0.0
            
            if '€' in price_raw or 'EUR' in str(price_raw).upper():
                currency = "EUR"
            elif '$' in price_raw or 'USD' in str(price_raw).upper():
                currency = "USD"
            elif '£' in price_raw or 'GBP' in str(price_raw).upper():
                currency = "GBP"
        
        if amount <= 0 or amount > 10000:
            amount = 300.0
            
    except Exception:
        amount = 300.0
    
    return {"amount": round(amount, 2), "currency": currency}

def extract_stop_details(flights_list: List[Dict]) -> List[Dict]:
    """Extrait les détails des escales"""
    stops = []
    
    if len(flights_list) <= 1:
        return stops
    
    for i in range(1, len(flights_list)):
        segment = flights_list[i]
        departure = segment.get("departure_airport", {})
        
        if departure:
            stop_info = {
                "airport": departure.get("name", ""),
                "airport_code": departure.get("id", ""),
                "city": "",
                "duration": segment.get("layover_duration", "N/A")
            }
            stops.append(stop_info)
    
    return stops

def extract_baggage_info(flight_data: Dict) -> str:
    baggage = flight_data.get("baggage", "")
    
    if baggage:
        return str(baggage)
    
    travel_class = flight_data.get("travel_class", "economy").lower()
    
    if travel_class == "business" or travel_class == "first":
        return "2 bagages cabine + 2×32kg en soute"
    elif travel_class == "premium economy":
        return "2 bagages cabine + 2×23kg en soute"
    else:
        return "1 bagage cabine + 23kg en soute"

def generate_booking_link(origin: str, destination: str, date: str) -> str:
    """Génère un lien de réservation Google Flights"""
    base_url = "https://www.google.com/travel/flights"
    params = f"q={origin}%20to%20{destination}%20on%20{date}"
    return f"{base_url}?{params}"
