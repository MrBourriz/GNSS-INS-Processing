# GNSS/INS Processing

## About

This repository comprises Jupyter Notebooks presenting the outcomes of my MSc Thesis titled 'Development of a holistic open-source processing pipeline for drone-based hyperspectral line scanning systems'. The main goal was to establish an open-source workflow for the Post-Processing Kinematic (PPK) correction of Global Navigation Satellite System (GNSS) data. This corrected GNSS data was then integrated with Inertial Navigation System (INS) data using an Extended Kalman Filter (EKF). The ultimate goal was to provide precise positioning (X,Y,Z) and orientation (𝜙,𝜃,𝜓) informations for sensors mounted on Unmanned Aerial Vehicles (UAVs) (Multi/Hyperspectral cameras...).

![Workflow](https://github.com/MrBourriz/GNSS-INS-Processing/assets/108701137/c063b786-23e8-4fb9-a530-abd346244743)

## Implementation Details
### 1. Data Preparation
The automated workflow begins with the 'Convert_To_Rinex.ipynb' notebook, which establishes the foundation for converting APX-15 observations recorded in Trimble *.T04 proprietary format to the universally accepted RINEX format. This notebook integrates with tools like [runpkr00](https://kb.unavco.org/article/trimble-runpkr00-latest-versions-744.html) and [TEQC](https://www.unavco.org/software/data-processing/teqc/teqc.html), facilitating conversion and merging of RINEX (Receiver Independant Exchange Format) files to ensure seamless integration of observation and navigation data, eliminating potential gaps. Subsequently, the 'Download_Corrections_Files.ipynb' notebook automates the retrieval of crucial correction files for PPK from diverse GNSS sources, using FTP (File Transfer Protocol) and allowing customization based on parameters like date and nearest permanent station. This comprehensive workflow optimizes data processing by preparing a complete dataset for further analysis with open-source tools.
### 2. Data Processing
In the data processing phase, serving as a crucial link between data preparation and data fusion,the notebook 'PPK.ipynb' focuses on applying the PPK method to enhance the positional accuracy of raw GNSS observations.The notebook seamlessly integrates [RTKlib](https://www.rtklib.com/) into the automated workflow, utilizing raw GNSS data in RINEX format and correction files previously downloaded to perform differential corrections and improve the rover's positional accuracy.
### 3. Data Fusion
The notebook 'LC_INS_GNSS.ipynb' is a compilation of functions designed for achieving precise navigation by integrating INS and GNSS corrected data using the EKF. The initial function handles dual responsibilities: reading GNSS and Inertial Measurement Unit (IMU) data, ensuring time synchronization, and estimating gyroscope and accelerometer biases to refine sensor measurements. Recognizing the disparate frames of GNSS and IMU measurements, the second function ensures consistent transformation between coordinate systems, with a focus on the NED (North,East,Down) frame for terrestrial navigation. The core of the notebook lies in the third function, which implements EKF functionalities to update INS states using mechanization equations in the NED frame. Matrices like the state transition matrix 𝐹 and measurement matrix 𝐻 play pivotal roles, facilitating accurate state estimation by balancing predicted UAV states and new sensor measurements, accounting for uncertainties in process and measurement noise covariance matrices (𝑄 and 𝑅, respectively). This comprehensive approach continuously refines position, velocity, and attitude estimates throughout the navigation process.

![ekf_vs_kf](https://github.com/MrBourriz/GNSS-INS-Processing/assets/108701137/b89de74a-9f71-43c1-834b-7cf910b9e72e)
### 4. Data Visualization
The 'Visualization.ipynb' notebook employs Python libraries like [Folium](https://python-visualization.github.io/folium/latest/) with [geemap](https://geemap.org/) to plot the drone's flight path on a map using diverse basemaps. This spatial representation of the drone's trajectory ensures a clear and accessible presentation of results, facilitating an intuitive comprehension of the drone's spatial movements.

https://github.com/MrBourriz/GNSS-INS-Processing/assets/108701137/beac5613-925a-4100-b691-5758a8d8d839

## Contributing
Pull requests are always welcome!
For significant changes or bug reports, please initiate the process by opening an issue, this allows us to collaboratively address the proposed modifications to improve this project. 

## To Do
- [x] Develop an automated workflow to convert Trimble *.T04 proprietary format files to RINEX.
- [x] Implement an automated workflow for PPK correction.
- [x] Fuse GNSS and INS data by implementing a loosely coupled architecture.
- [ ] Generalize the RINEX conversion process to accommodate various formats such as Topcon, Leica, etc.
- [ ] Enhance the workflow by integrating algorithms for despiking and smoothing.     

## Acknowledgments
This Research would not have been possible without the collaborative efforts and contributions from both the [HIF-EXPLO](https://github.com/hifexplo) & my supervisor from the department of Cartography and Photogrammetry at the School of Geomatics and Surveying Engineering in the Institute of Agronomy and Veterinary Medicine Hassan II (IAV). Their support has played a crucial role in the success of this project.

## References

[1] Chen K, Chang G and Chen C. GINav: a MATLAB-based software for the data processing and analysis of a GNSS/INS integrated navigation system. GPS Solut 25, 108 (2021). https://doi.org/10.1007/s10291-021-01144-9

[2] RTKLIB ver. 2.4.2 Manual. https://www.rtklib.com/rtklib_document.htm

[3] Kalman Filter Interview. Towards Data Science. https://towardsdatascience.com/kalman-filter-interview-bdc39f3e6cf3

[4] Groves, P.D. Principles of GNSS, Inertial, and Multi Sensor Integrated Navigation Systems; Artech House: London, UK, (2013).

[5] GDOP calculation for simple GPS positoning post-processing. GitHub page. https://github.com/FelipeTJ/gdoper/tree/main

