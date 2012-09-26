# Geocode stuff
import settings, json, urllib
from google.appengine.ext import ndb
import logging
import math

BASE_URI = "http://where.yahooapis.com/geocode"

def run_lookup(address):
    context = ndb.get_context()
    return context.urlfetch(get_lookup_uri(address))

def parse_response(response):
    try:
        parsed = json.loads(response.content)
        locs = parsed["ResultSet"]["Results"][0]
        return ndb.GeoPt(locs["latitude"],locs["longitude"])
    except Exception:
        logging.exception("could not get lat_long")
        return None

def address_to_geopoint(addresses):
    '''
    Give me a dictionary with {id:address} and I will give you
    a dictionary of {id:GeoPt}.
    '''
    returner = {}
    context = ndb.get_context()
    futures = {id:run_lookup(addresses[id])
               for id in addresses}

    for id in futures:
        try:
            result = futures[id].get_result()
            parsed = json.loads(result.content)
            locs = parsed["ResultSet"]["Results"][0]
            returner[id] = ndb.GeoPt(locs["latitude"],locs["longitude"])
        except Exception:
            logging.exception("could not get lat_long")

    return returner

def get_lookup_uri(address):
    return "%s?%s"%(BASE_URI, urllib.urlencode({
        "location":address,"country":"UK",
        "appid":settings.GEOCODE_APP_ID,
        "flags":"CJ"
    }))

def distance(point1, point2):
    R = 3956 # Earth Radius in Miles

    lat1, long1 = (point1.lat, point1.lon)
    lat2, long2 = (point2.lat, point2.lon)

    dLat = math.radians(lat2 - lat1) # Convert Degrees 2 Radians
    dLong = math.radians(long2 - long1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.sin(dLong/2) * math.sin(dLong/2) * math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = R * c
    return d