import platform, os, configparser
from datetime import datetime

GENERICAL_PATH = "/".join(os.getcwd().split('/')[:-1]) 

def get_params(c: configparser) -> dict:   
    """
    Get simulation parameters from configuration setup file.
    
    Parameters
    ----------
        c : configparser
        
    Returns
    -------
    
        Dictionary of parameters.
    
    """ 
    
    # Read input parameters
    c.read(os.path.join('..','setup.ini'))

    # Sections
    sections = ['Paths', 'Pre-Processing', 'Grid', 'Fluid', 'Initial Conditions', 
                        'Boundary Conditions', 'Wells', 'Schedule', 'MATLAB']
    
    # Auxiliary function to reduce coding. 
    # Here, 'section=section' is used to bypass late binding and capture the looped value.
    # Otherwise, the 'section' value at lambda definition time would be the last looped value.
    aux = [lambda param, section=section: c.get(section, param) for section in sections]

    # TODO Remove globals and implement class. Should we transfer that to a Makefile??
    
    # check if the key Paths exists in the configuration file

    # Paths 
    global PUMLE_ROOT;      PUMLE_ROOT = c.get('Paths','PUMLE_ROOT') 
    global PUMLE_RESULTS;   PUMLE_RESULTS = c.get('Paths','PUMLE_RESULTS') 
    
    p_params = ['PUMLE_ROOT', 'PUMLE_RESULTS']    
        
    # Pre-Processing
    pp_params = ['case_name', 'file_basename', 'model_name']    
                                      
    # Grid
    gp_params = ['file_path', 'repair_flag']
    
    # Fluid
    fp_params = ['pres_ref', 'temp_ref', 'cp_rock', 'srw', 'src', 'pe', 'XNaCl', 'rho_h2o']

    # Initial Conditions
    sp_params = ['sw_0']

    # TODO Study MRST::addBC
    # Boundary conditions
    bc_params = ['type']

    # Well
    w_params = ['CO2_inj']

    # Schedule
    s_params = ['injection_time', 'migration_time', 'injection_timestep_rampup', 'migration_timestep']

    # MATLAB
    m_params = ['matlab','mrst_root']
    
    # Fetch sections to return a dict whose keys are sections and values are second-level dicts of parameters
    all_params = [p_params, pp_params, gp_params, fp_params, sp_params, bc_params, w_params, s_params, m_params]
    
    # Marks to do a type casting to float over numerical parameters.
    cast = [False, False, False, True, True, False, True, True, False]
    
    PARAMS = {}
    for k in range(len(all_params)):
        PARAMS[sections[k]] = dict(zip(all_params[k], [float(aux[k](_)) if cast[k] else aux[k](_) for _ in all_params[k]]))
        
    print(f'[PUMLE] Simulation setup file sucessfully read.')

    return PARAMS

def read_sim_params():
    """
    Read simulation parameters from the configuration file 'setup.ini'. 
    
    TODO Refactor this function to better define the top project folder and allow setup.ini to come from other path.

    Returns
    -------
    dict: 
    
    """
                    
    # Search in directory above
    if 'setup.ini' not in os.listdir('..'): 
        raise RuntimeError('File \'setup.ini\' not found in the top project folder. Change working directory and rerun this script.')
   
    else: 
        # Get path to top folder project inside 'setup.ini'                            
        c = configparser.ConfigParser()
        return get_params(c)
    
    

def dict_to_ini(config_dict):
    """Helper function to convert a dict back to .ini format"""
    
    ini_str = ""
    for section, items in config_dict.items():
        ini_str += f"[{section}]\n"
        print(items)
        for key, value in items.items():
            ini_str += f"{key} = {value}\n"
        ini_str += "\n"
    return ini_str



