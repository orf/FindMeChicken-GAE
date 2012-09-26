from models import ChickenPlace
from google.appengine.ext import ndb

class ChickenSource(object):
    '''
    I am a source of chicken. You give me a GPS location and/or a postcode and I will
    try my hardest to return a bunch of ChickenLocations.
    '''

    NAME = None

    POSTCODE_REQUIRED = None
    LOCATION_REQUIRED = None

    def GetAvailablePlaces(self, postcode=None, location=None):
        '''
        I return a list of ChickenPlace objects based on the postcode and/or location.
        '''
        raise NotImplementedError()


    def MenusAvailable(self):
        ''' I return True if I am able to fetch menus and False if no menus are available '''
        raise NotImplementedError()


    def GetMenu(self, place):
        '''
        Give me a single place and I will return the menu
        '''
        raise NotImplementedError()

    def getPlacesFromDataStore(self, places):
        '''
        I get given a list of ID's. I return a list of database entries
        I may also cache stuff in the future.
        '''
        entries = self.get_multi([
            ndb.Key(ChickenPlace,id, namespace=self.NAME)
            for id in places])
        return {x.getID():x for x in entries if x is not None and x.has_chicken}

    def get_multi(self, keys):
        futures = [key.get_async() for key in keys]
        return [future.get_result() for future in futures]