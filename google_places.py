"""
Google Places Service para Claudette Bot.
Buscar restaurantes, ferreterías, tiendas y lugares cercanos.
"""

import os
import logging
import requests

logger = logging.getLogger(__name__)

# Google Places API
PLACES_API_KEY = os.environ.get('GOOGLE_PLACES_API_KEY')

def search_nearby_places(query: str, latitude: float, longitude: float, radius: int = 2000) -> dict:
    """
    Search for places near a location.
    
    Args:
        query: What to search for (e.g., "restaurante", "ferretería", "farmacia")
        latitude: User's latitude
        longitude: User's longitude
        radius: Search radius in meters (default 2000m = 2km)
    
    Returns:
        dict with 'success', 'places' array, and 'error' if any
    """
    if not PLACES_API_KEY:
        return {"success": False, "error": "Google Places API key not configured."}
    
    try:
        # Use Places API Text Search
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        
        params = {
            "query": query,
            "location": f"{latitude},{longitude}",
            "radius": radius,
            "key": PLACES_API_KEY,
            "language": "es"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") != "OK":
            if data.get("status") == "ZERO_RESULTS":
                return {"success": True, "places": [], "message": f"No encontré '{query}' cerca de tu ubicación."}
            return {"success": False, "error": f"API Error: {data.get('status')}"}
        
        places = []
        for place in data.get("results", [])[:5]:  # Top 5 results
            place_info = {
                "name": place.get("name"),
                "address": place.get("formatted_address", ""),
                "rating": place.get("rating", "N/A"),
                "total_ratings": place.get("user_ratings_total", 0),
                "open_now": place.get("opening_hours", {}).get("open_now", None),
                "place_id": place.get("place_id"),
                "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                "lng": place.get("geometry", {}).get("location", {}).get("lng")
            }
            
            # Build Google Maps link
            place_info["maps_link"] = f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}"
            
            # Build directions link
            place_info["directions_link"] = f"https://www.google.com/maps/dir/?api=1&destination={place_info['lat']},{place_info['lng']}"
            
            places.append(place_info)
        
        return {"success": True, "places": places, "count": len(places)}
    
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Timeout conectando a Google Places."}
    except Exception as e:
        logger.error(f"Error searching places: {e}")
        return {"success": False, "error": f"Error: {str(e)}"}

def get_place_details(place_id: str) -> dict:
    """
    Get detailed information about a place.
    
    Args:
        place_id: Google Place ID
    
    Returns:
        dict with place details
    """
    if not PLACES_API_KEY:
        return {"success": False, "error": "Google Places API key not configured."}
    
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        
        params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,opening_hours,website,rating,reviews,price_level",
            "key": PLACES_API_KEY,
            "language": "es"
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") != "OK":
            return {"success": False, "error": f"API Error: {data.get('status')}"}
        
        result = data.get("result", {})
        
        # Format opening hours
        hours_text = "No disponible"
        if result.get("opening_hours"):
            hours = result["opening_hours"].get("weekday_text", [])
            if hours:
                hours_text = "\n".join(hours)
        
        return {
            "success": True,
            "name": result.get("name"),
            "address": result.get("formatted_address"),
            "phone": result.get("formatted_phone_number"),
            "website": result.get("website"),
            "rating": result.get("rating"),
            "price_level": "💰" * result.get("price_level", 0) if result.get("price_level") else "N/A",
            "hours": hours_text
        }
    
    except Exception as e:
        logger.error(f"Error getting place details: {e}")
        return {"success": False, "error": f"Error: {str(e)}"}

def format_places_response(places: list) -> str:
    """Format places list for display."""
    if not places:
        return "No encontré lugares cercanos."
    
    text = f"📍 Encontré {len(places)} opciones:\n\n"
    
    for i, place in enumerate(places, 1):
        # Rating stars
        rating = place.get('rating', 'N/A')
        if isinstance(rating, (int, float)):
            stars = "⭐" * int(rating)
            rating_text = f"{rating} {stars}"
        else:
            rating_text = "Sin calificación"
        
        # Open status
        open_status = ""
        if place.get('open_now') is True:
            open_status = "🟢 Abierto"
        elif place.get('open_now') is False:
            open_status = "🔴 Cerrado"
        
        text += f"**{i}. {place['name']}**\n"
        text += f"   📍 {place['address']}\n"
        text += f"   {rating_text} ({place.get('total_ratings', 0)} reseñas)\n"
        if open_status:
            text += f"   {open_status}\n"
        text += f"   🗺️ [Ver en Maps]({place['maps_link']})\n"
        text += f"   🚗 [Cómo llegar]({place['directions_link']})\n\n"
    
    return text
