from src.pumle.dataset import Dataset

data = Dataset("data_lake/json_results", "data_lake/consolidated_data")

data.save_consolidated_data()
