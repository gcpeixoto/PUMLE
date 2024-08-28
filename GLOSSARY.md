# PUMLE Simulation Glossary


## Pre-Processing

- **case_name**: `GCS01`  
  The name of the case study for this simulation.

- **file_basename**: `db_sim`  
  The base name of files used for organization purposes.

- **model_name**: `UNISIM-I-D`  
  The name of the reservoir model being used.

## Grid

- **repair_flag**: `False`  
  Indicates whether to repair the grid ZCORN. Valid inputs are `True` or `False`.

## Fluid

- **pres_ref**: `39.12 MPa`  
  Reference pressure for the simulation.

- **temp_ref**: `95.15 ºC`  
  Reference temperature for the simulation.

- **cp_rock**: `4e-5 1/bar`  
  Rock compressibility.

- **srw**: `0.11`  
  Brine residual saturation.

- **src**: `0.21`  
  CO2 residual saturation.

- **pe**: `5 kPa`  
  Maximum capillary pressure.

- **XNaCl**: `0.2`  
  NaCl mass fraction to consider for brine.

- **mu_brine**: `8e-4 Pa.s`  
  Brine viscosity (to be implemented).

## Initial Conditions

- **sw_0**: `1.0`  
  Initial brine saturation.

## Boundary Conditions

- **type**: `pressure`  
  Type of boundary condition applied over vertical and lateral faces. Valid inputs are `pressure` or `flux`.

## Wells

- **CO2_inj**: `1.5e9 m^3/year`  
  Gas injection volumetric flow rate.

- **wells_list**: `NA1A: (38, 36, 6, 11) & RJS16: (12, 14, 6, 11)`  
  Logical grid coordinates for wells, specified in the format `(I, J, K_min, K_max)`.

## Schedule

- **injection_time**: `5 years`  
  Duration of the injection phase (can be fractional).

- **migration_time**: `10 years`  
  Duration of the post-injection phase (can be fractional).

- **injection_timestep_rampup**: `1/6`  
  Fraction of years for the simulation ramp-up time slicing.

- **migration_timestep**: `15`  
  Number of time steps for post-injection control.
