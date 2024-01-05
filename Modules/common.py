#Modified by Bourriz mohamed 2023
from pyproj.transformer import Transformer
import datetime as d
import typing as t
import os

BASE_FOLDER = 'C:/Users/bourriz/GNSS-Correction-RTKLIB-master/UIS_PosPac_HyspexNav_processing/Result/' #Path u can change it
RINEX_FOLDER = BASE_FOLDER + 'Corrections_files'
POS_DATA_FOLDER = BASE_FOLDER +'Position'
# print(RINEX_FOLDER)

# WGS84 constants
# TODO: put them here?


# Column header names as written in the postioning data csv files
CHN_LAT = 'Latitude'
CHN_LON = 'Longitude'
CHN_ALT = 'Height'
CHN_UTC = 'UTC_Time'
CHN_SAT = 'ns'
CHN_TMS = 'Timestamp'
CHN_DEFAULTS = (CHN_TMS,CHN_LON, CHN_LAT, CHN_ALT, CHN_UTC, CHN_SAT)



# Time intervals for which to calculate GDOP
GDOP_INTERVAL = d.timedelta(seconds=2)

# TODO: write in proper struct format
# Types of GDOP output 
GDOP_ALL = 0
GDOP_ONLY = 1

# Angle from horizon for FOV mask (in degrees)
LOS_ANGLE = 5


# Functions

def lla2ecef(lat, lon, alt) -> tuple:
  # https://epsg.io/4978 and http://epsg.io/4979
  # WGS84 lat,lon,alt    and WGS84 ECEF
  t = Transformer.from_crs("epsg:4979", "epsg:4978")
  return (t.transform(lat, lon, alt))