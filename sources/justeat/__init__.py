# JustEat handler
from sources import ChickenSource
from google.appengine.api import urlfetch
from models import ChickenPlace
from lib import BeautifulSoup, geocode
from google.appengine.ext import ndb
from google.appengine.api import memcache
import logging
import datetime

IOS_USER_AGENT = "Mozilla/5.0 (iPhone; U; CPU iPhone OS 4_3_2 like Mac OS X; en-us) " \
                 "AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8H7 " \
                 "Safari/6533.18.5"
HOST = "http://www.just-eat.co.uk"
BASE_URL = HOST + "/area/{0}" #/american

class JustEatSource(ChickenSource):

    NAME = "JustEat"
    POSTCODE_REQUIRED = True
    LOCATION_REQUIRED = False

    def GetAvailablePlaces(self, postcode=None, location=None):
        places = memcache.get(postcode, namespace=self.NAME)

        if places is None:
            result = urlfetch.fetch(BASE_URL.format(postcode),
                            headers={"User-Agent":IOS_USER_AGENT})
            parser = BeautifulSoup.BeautifulSoup(result.content)
            open_places_tag = parser.find(id="OpenRestaurants")
            places = {}

            for place_root_tag in open_places_tag.findAll("li"):
                place = {"title":place_root_tag.find("h2").text}
                place["identifier"] = place_root_tag.find("a")["href"]
                places[place_root_tag["data-restaurantid"]] = place

            # Cache for 20 minutes if we have some places, else
            # cache an empty result for 5 minutes.
            memcache.set(postcode, places,
                namespace=self.NAME, time=(60*5, 60*20)[len(places) != 0])

        database_places = self.getPlacesFromDataStore(places.keys())
        database_place_ids = set(database_places.keys())

        places_that_dont_exist = set(places.keys()).difference(database_place_ids)

        if places_that_dont_exist:
            # To fetch the location we don't use the iOS user-agent as the address isn't
            # included in the response.

            created_places = {}

            futures = {id:self.CreateChickenPlace(id, places[id])
                       for id in places_that_dont_exist}

            for id in futures:
                try:
                    created_places[id] = futures[id].get_result()
                    # Run the geo lookup as soon as the chicken place is created
                    created_places[id]._loc_future = geocode.run_lookup(created_places[id].address)
                except Exception:
                    logging.exception("could not get ID")

            for res in created_places:
                # Loop through all geo responses and set the location
                geo_lookup_response = created_places[res]._loc_future.get_result()
                created_places[res].location = geocode.parse_response(geo_lookup_response)

            """for id,geopt in geocode.address_to_geopoint({id:item.address
                                                         for id,item in created_places.items()
                                                        }).items():
                created_places[id].location = geopt"""

            ndb.put_multi(created_places.values())
            database_places.update({id:created_places[id]
                                    for id in created_places
                                    if created_places[id].has_chicken})

        return database_places.values()


    @ndb.tasklet
    def CreateChickenPlace(self, id, place_info):
        ctx = ndb.get_context()
        menu_page = yield ctx.urlfetch(HOST + place_info["identifier"])
        if not menu_page.status_code == 200:
            raise ndb.Return(None)

        parser = BeautifulSoup.BeautifulSoup(menu_page.content)
        address_1 = parser.find(id="ctl00_ContentPlaceHolder1_RestInfo_lblRestAddress").text
        address_2 = parser.find(id="ctl00_ContentPlaceHolder1_RestInfo_lblRestZip").text

        address = "%s, %s"%(address_1, " ".join(address_2.split()))

        place = ChickenPlace()
        place.key = ndb.Key(ChickenPlace, id, namespace=self.NAME)
        place.has_chicken = False
        # Check if they actually serve chicken:
        for tag in parser.findAll("h2", attrs={"class":"H2MC"}):
            if "chicken" in tag.text.lower():
                place.has_chicken = True

        if place.has_chicken:
            # If they don't serve chicken then don't save any of their info. Fuck them.
            place.identifier = place_info["identifier"]
            place.title = place_info["title"]
            place.address = address

        raise ndb.Return(place)

    def MenusAvailable(self):
        return True

    def GetMenu(self, place):
        if len(place.menu) and place.MenuIsFresh():
            return place.menu

        # Fetch the menu
        result = urlfetch.fetch(HOST + place.identifier,
                                headers={"User-Agent":IOS_USER_AGENT})
        parser = BeautifulSoup.BeautifulSoup(result.content)
        for category in parser.findAll("li", attrs={"class":"cat"}):
            header = category.find("h2").text
            if "fried chicken" in header.lower():
                for product in category.findAll("li"):
                    title = product.find("h3").text
                    price = product.find("span").text
                    place.menu.append("%s|%s"%(title,price))
                    logging.info(title)
                    logging.info(price)
                break

        place.menu_freshness = datetime.date.today()
        place.put()
        return place.menu
