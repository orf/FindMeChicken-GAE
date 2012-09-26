from google.appengine.ext import ndb
import datetime

class ChickenPlace(ndb.Model):
    identifier = ndb.StringProperty(indexed=True)
    # Some places might not serve chicken :( Store them anyway.
    has_chicken = ndb.BooleanProperty(default=True, indexed=True)

    title = ndb.TextProperty(indexed=False)
    address  = ndb.TextProperty(indexed=False)
    location = ndb.GeoPtProperty(indexed=False)

    menu = ndb.StringProperty(repeated=True, indexed=False)
    menu_freshness = ndb.DateProperty(indexed=False)

    rating = ndb.IntegerProperty(indexed=False)
    created = ndb.DateProperty(auto_now_add=True, indexed=True)

    def MenuIsFresh(self):
        return (datetime.date.today() - self.menu_freshness) > datetime.timedelta(days=7)

    def getID(self):
        return self.key.string_id()

    def setSource(self, source):
        self.source = source

    def getJson(self):
        d = {"title":self.title,
            "address":self.address,
            "location":str(self.location),
            "rating":self.rating}
        if hasattr(self, "source"):
            d.update({"source":self.source})
        if self.key is not None:
            d.update({"id":self.key.urlsafe()})
        return d