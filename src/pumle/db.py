# db.py
import sqlite3

CREATE_TABLE_SIM = """
CREATE TABLE IF NOT EXISTS simulations (
    sim_hash TEXT PRIMARY KEY,
    sim_id INTEGER,
    fluid_params TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

INSERT_SIM = """
INSERT OR IGNORE INTO simulations (sim_hash, sim_id, fluid_params, status)
VALUES (?, ?, ?, ?);
"""

UPDATE_SIM_STATUS = """
UPDATE simulations
SET status = ?
WHERE sim_hash = ?;
"""

GET_SIM_BY_HASH = """
SELECT sim_hash, sim_id, fluid_params, status
FROM simulations
WHERE sim_hash = ?;
"""


class DBManager:
    def __init__(self, db_path="pumle.db"):
        self.db_path = db_path
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(CREATE_TABLE_SIM)

    def insert_simulation(self, sim_hash: str, sim_id: int, fluid_params: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(INSERT_SIM, (sim_hash, sim_id, fluid_params, "CREATED"))

    def update_sim_status(self, sim_hash: str, new_status: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(UPDATE_SIM_STATUS, (new_status, sim_hash))

    def get_sim_by_hash(self, sim_hash: str):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(GET_SIM_BY_HASH, (sim_hash,))
            row = cur.fetchone()
            return row
