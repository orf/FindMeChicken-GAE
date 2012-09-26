from sources import ChickenSource
from models import ChickenPlace
import json
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from google.appengine.api import memcache
from lib import geohash


BASE_URL = "http://www.kfc.co.uk/our-restaurants/search?latitude={0}&longitude={1}&radius=10&storeTypes="

class KFCSource(ChickenSource):
    NAME = "KFC"
    POSTCODE_REQUIRED = False
    LOCATION_REQUIRED = True

    def GetAvailablePlaces(self, postcode=None, location=None):
        encoded = geohash.encode(location.lat, location.lon, precision=10)

        result = memcache.get(encoded, namespace=self.NAME)
        if result is None:
            result = json.loads(urlfetch.fetch(BASE_URL.format(location.lat,
                                                               location.lon)).content)
            memcache.set(encoded, result, namespace=self.NAME)

        places = []

        for place in result:
            chicken_place = ChickenPlace()
            chicken_place.title = place["storeName"]
            chicken_place.address = "%s %s %s %s"%(place["address1"],
                                                   place["address2"],
                                                   place["address3"],
                                                   place["postcode"])
            chicken_place.location = ndb.GeoPt(place["latitude"],
                                               place["longitude"])
            places.append(chicken_place)

        return places


    def MenusAvailable(self):
        return False