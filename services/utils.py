# services/utils.py
def get_airport_code(city_name: str):
    codes = {
        'paris': 'CDG', 'tunis': 'TUN', 'london': 'LHR',
        'new york': 'JFK', 'rome': 'FCO', 'madrid': 'MAD',
        'berlin': 'BER', 'amsterdam': 'AMS', 'dubai': 'DXB',
        'tokyo': 'HND', 'marseille': 'MRS', 'lyon': 'LYS',
        'algiers': 'ALG', 'alger': 'ALG', 'algerie': 'ALG',
        'casablanca': 'CMN', 'rabat': 'RBA', 'marrakech': 'RAK',
        'nice': 'NCE', 'toulouse': 'TLS', 'bordeaux': 'BOD',
        'nantes': 'NTE', 'strasbourg': 'SXB', 'lille': 'LIL',
        'geneva': 'GVA', 'zurich': 'ZRH', 'milan': 'MXP',
        'barcelona': 'BCN', 'lisbon': 'LIS', 'dublin': 'DUB',
        'brussels': 'BRU', 'vienna': 'VIE', 'prague': 'PRG',
        'budapest': 'BUD', 'warsaw': 'WAW', 'copenhagen': 'CPH',
        'stockholm': 'ARN', 'oslo': 'OSL', 'helsinki': 'HEL',
        'athens': 'ATH', 'istanbul': 'IST', 'cairo': 'CAI',
        'beirut': 'BEY', 'doha': 'DOH', 'abu dhabi': 'AUH',
        'singapore': 'SIN', 'bangkok': 'BKK', 'hong kong': 'HKG',
        'seoul': 'ICN', 'beijing': 'PEK', 'shanghai': 'PVG',
        'sydney': 'SYD', 'melbourne': 'MEL', 'auckland': 'AKL',
        'toronto': 'YYZ', 'montreal': 'YUL', 'vancouver': 'YVR',
        'chicago': 'ORD', 'los angeles': 'LAX', 'miami': 'MIA',
        'san francisco': 'SFO', 'houston': 'IAH',
        'munich': 'MUC', 'frankfurt': 'FRA', 'hamburg': 'HAM',
        'manchester': 'MAN', 'birmingham': 'BHX', 'glasgow': 'GLA',
        'edinburgh': 'EDI', 'valencia': 'VLC', 'seville': 'SVQ',
        'porto': 'OPO', 'osaka': 'KIX', 'nagoya': 'NGO',
        'guangzhou': 'CAN', 'shenzhen': 'SZX', 'chengdu': 'CTU',
        'moscow': 'SVO', 'mumbai': 'BOM', 'delhi': 'DEL',
        'bangalore': 'BLR', 'jakarta': 'CGK', 'bali': 'DPS',
        'manila': 'MNL', 'kuala lumpur': 'KUL', 'ho chi minh': 'SGN',
        'hanoi': 'HAN', 'dallas': 'DFW', 'atlanta': 'ATL',
        'las vegas': 'LAS', 'denver': 'DEN', 'orlando': 'MCO',
        'seattle': 'SEA', 'boston': 'BOS', 'washington': 'IAD',
        'portland': 'PDX', 'san diego': 'SAN', 'austin': 'AUS',
        'san juan': 'SJU', 'punta cana': 'PUJ', 'cancun': 'CUN',
        'mexico city': 'MEX', 'lima': 'LIM', 'santiago': 'SCL',
        'buenos aires': 'EZE', 'sao paulo': 'GRU', 'rio de janeiro': 'GIG',
        'bogota': 'BOG', 'cape town': 'CPT', 'johannesburg': 'JNB',
        'nairobi': 'NBO', 'accra': 'ACC', 'lagos': 'LOS',
        'oran': 'ORN', 'annaba': 'AAE', 'constantine': 'CZL',
        'sousse': 'SUS', 'sfax': 'SFA', 'djerba': 'DJE',
        'agadir': 'AGA', 'fes': 'FEZ', 'tangier': 'TNG',
        'alexandria': 'HBE', 'sharm el sheikh': 'SSH',
        'hurghada': 'HRG', 'luxor': 'LXR', 'riyadh': 'RUH',
        'jeddah': 'JED', 'dammam': 'DMM', 'medina': 'MED',
        'sharjah': 'SHJ', 'muscat': 'MCT', 'salalah': 'SLL',
        'bahrain': 'BAH', 'amman': 'AMM', 'aqaba': 'AQJ',
        'damascus': 'DAM', 'aleppo': 'ALP', 'baghdad': 'BGW',
        'basra': 'BSR', 'sanaa': 'SAH', 'tripoli': 'TIP',
        'benghazi': 'BEN', 'khartoum': 'KRT', 'nouakchott': 'NKC',
        'mogadishu': 'MGQ', 'djibouti': 'JIB', 'moroni': 'HAH'
    }
    
    city_lower = city_name.lower().strip()
    
    for city_key, code in codes.items():
        if city_key == city_lower or city_lower in city_key:
            return code
    
    return city_name[:3].upper()