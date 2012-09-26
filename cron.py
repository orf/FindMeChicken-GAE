from google.appengine.ext import webapp
from google.appengine.ext import ndb
from models import ChickenPlace
import datetime
import logging


class FlushPlaces(webapp.RequestHandler):
    def get(self):
        # Flush old JustEat chickenplaces
        ten_days_ago = datetime.date.today() - datetime.timedelta(days=10)
        cursor = None
        more = True
        keys = []
        while more:
            results, cursor, more = ChickenPlace.query(namespace="JustEat").filter(ChickenPlace.created < ten_days_ago) \
                                                        .fetch_page(150, keys_only=True, start_cursor=cursor)
            keys.extend(results)

        logging.info("Deleting %s old ChickenPlaces"%len(keys))
        ndb.delete_multi(keys)
        logging.info("Deleted!")

app = webapp.WSGIApplication([('/cron/flush_old', FlushPlaces)],
    debug=True)

