import requests
import json
import os
import logging

logger = logging.getLogger(__name__)

def search_nearby_places(query, lat, lon, radius=2000):
    """
    Busca lugares cercanos usando Google Places API.
    lat, lon: Coordenadas del usuario.
    query: Lo que buscas (ej: 'supermercado', 'farmacia').
    radius: Radio en metros (default 2km).
    """
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        logger.error("âŒ GOOGLE_MAPS_API_KEY no estÃ¡ configurada")
        return "âš ï¸ Error: Falta la GOOGLE_MAPS_API_KEY en Render."
    
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    location = f"{lat},{lon}"
    
    params = {
        'query': query,
        'location': location,
        'radius': radius,
        'language': 'es',
        'key': api_key
    }
    
    try:
        logger.info(f"ðŸ” Places API: query='{query}', location={location}, radius={radius}")
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        status = data.get('status')
        logger.info(f"ðŸ” Places API status: {status}")
        
        # --- DIAGNÃ“STICO DETALLADO ---
        if status == 'REQUEST_DENIED':
            error_msg = data.get('error_message', 'Sin detalle')
            logger.error(f"âŒ Places API DENIED: {error_msg}")
            return f"âš ï¸ API Places denegada: {error_msg}"
        
        if status == 'INVALID_REQUEST':
            error_msg = data.get('error_message', 'Sin detalle')
            logger.error(f"âŒ Places API INVALID: {error_msg}")
            return f"âš ï¸ Request invÃ¡lido: {error_msg}"
        
        if status == 'OVER_QUERY_LIMIT':
            logger.error("âŒ Places API: Cuota agotada")
            return "âš ï¸ Cuota de Google Places agotada."
            
        if status == 'ZERO_RESULTS':
            return f"No encontrÃ© '{query}' en un radio de {radius}m. Intenta ampliar la bÃºsqueda."
            
        if status != 'OK':
            logger.error(f"âŒ Places API status inesperado: {status}")
            return f"âš ï¸ Google Places respondiÃ³: {status}"
        
        results = data.get('results', [])[:5]
        
        if not results:
            return f"No encontrÃ© resultados para '{query}' cerca de ti."
        
        output = f"ðŸ“ Lugares encontrados cerca de ti ({query}):\n"
        for place in results:
            name = place.get('name')
            addr = place.get('formatted_address', 'Sin direcciÃ³n')
            rating = place.get('rating', 'N/A')
            open_now = place.get('opening_hours', {}).get('open_now')
            status_str = "ðŸŸ¢ Abierto" if open_now else "ðŸ”´ Cerrado" if open_now is False else "ðŸ•’ Horario no disponible"
            
            # Google Maps link
            place_lat = place.get('geometry', {}).get('location', {}).get('lat', '')
            place_lng = place.get('geometry', {}).get('location', {}).get('lng', '')
            maps_link = f"https://www.google.com/maps/search/?api=1&query={place_lat},{place_lng}" if place_lat else ""
            
            output += f"\nðŸ¢ {name} ({rating}â­)\n   ðŸ“ {addr}\n   {status_str}\n"
            if maps_link:
                output += f"   ðŸ—ºï¸ {maps_link}\n"
            
        return output
        
    except requests.exceptions.Timeout:
        logger.error("âŒ Places API: Timeout")
        return "âš ï¸ Google Places tardÃ³ demasiado en responder."
    except requests.exceptions.ConnectionError:
        logger.error("âŒ Places API: Error de conexiÃ³n")
        return "âš ï¸ No se pudo conectar a Google Places."
    except Exception as e:
        logger.error(f"âŒ Places API exception: {type(e).__name__}: {e}")
        return f"Error en Google Places: {str(e)}"
