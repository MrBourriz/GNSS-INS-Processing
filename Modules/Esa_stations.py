#Modified by Bourriz mohamed 2023
ESA_URL = 'gssc.esa.int'
ESA_NAV = '/gnss/data/daily/'

stations = ['brdc']

# Return a random GPS monitoring station
def get_station(station):
  station=stations[0]
  return station

def get_url():
  return ESA_URL

def get_nav():
  return ESA_NAV
