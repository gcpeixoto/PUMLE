from fastapi import FastAPI, BackgroundTasks
from uuid import uuid4
from typing import Dict
import os
from src.pumle.pumle import Pumle

app = FastAPI()

# Store simulation states
simulations: Dict[str, Dict[str, str]] = {}
global_simulation_id = 1
# Default configuration
CONFIG = {
    "root_path": os.path.dirname(os.path.abspath(__file__)),
    "selected_parameters": ["pres_ref"],
    "variation_delta": 0.3,
    "save_metadata": False,
    "num_threads": 4,
}

pumle = Pumle(config=CONFIG)
cache = []
use_cache = True


def run_simulation(simulation_id: str):
    """Executes the simulation in the background."""
    try:
        pumle.pre_process()

        if use_cache:
            for config in pumle.configs[:]:
                if config["Fluid"] not in cache:
                    cache.append(config["Fluid"])
                else:
                    pumle.configs.remove(config["Fluid"])

        if pumle.configs == []:
            simulations[simulation_id] = {"status": "running", "configs": []}
        else:
            config_to_log = [i["Fluid"] for i in pumle.configs]

            simulations[simulation_id] = {"status": "running", "configs": config_to_log}
            pumle.run_simulations()
    except Exception as e:
        simulations[simulation_id] = {"status": f"failed: {str(e)}"}


@app.post("/persist/{simulation_id}")
def persists_data(simulation_id: str):
    simulations[simulation_id] = {
        "status": "saving data",
    }
    pumle.post_process()
    pumle.save_data()

    simulations[simulation_id] = {
        "status": "completed",
    }
    return simulations[simulation_id]


@app.post("/run")
def start_simulation(background_tasks: BackgroundTasks):
    """Starts a new simulation and runs it in the background."""
    global global_simulation_id
    simulation_id = str(global_simulation_id)
    global_simulation_id += 1
    simulations[simulation_id] = {"status": "queued"}
    background_tasks.add_task(run_simulation, simulation_id)
    return simulations[simulation_id]


@app.get("/status")
def get_all_status():
    """Retrieves the status of all simulations."""
    return simulations


@app.get("/status/{simulation_id}")
def get_status(simulation_id: str):
    """Retrieves the current status of a simulation."""
    return {
        "simulation_id": simulation_id,
        "status": simulations.get(simulation_id, "not found"),
        "configs": simulations.get(simulation_id, {}).get("configs"),
    }


@app.get("/results/{simulation_id}")
def get_results(simulation_id: str):
    """Fetches results of a completed simulation."""
    results_path = os.path.join(CONFIG["root_path"], "data_lake", "tabular_data")
    if os.path.exists(results_path):
        return {"simulation_id": simulation_id, "results_path": results_path}
    return {"simulation_id": simulation_id, "error": "Results not found"}


@app.delete("/clean")
def clean_old_files():
    """Cleans up old simulation files."""
    try:
        p = Pumle(config=CONFIG)
        p.set_data_lake_paths()
        p.clean_older_files()
        return {"message": "Old files cleaned successfully"}
    except Exception as e:
        return {"error": str(e)}
