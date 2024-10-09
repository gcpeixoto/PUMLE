import platform, os, configparser
from datetime import datetime
import os

PUMLE_ROOT = os.getcwd() 


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
    c.read('setup.ini')

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
    global PUMLE_RESULTS;   PUMLE_RESULTS = c.get('Paths','PUMLE_RESULTS') 
    
    p_params = ['PUMLE_RESULTS']    
        
    # Pre-Processing
    pp_params = ['case_name', 'file_basename', 'model_name']    
                                      
    # Grid
    gp_params = ['file_path', 'repair_flag']
    
    # Fluid
    fp_params = ['pres_ref', 'temp_ref', 'cp_rock', 'srw', 'src', 'pe', 'XNaCl', 'mu_brine']

    # Initial Conditions
    sp_params = ['sw_0']

    # TODO Study MRST::addBC
    # Boundary conditions
    bc_params = ['type']

    # Well
    w_params = ['CO2_inj']

    # Schedule
    s_params = ['injection_time', 'migration_time', 'injection_timestep_rampup', 'migration_timestep']
    
    # Fetch sections to return a dict whose keys are sections and values are second-level dicts of parameters
    all_params = [p_params, pp_params, gp_params, fp_params, sp_params, bc_params, w_params, s_params]
    
    PARAMS = {}
    for k in range(len(all_params)):
        PARAMS[sections[k]] = dict(zip(all_params[k], [aux[k](_) for _ in all_params[k]]))
        
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
    print(os.listdir('..'))
                    
    # Search in directory above
    if 'setup.ini' not in os.listdir(): 
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
        for key, value in items.items():
            ini_str += f"{key} = {value}\n"
        ini_str += "\n"
    return ini_str



def print_report(PARAMS: dict, msg: bool=True) -> None:
    """
    Print simulation setup report for log purposes.
    
    Parameters
    ---------
        PARAMS: dictionary of parameters
        PUMLE_RESULTS: results output directory
        msg: log message
    
    """
    
    # Defaults results folder to '/temp'
    out = os.path.join(PUMLE_ROOT,PUMLE_RESULTS)
    print(out)

    if len(PUMLE_RESULTS) == 0:
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
    with open(os.path.join(PUMLE_ROOT,PUMLE_RESULTS,'report.txt'),'w',) as fo:
        
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

    print(PUMLE_ROOT)
    
    for k in PARAMS.keys():    
        k_formated = k.replace('-','').replace(' ','')
        basename = f"{k_formated}ParamsPUMLE.mat"
        mroot = os.path.join(PUMLE_ROOT,'m')
        fname = os.path.join(mroot,basename)
        savemat(fname, PARAMS[k], appendmat=True)
        print(f'[PUMLE] Matlab file \'{basename}\' exported to \'{mroot}\'.')
    
def run_matlab_batch(PARAMS):    
    import subprocess
    
    
    mfile = PUMLE_ROOT + '/m'
    
    # Change directory to Matlab folder
    print(mfile)
    os.chdir(mfile)

    print(os.getcwd())

    # Command to run matlab script in batch mode without Java
    cmd = f' --silent --eval co2lab3DPUMLE'
    
    try:
        out = subprocess.run("octave" + cmd, shell=False, check=True)
        print(f"[PUMLE] Calling Matlab in batch mode: {out.returncode}")
        
    except subprocess.CalledProcessError as e:
        print(f"[PUMLE] exception raise: {e}")
 
    # Change back to root folder
    os.chdir(os.path.join(PUMLE_ROOT,"ipynb"))