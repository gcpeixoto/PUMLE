from utils import *

def execute_simulation():
    # Pipeline test
    PARAMS = read_sim_params()
    print(PARAMS)
    print_report(PARAMS)
    export_to_matlab(PARAMS)
    run_matlab_batch(PARAMS)
    
if __name__ == "__main__":
    execute_simulation()