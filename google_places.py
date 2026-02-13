import requests
import json
import os

def search_nearby_places(query, lat, lon, radius=2000):
    """
    Busca lugares cercanos usando Google Places API.
    lat, lon: Coordenadas del usuario.
    query: Lo que buscas (ej: 'supermercado', 'farmacia').
    radius: Radio en metros (default 2km).
    """
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        return "⚠️ Error: Falta la GOOGLE_MAPS_API_KEY en Render."

    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    
    # Si tenemos ubicación, priorizamos cercanía
    location = f"{lat},{lon}"
    
    params = {
        'query': query,
        'location': location,
        'radius': radius,
        'language': 'es',
        'key': api_key
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') != 'OK':
            return f"No encontré lugares. Estado: {data.get('status')}"

        results = data.get('results', [])[:5] # Tomamos los 5 mejores
        
        output = f"📍 **Lugares encontrados cerca de ti ({query}):**\n"
        for place in results:
            name = place.get('name')
            addr = place.get('formatted_address')
            rating = place.get('rating', 'N/A')
            open_now = place.get('opening_hours', {}).get('open_now')
            status = "🟢 Abierto" if open_now else "🔴 Cerrado" if open_now is False else "🕒 Horario no disponible"
            
            output += f"\n🏢 **{name}** ({rating}⭐)\n   └ {addr}\n   └ {status}\n"
            
        return output

    except Exception as e:
        return f"Error en Google Places: {str(e)}"
