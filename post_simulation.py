from src.pumle.sim_results_parser import SimResultsParser


parser = SimResultsParser("data_lake/sim_results")
parser.save_all("data_lake/json_results")
