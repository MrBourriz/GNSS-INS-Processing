#%%
#Modified by Bourriz mohamed 2023
from typing import Tuple, List
import numpy as np
from numpy.core.fromnumeric import trace
import Modules.common as c

class Calc:
  def __init__(self):
    self.is_setup = False
    pass

  def get_chn(self) -> List[str]:
    pass

  def required_vars(self) -> List[str]:
    pass

  def do_calc(self, sampled_pos, sats_FOV) -> Tuple[str, list]:
    # Expected sats_FOV heirarchy is:  time{} -> prn{} -> (x,y,z)
    # Expected sampled_pos order is :  chn{} -> data[]
    pass


class Calc_gdop(Calc):
  def __init__(self):
    super().__init__()
    pass

  def get_chn(self) -> List[str]:
    return ['HDOP', 'VDOP', 'GDOP']

  def required_vars(self) -> List[str]:
    return [c.CHN_UTC, c.CHN_LAT, c.CHN_LON, c.CHN_ALT,c.CHN_TMS]

  def do_calc(self, pos_pos, sats_FOV) -> Tuple[str, list]:
    # sats_FOV is ordered like:  times{} -> prn{} = (x,y,z)

    results = {'HDOP': [], 'VDOP': [], 'GDOP': []}

    for i in range(len(pos_pos[c.CHN_UTC])):
      t = pos_pos[c.CHN_UTC][i]

      lat = pos_pos[c.CHN_LAT][i]
      lon = pos_pos[c.CHN_LON][i]
      alt = pos_pos[c.CHN_ALT][i]

      u = np.array(c.lla2ecef(lat, lon, alt))

      mat: np.array = []

      # Add visible satellites to LOS matrix
      for j in sats_FOV[t]:
        sat_pos = sats_FOV[t][j]                # tuple, ECEF coord of a sat
        d = lambda ax: sat_pos[ax] - u[ax]      # float, axis value difference (x=0, y=1, z=2)
        psd = np.sqrt(d(0)**2 + d(1)**2 + d(2)**2)    # pseudo range from receiver to sat
        m_row = [-d(0)/psd, -d(1)/psd, -d(2)/psd, 1]  # Row in GDOP matrix
        mat.append(m_row)

      m = np.matmul(np.transpose(mat), mat)
      Q = np.linalg.inv(m)
      T = [Q[0][0], Q[1][1], Q[2][2], Q[3][3]]
      hdop = np.sqrt(T[0]**2 + T[1]**2)
      
      results['HDOP'].append(hdop)
      results['VDOP'].append(T[2])
      results['GDOP'].append(np.sqrt(np.trace(Q)))
    
    return results
