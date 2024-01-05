###############################################################################
# Gdoper v1.0                                                                 #
#                                                                             #
# File:  gdop_calculation.py
# Author: Felipe Tampier Jara
# Date:   1 Mar 2021
# Email:  felipe.tampierjara@tuni.fi
#
# Description:
# Gets positioning data using reader_pos_data.py and for every row of data,
# uses reader_rinex.py to aquire satellite data and calculates the GDOP +
# other data. Outputs processed data + corresponding original data to csv.
#                                                                             #
############################################################################### 
#Modified by Bourriz mohamed 2023

# %%
import datetime as dt
from typing import Mapping
import pyproj as pp
import numpy as np
import time
import math
import csv
import os



import reader_pos_data as ddr
import reader_rinex as rr
import d_print as p
import common as c
os.chdir(os.path.dirname(os.path.abspath(__file__)))



WGS84_RADIUS = 6378137    # in meters
NOM_GPS_RAD = 26600000    # in meters

class FOV_simple:
  """
    A simple FOV model
  """
  def __init__(self, u) -> None:
      self.m_a = math.pi*(c.LOS_ANGLE)/180      # Mask angle in radians
      self.u = np.array(u)                      # User pos
      self.n_u = self.u/np.linalg.norm(self.u)  # Normalized user pos
      self.dot_value = self.__get_mask_dot()    # Comparison value
      

  def __get_thrsh_point_angle(self) -> float:
    """
      Return the angle between the user and the threshold point.
      The latter is a point along the mask angle at GPS nominal orbit height.
    """

    u = self.u
    pi = math.pi
    m_a = self.m_a

    c1 = pi/2 - m_a                       
    c2 = math.cos(m_a) / NOM_GPS_RAD
    c3 = math.asin(c2 * np.linalg.norm(u))

    return c1 - c3

  def __get_thrsh_mask_len(self) -> float:
    """
      Return the length of the mask vector.
      Using law of sines for a triangle formed by the origin,
      user pos, and threshold point.
    """
    # Angle formed at user pos by its vector and mask vector
    um_a = self.m_a + math.pi/2

    t_a = self.__get_thrsh_point_angle()
    gps_r = NOM_GPS_RAD

    return math.sin(t_a)*gps_r/math.sin(um_a)

  def __get_thrsh_point_vector(self) -> np.array:
    """
      Returns the coordinates of the threshold point.
      Creates a plane along the Z axis and user pos. Using the
      mask angle, a (mask) vector is projected up to nominal
      GPS orbit height. The sum of user pos and mask vector is
      the threshold point vector.

    """

    # Create user pos projection on ecuatorial plane
    u = self.u
    z_ax = np.array([0, 0, 1])
    u_p = u - np.dot(u, z_ax)*z_ax
    u_p = u_p/np.linalg.norm(u_p)

    # Angle of the horizon
    lat = math.acos(np.dot(u_p, z_ax))
    h = lat - math.pi/2                 # TODO: make angle change

    # Create mask vector (from user to threshold point)
    m_a = self.m_a
    m_v = u_p*math.cos(h + m_a) + z_ax*math.sin(h + m_a)
    m_l = self.__get_thrsh_mask_len()
    m_v = m_v * m_l

    # Threshold point vector (from ECEF origin to the point)
    p_t = u + m_v

    return p_t

  def __get_mask_dot(self) -> float:
    """
      Return the dot product of user pos and threshold point
    """

    p_t = self.__get_thrsh_point_vector()

    n_u = self.n_u
    n_pt = p_t/np.linalg.norm(p_t)

    return np.dot(n_u, n_pt)
  
  def compare(self, p_sv: np.array) -> bool:
    """
      Returns true if SV is within line of sight (in FOV)
    """
    return np.dot(self.n_u, p_sv) >= self.dot_value

  def d_compare(self, p_sv: np.array) -> bool:
    """
      Debug version of compare
    """
    res = np.dot(self.n_u, p_sv)
    isIn = res >= self.dot_value
    if isIn:
      p.Print('debug',f'Threshold: {self.dot_value:.5}\tResult: {p.GREEN}{res:.5}{p.CEND}')
    else:
      p.Print('debug',f'Threshold: {self.dot_value:.5}\tResult: {p.VIOLET}{res:.5}{p.CEND}')

    return isIn

class FOV_no_calc:
  """
    Is based on the amount of satellites that the receiver sees
  """
  def __init__(self, u, n_sats) -> None:
    self.u = np.array(u)
    self.n_u = self.u/np.linalg.norm(self.u)
    self.n_sats = int(n_sats)
    self.sats = {}

  def add_sat(self, pos, name):
    # Add position to potential sats
    n_p = pos/np.linalg.norm(pos)
    self.sats[np.dot(self.n_u, n_p)] = name

  def get_satellites(self) -> list:
    visible = []
    ordered = sorted(self.sats.keys(), key=np.abs, reverse=True)
    #print(ordered)
    for i in range(self.n_sats):
      visible.append(self.sats[ordered[i]])
    return visible