def print_report(PARAMS: dict, res_dir: str, msg: bool=True) -> None:
    """
    Print simulation setup report for log purposes.
    
    Parameters
    ---------
        PARAMS: dictionary of parameters
        res_dir: results output directory
        msg: log message
    
    """
    
    # Defaults results folder to '/temp'
    out = os.path.join(PUMLE_ROOT,res_dir)

    if len(res_dir) == 0:
        out = os.path.join(PUMLE_ROOT,'temp')
        os.makedirs(out,exist_ok=True)
    else:
        os.makedirs(out,exist_ok=True)
            
    # Get date/time and system information
    system, hostname, release, *_ =  platform.uname()
    date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Text elements to write
    te = {
        0: ''.center(80,'-') + '\n',
        1: 'PUMLE SIMULATION REPORT'.center(80, ' ') + '\n',     
        2: f'Date/Time: {date_time}\n',   
        3: f'OS: {system}\n',
        4: f'Version: {release}\n',
        5: f'Hostname: {hostname}\n'
    }
    
    # Write report
    with open(os.path.join(PUMLE_ROOT,res_dir,'report.txt'),'w',) as fo:
        
        # Header
        fo.write(te[0])
        fo.write(te[1])
        fo.write(te[0])
                
        for k in range(2,6): fo.write(te[k])
        
        # Core information
        fo.write(te[0])        
        fo.write(dict_to_ini(PARAMS)) # TODO Should we change to another structure?        
    
    fo.close()
    
    if msg: print(f'[PUMLE] Report file saved to \'{out}\'.')
    

def export_to_matlab(PARAMS) -> None:
    """ Export dict of simulation parameters to Matlab to be read individually."""
    
    from scipy.io import savemat
    
    for k in PARAMS.keys():    
        basename = f'{k.replace('-','').replace(' ','')}ParamsPUMLE'
        mroot = os.path.join(PUMLE_ROOT,'m')
        fname = os.path.join(mroot,basename + '.mat')
        savemat(fname, PARAMS[k], appendmat=True)
        print(f'[PUMLE] Matlab file \'{basename + '.mat'}\' exported to \'{mroot}\'.')
        
        
def run_matlab_batch(PARAMS):    
    import subprocess
    
    # Path to Matlab binary in your computer
    bin = PARAMS['MATLAB']['matlab']
    
    mfile = PUMLE_ROOT + '/m'
    
    # Change directory to Matlab folder
    os.chdir(mfile)

    # Command to run matlab script in batch mode without Java
    cmd = f'-logfile co2lab3DPUMLE.log -nojvm -batch co2lab3DPUMLE'
    
    try:
        out = subprocess.run([bin] + cmd.split(), shell=False, check=True)
        print(f"[PUMLE] Calling Matlab in batch mode: {out.returncode}")
        
    except subprocess.CalledProcessError as e:
        print(f"[PUMLE] exception raise: {e}")
 
    # Change back to root folder
    os.chdir(os.path.join(PUMLE_ROOT,"py"))

def run_simulation(PARAMS: dict) -> None:
    """
    Run the simulation pipeline.
    
    Parameters
    ----------
        PARAMS: dict
        res_dir: str
        
    """
    
    # Print report
    export_to_matlab(PARAMS)
    run_matlab_batch(PARAMS)


def run_multiple_simulations(PARAMS: dict, res_dir: str, n: int) -> None:
    """
    Run multiple simulations.
    
    Parameters
    ----------
        PARAMS: dict
        res_dir: str
        n: int
        
    """
    # Define the parameter ranges
    print(f'Running {n**3} simulations')
    param_range = np.linspace(-1, 1, n)
    counter = 0
    # Iterate over combinations of parameter values
    for pres_ref in param_range:
        for XNaCl in param_range:
            for rho_h2o in param_range:
                # Update the parameters
                
                PARAMS['Fluid']["pres_ref"] += pres_ref
                PARAMS['Fluid']['XNaCl'] += XNaCl
                PARAMS['Fluid']['rho_h2o'] += rho_h2o
                PARAMS["Pre-Processing"]["case_name"] = f"GCS01_{counter}"
                PARAMS["Paths"]["PUMLE_RESULTS"] = res_dir
                
                print("="*80)
                print(f'Running simulation with pres_ref={pres_ref}, XNaCl={XNaCl}, rho_h2o={rho_h2o}')
                run_simulation(PARAMS)
                print('Simulation finished')
                print("="*80)


if __name__ == "__main__":
    import numpy as np
    # Pipeline test
    PARAMS = read_sim_params()


    run_multiple_simulations(PARAMS, "dataset", 2) # n^3 different simulations
    