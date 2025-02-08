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


def run_simulation(simulation_id: str):
    """Executes the simulation in the background."""
    try:
        pumle = Pumle(config=CONFIG)
        pumle.setup()
        configs = pumle.pre_process()
        layers_to_keep = {"tabular_data"}

        simulations[simulation_id] = {"status": "running", "configs": configs}
        pumle.run_simulations()

        if "pre_bronze" not in layers_to_keep:
            pumle.exclude_previous_layers("pre_bronze")
        if "metadata" not in layers_to_keep:
            pumle.exclude_previous_layers("metadata")

        simulations[simulation_id] = {"status": "saving data", "configs": configs}
        pumle.post_process()

        if "bronze_data" not in layers_to_keep:
            pumle.exclude_previous_layers("bronze_data")

        pumle.save_data()

        if "silver_data" not in layers_to_keep:
            pumle.exclude_previous_layers("silver_data")

        pumle.save_tabular_data()
        simulations[simulation_id] = {"status": "completed", "configs": configs}
    except Exception as e:
        simulations[simulation_id] = {"status": f"failed: {str(e)}"}


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
