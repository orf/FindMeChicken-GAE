from google.appengine.ext import webapp
from sources.justeat import JustEatSource
from sources.kfc import KFCSource
from google.appengine.ext import ndb
from lib import geocode
import json, logging, operator

SOURCES = {
    "JustEat":JustEatSource,
    "KFC":KFCSource
}

class ChickenHandler(webapp.RequestHandler):

    def jsonError(self, message):
        return json.dumps({"error":message})

    def get(self):
        try:
            gps_input = self.request.get("gps","") #LAT,LONG
            gps = ndb.GeoPt(gps_input)
        except Exception:
            gps = None

        postcode = self.request.get("postcode",None)
        if not any([postcode, gps]):
            return self.response.out.write(
                self.jsonError("No GPS or postcode given")
            )

        source = self.request.get("sources",None) # List of sources to use, comma separated
        if source is None:
            sources_to_use = SOURCES.values()
        else:
            sources_to_use = [ SOURCES.get(name)
                               for name in source.split(",")
                               if name in SOURCES ]

        results = []
        for source_class in sources_to_use:
            source = source_class()
            try:
                _results = source.GetAvailablePlaces(postcode=postcode, location=gps)
            except Exception, e:
                logging.exception("Error processing %s for postcode %s, Loc: %s"%(source_class.__name__, postcode, gps))
                continue

            for x in _results:
                x.setSource(source.NAME)

            if gps:
                results.extend([(geocode.distance(gps, place.location), place)
                                for place in _results])
            else:
                results.extend([(None, place) for place in _results])

        if gps is not None:
            results = sorted(results, key=operator.itemgetter(0))
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(json.dumps([(dist,p.getJson()) for dist,p in results]))


class ChickenMenuHandler(webapp.RequestHandler):
    def get(self):
        key = self.request.get("id",None)
        if not key:
            return self.response.out.write(json.dumps({"error":"No ID given"}))

        db_key = ndb.Key(urlsafe=key)
        entry = db_key.get()
        source = db_key.namespace()

        chicken_source = SOURCES[source]()
        if not chicken_source.MenusAvailable():
            return json.dumps({"menu":None})

        menu = chicken_source.GetMenu(entry)
        self.response.out.write(json.dumps({"menu":menu}))


app = webapp.WSGIApplication([('/getChicken', ChickenHandler),
                              ('/getMenu', ChickenMenuHandler)],
                             debug=True)

