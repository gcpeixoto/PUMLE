import os
import sqlite3
from src.pumle.pumle import Pumle
from src.pumle.db import DBManager
from dotenv import load_dotenv

load_dotenv()


# ------------------------------------------------
# CONFIGURAÇÃO INICIAL
# ------------------------------------------------
CONFIG = {
    "root_path": os.path.dirname(os.path.abspath(__file__)),
    "save_metadata": False,
    "num_threads": 4,
    "saving_method": "numpy",
    "upload_to_s3": True,
    "s3_config": {
        "bucket_name": os.getenv("S3_BUCKET_NAME"),
        "aws_access_key": os.getenv("AWS_ACCESS_KEY"),
        "aws_secret_key": os.getenv("AWS_SECRET_KEY"),
        "region_name": os.getenv("AWS_REGION_NAME"),
    },
    # "parms_schema": {...}  # Se quiser customizar
}

# Instanciamos o Pumle com essa configuração
pumle = Pumle(config=CONFIG)

# ------------------------------------------------
# FUNÇÕES DO MENU
# ------------------------------------------------


def run_simulation():
    """
    1) Permite o usuário selecionar parâmetros e delta.
    2) Configura no `pumle.config`.
    3) Executa pre_process() e run_simulations().
    """
    possible_parameters = [
        "pres_ref",
        "temp_ref",
        "cp_rock",
        "srw",
        "src",
        "pe",
        "xnacl",
        "rho_h2o",
    ]
    print("\n=== RUN SIMULATION ===")
    print("Possible parameters:", possible_parameters)

    # 1) Usuário seleciona parâmetros
    parameters_input = input("Enter parameters (separated by commas): ").strip()
    selected_params = [
        param.strip() for param in parameters_input.split(",") if param.strip()
    ]

    # 2) Usuário informa delta
    try:
        delta_input = input("Enter delta variation: ").strip()
        delta_var = float(delta_input)
    except ValueError:
        print("Invalid input for delta variation. Please enter a numeric value.")
        input("Press Enter to continue...")
        return

    # 3) Ajustamos no CONFIG do pumle
    pumle.config["selected_parameters"] = selected_params
    pumle.config["variation_delta"] = delta_var

    # 4) Chamamos pre_process() => gera .mat, define hash, etc.
    #    run_simulations() => chama script .sh e .cpp
    print("[INFO] Starting pre_process...")
    pumle.pre_process()
    print("[INFO] Pre-process done. Starting simulations...")
    pumle.run_simulations()
    print("[INFO] Simulations finished.")
    input("Press Enter to continue...")


def persist_data():
    """
    1) Roda post_process() para parsear resultados
    2) Salva dados (silver->golden), metadados, etc.
    """
    print("\n=== PERSIST DATA ===")
    # post_process() => parseia bronze_data
    print("[INFO] Parsing results from bronze_data...")
    # Precisamos salvar cada sim. Em muitos cenários,
    # cada variação gera um sim_hash diferente. Aqui, iremos
    # iterar sobre `pumle.configs`.
    print("[INFO] Saving consolidated data (silver->golden)...")
    if not pumle.configs:
        print("[INFO] No simulations found.")
        input("Press Enter to continue...")
        return
    for conf in pumle.configs:
        sim_hash = conf["SimNums"]["sim_hash"]

        result = pumle.post_process(sim_hash)
        # chamamos save_data passando o hash
        pumle.save_data(sim_hash, result)

    print("[INFO] Data persisted successfully.")
    input("Press Enter to continue...")


def show_db():
    """
    Lê do BD e mostra todas as simulações registradas
    """
    print("\n=== SHOW DATABASE ===")
    db = DBManager()
    query = "SELECT sim_hash, sim_id, fluid_params, status FROM simulations"
    with sqlite3.connect(db.db_path) as conn:
        rows = conn.execute(query).fetchall()

    if not rows:
        print("No simulations found in DB.")
    else:
        print(f"{'HASH':<12} | {'SIM_ID':<6} | {'STATUS':<10} | FLUID_PARAMS")
        print("-" * 80)
        for shash, sid, fparams, status in rows:
            print(f"{shash:<12} | {sid:<6} | {status:<10} | {fparams}")
    print()
    input("Press Enter to continue...")


def clean_old_files():
    """
    Se desejar remover pastas antigas ou data_lake,
    chame alguma função do Pumle ou faça aqui.
    """
    print("\n=== CLEAN OLD FILES ===")
    # Exemplo: pumle.clean_older_files()
    # Se implementado, cuidado para não apagar coisas que ainda está rodando
    pumle.clean_older_files()
    print("[INFO] Old files cleaned.")
    input("Press Enter to continue...")


def main_menu():
    while True:
        # Se Windows, troque por "cls"
        os.system("clear")
        menu_text = r"""
  =========================================
               P U M L E   M E N U
  =========================================
   1) Run simulation
   2) Persist data (post-process + save)
   3) Show DB records
   4) Clean old files
   5) Exit
  -----------------------------------------
        """
        print(menu_text)
        choice = input("Select an option: ").strip()

        if choice == "1":
            run_simulation()
        elif choice == "2":
            persist_data()
        elif choice == "3":
            show_db()
        elif choice == "4":
            clean_old_files()
        elif choice == "5":
            print("\nExiting. Goodbye!\n")
            break
        else:
            print("Invalid option!")
            input("Press Enter to continue...")


if __name__ == "__main__":
    main_menu()
