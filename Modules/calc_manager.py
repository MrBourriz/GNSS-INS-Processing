###############################################################################
# Gdoper v2.0                                                                 #
#                                                                             #
# File:  calc_manager.py
# Author: Felipe Tampier Jara
# Date:   5 Apr 2021
# Email:  felipe.tampierjara@tuni.fi
# TODO: update description
# Description:***
# Gets positioning data using reader_pos_data.py and for every row of data,
# uses reader_rinex.py to aquire satellite data and calculates the GDOP +
# other data. Outputs processed data + corresponding original data to csv.
#                                                                             #
############################################################################### 
#Modified by Bourriz mohamed 2023

# %%
from typing import Dict, Mapping, List
from xarray import DataArray
from csv import writer
import datetime as dt
import time,sys
import Modules.common as c
import Modules.reader_rinex as rr
import Modules.reader_pos_data as rpc
from Modules.fov_models import FOV_model, FOV_view_match
from Modules.calcs import Calc, Calc_gdop
from Modules.d_print import Debug, Info




class Calc_manager:
  def __init__(self, in_file,
              out_file = '',
              rinex_folder = c.RINEX_FOLDER,
              data_folder = c.POS_DATA_FOLDER,
              out_folder = c.POS_DATA_FOLDER,
              ts = 5):

    # Sampling period
    self.Ts = dt.timedelta(seconds=ts)

    # Directories
    self.rinex_dir = rinex_folder
    self.pdata_dir = data_folder
    self.out_dir = out_folder

    # File names
    self.input_file = in_file
    self.output_file = (in_file[:-4] + '_gdop.csv' if out_file == '' else out_file)

    # Objects
    self.pos_obj = rpc.Pos_data(self.pdata_dir + self.input_file)
    self.sat_obj = rr.Orbital_data()
    self.fov_obj = FOV_model()      # real obj created in setup_FOV()
    self.calcs_q: List[Calc] = []   # A queue for calculations
    self.req_vars = set()           # The variables required by FOV_model and Calc

    # Processed data
    self.output_map: Dict[str, list] = {}
    self.ordered_keys: List[str]        = []
  

  def set_FOV(self, model: FOV_model) -> None:
    """
      Input the instance of an FOVmodel to be used in the calculations
    """
    self.fov_obj = model


  def add_calc(self, calc: Calc) -> None:
    """
      Add a Calc object to the queue to perform calculations on the data
    """
    if calc in self.calcs_q:
      return
    else:
      self.calcs_q.append(calc)


  def __setup(self) -> None:
    """
      Perform checks and do setups before starting to process data
    """
    if self.fov_obj == FOV_model():
      raise Exception("FOV_model is the base class, it cannot be used.\
                      Select an inherited model.")
    
    if len(self.calcs_q) == 0:
      raise Exception("No calculations have been queued.\
                      Use the 'add_calc()' method to do so.")

    for i in self.calcs_q:
      if i == Calc():
        raise Exception("Calc cannot be used as a calculation.\
                        Select an inherited class.")
      else:
        self.req_vars.union(set(i.required_vars()))

    self.req_vars = self.req_vars.union(set(self.fov_obj.required_vars()))

    # Have readers check for existance of their files and folders
    self.pos_obj.setup()
    self.sat_obj.setup(self.pos_obj.get_first_utc())


  def __sample_pos(self) -> Dict[str, list]:
    """
      Get the position data from file and return a sampled version
    """
    # Get pos data
    all_pos = self.pos_obj.get_merged_cols(list(self.req_vars))
    all_pos_row_count = self.pos_obj.row_count
    chn_keys = list(all_pos.keys())
    sampled = {}

    # Setup empty lists for each CHN
    for i in chn_keys:
      sampled[i] = []

    # Sample
    dif = dt.timedelta(seconds=self.Ts.seconds)
    last_saved =  dt.datetime.fromisoformat(self.pos_obj.get_first_utc()) - dif

    for i in range(all_pos_row_count):
      t = dt.datetime.fromisoformat(all_pos[c.CHN_UTC][i])  # TODO: use proper name for utc

      if t-last_saved >= dif:

        # Add samples from this index
        for chn in chn_keys:
          sampled[chn].append(all_pos[chn][i])
        
        last_saved = last_saved + dif

    return sampled  


  def __acquire_sats(self, pos_timestamps) -> Dict[str, DataArray]:
    """
      Return all satellites for all pos in time
    """
    return self.sat_obj.get_sats_pos(pos_timestamps)
    

  def __sats_in_fov(self, pos_pos, sats_pos):
    """
      Return all satellites in view from pos_pos, given sats_pos and FOV_model
    """
    return self.fov_obj.get_sats(pos_pos, sats_pos)
    

  def __do_calcs(self, pos_pos, sats_LOS_pos): # Positions in ECEF
    """
      Return dict with keys as calculation names, and values
      as lists of datapoints.\n
      The datapoints are in the same line as the values used
      for the calculation. 
    """
    if len(self.calcs_q) == 0:
      raise Exception("No calculations were queued")

    for calc in self.calcs_q:
      self.__add_dict_to_output_map(calc.do_calc(pos_pos, sats_LOS_pos))
  

  def __add_dict_to_output_map(self, data: dict):
    """
      Add a title to the data and store in the output mapping.
    """
    self.ordered_keys.extend(data.keys())
    self.output_map.update(data)


  def __add_to_output_map(self, chn: str, data: list):
    """
      Add a title to the data and store in the output mapping.
    """
    self.ordered_keys.append(chn)
    self.output_map[chn] = data


  def __output_to_file(self):
    """
      Writes all data in self.output_map to a file in csv format.\n
      File name is "self.out_dir + self.output_file"
    """

    fn = self.out_dir + self.output_file
    map_keys = self.ordered_keys
    row_count = len(self.output_map[map_keys[0]])

    with open(fn, 'w') as csvfile:
      wr = writer(csvfile)
      wr.writerow(map_keys)

      for row in range(row_count):
        temp = []
        for col in map_keys:
          temp.append(self.output_map[col][row])

        wr.writerow(temp) 


  def process_data(self):
    """
      Acquire relevant data, process, and output into csv format
    """
    tot = time.perf_counter()
    now = time.perf_counter()
    Debug(f'Setting up...')
    self.__setup()
    Debug(f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(f'Sampling positions...')
    pos = self.__sample_pos()
    Debug(f'Done. {time.perf_counter()-now:.3f}s\n')

    # Add data used for calculation to output file
    for k in list(pos.keys()):
      if (k in self.req_vars) and (k not in self.ordered_keys):
        self.__add_to_output_map(k, pos[k])

    now = time.perf_counter()
    Debug(f'Aquiring satellite info...')
    all_sats = self.__acquire_sats(pos[c.CHN_UTC]) # TODO: make CHNs more flexible
    #Debug(f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(f'Calculating visible satellites...')
    los_sats = self.__sats_in_fov(pos, all_sats)
    Debug(f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(f'Performing calculations...')
    self.__do_calcs(pos, los_sats)
    Debug(f'Done. {time.perf_counter()-now:.3f}s\n')

    now = time.perf_counter()
    Debug(f'Writing to file...')
    self.__output_to_file()
    Debug(f'Done. {time.perf_counter()-now:.3f}s\n')

    Debug(f'Total runtime: {time.perf_counter() - tot:.3f}'
          + f' for {len(self.output_map[self.ordered_keys[0]])} output rows')




def test():
  drone_data = '/Pos_UTC.csv'

  gdoper = Calc_manager(drone_data, ts=10)
  gdoper.set_FOV(FOV_view_match())
  gdoper.add_calc(Calc_gdop())
  gdoper.process_data()

if __name__ == '__main__':
  test()
  print('Done running')
  pass