class Gdop:
  def __init__(self, filename: str, output_file: str, fov: str = "", t_s: float = 5):
    # Calculation parameters
    self.fov_model = fov
    self.T_s = c.d.timedelta(seconds=t_s)        # Sampling period


    self.pos_index = 0
    self.pos_obj = ddr.PosData(filename)
    self.pos_data = self.pos_obj.get_merged_cols(c.CHN_DEFAULTS) # TODO: Change to dataset
    
    #print(self.pos_data)
    self.sat_data = rr.Orbital_data(self.pos_data[c.CHN_UTC][self.pos_index])
    self.sat_poss = self.sat_data.get_sats_pos([self.pos_obj.get_first_utc()]) # Deprecated
    self.measured_visible_sats = self.pos_data[c.CHN_SAT][self.pos_index]
    self.calculated_visible_sats = self.get_visible_sats()
    self.output_filename = output_file
    self.output_file()

  def print_data(self):
    print()
    p.Print('info',f'Variables for: {self}')
    for i in list(self.__dict__.keys()):
      p.Print('info',f' - {i:15} : {(self.__dict__[i] if type(self.__dict__[i]) != dict else "<dict>")}')
    print()

  def lla2ecef_drone(self) -> tuple:
    # https://epsg.io/4978 and http://epsg.io/4979
    # WGS84 lat,lon,alt    and WGS84 ECEF
    t = pp.Transformer.from_crs("epsg:4979", "epsg:4978") 
    lat = self.pos_data[c.CHN_LAT][self.pos_index]
    lon = self.pos_data[c.CHN_LON][self.pos_index]
    alt = self.pos_data[c.CHN_ALT][self.pos_index]
    return (t.transform(lat, lon, alt))

  def get_visible_sats(self) -> list:
    decef = self.lla2ecef_drone()

    p.Print('info0', f'Drone ecef: {decef}')

    visible = []
    #fov = FOV_simple(decef)
    fov = FOV_no_calc(decef,self.measured_visible_sats)

    for sat in list(self.sat_poss.keys()):
      spos = self.sat_poss[sat]
      #nsat = spos/np.linalg.norm(spos)
      fov.add_sat(spos, sat)
      #if fov.d_compare(nsat):
      #  visible.append(sat)

    visible = fov.get_satellites()

    p.Print('info0',f'visible sats ({len(visible)}): {visible}')
    return visible

  # Calculate GDOP given the receiver's and satellites' positions
  # @return: Calculated GDOP
  def get_single_gdop(self):
    decef = self.lla2ecef_drone()

    mat: np.array = []
    # Calc vis sats is list of sat names
    for i in self.calculated_visible_sats:
      sat_p = self.sat_poss[i]
      d = lambda x: sat_p[x] - decef[x]
      psd = np.sqrt(d(0)**2 + d(1)**2 + d(2)**2)
      row = [-d(0)/psd, -d(1)/psd, -d(2)/psd, 1]
      mat.append(row)

    m = np.matmul(np.transpose(mat), mat)
    Q = np.linalg.inv(m)
    T = np.trace(Q)
    G = np.sqrt(T)
    p.Print('info',f'{p.GREEN}GDOP: {G:.4f}{p.CEND}')

    return G

  def get_all_gdop(self):
    gdops = []
    inview = []
    p.Print('info', f'{p.GREEN}Calculating GDOP{p.CEND} ({self.pos_obj.row_count} rows, calculate every {c.GDOP_INTERVAL.seconds}s)')
    now = time.perf_counter()
    p.Print('\\debug',f'row: {0}')
    gdops.append(self.get_single_gdop())
    inview.append(len(self.calculated_visible_sats))
    for i in range(1, self.pos_obj.row_count):
      self.pos_index = i
      new_date = dt.datetime.fromisoformat(self.pos_data[c.CHN_UTC][self.pos_index])
      if new_date - self.sat_data.utc < self.T_s:
        p.Print('debug0',f'{p.VIOLET}new_date is too close ({new_date-self.sat_data.utc}){p.CEND}')
        gdops.append(0)
        inview.append(0)
        continue
      p.Print('\\debug',f'row: {i}')
      self.sat_data.change_date(new_date)
      self.sat_poss = self.sat_data.get_sats_pos([new_date])
      self.measured_visible_sats = self.pos_data[c.CHN_SAT][self.pos_index]
      self.calculated_visible_sats = self.get_visible_sats()
      gdops.append(self.get_single_gdop())
      inview.append(len(self.calculated_visible_sats))

    p.Print('info\\',f'Done. ({time.perf_counter()-now:.2f}s for {self.pos_index} rows)')
    return gdops, inview

  def output_file(self):
    output = self.pos_data.copy()
    gdops, inview = self.get_all_gdop()
    output['GDOP'] = gdops
    output['calculated_sats_LOS'] = inview

    # TODO: Calculate lines correctly
    p.Print('info', f'Writing to file ({len(gdops)} rows)')
    now = time.perf_counter()
    fn = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + self.output_filename
    with open(fn, 'w') as csvfile: # TODO: implement proper file location
      wr = csv.writer(csvfile)
      wr.writerow(list(output.keys()))

      for row in range(0, self.pos_obj.row_count):
        if output['GDOP'][row] == 0:
          continue

        temp = []
        for col in list(output.keys()):
          temp.append(output[col][row])

        if len(temp) != 0:
          wr.writerow(temp) 

    p.Print('info\\',f'Done. ({time.perf_counter()-now:.2f}s for {self.pos_index} rows)')



def test():
  drone_data = '/test_data/Pos_UTC.csv'
  output = '/test_data/Pos_UTC.csv'

  Gdop(drone_data, output)

  

if __name__ == '__main__':
  test()
  pass

# %%
