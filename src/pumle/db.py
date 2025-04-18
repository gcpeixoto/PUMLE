# db.py
"""
Database management for PUMLE simulations.
Handles storage and retrieval of simulation metadata and status.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Tuple, Any, Dict
from contextlib import contextmanager
import logging
import ast

# SQL Queries
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

# Simulation status constants
class SimulationStatus:
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DBManager:
    """Manages database operations for PUMLE simulations."""
    
    def __init__(self, db_path: str = "pumle.db") -> None:
        """Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._setup_logger()
        self._ensure_db_directory()
        self._create_tables()
        
    def _setup_logger(self) -> None:
        """Configure logging for the database manager."""
        self.logger = logging.getLogger("pumle.db")
        self.logger.setLevel(logging.DEBUG)
        
    def _ensure_db_directory(self) -> None:
        """Ensure the database directory exists."""
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True)
            self.logger.info(f"Created database directory: {db_dir}")
            
    def _create_tables(self) -> None:
        """Create necessary database tables."""
        try:
            with self._get_connection() as conn:
                conn.execute(CREATE_TABLE_SIM)
            self.logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create database tables: {e}")
            raise
            
    @contextmanager
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper error handling.
        
        Yields:
            sqlite3.Connection: Database connection
            
        Raises:
            sqlite3.Error: If connection fails
        """
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
            
    def insert_simulation(
        self, 
        sim_hash: str, 
        sim_id: int, 
        fluid_params: str
    ) -> None:
        """Insert a new simulation record.
        
        Args:
            sim_hash: Unique hash identifying the simulation
            sim_id: Simulation ID
            fluid_params: JSON string of fluid parameters
            
        Raises:
            sqlite3.Error: If insertion fails
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    INSERT_SIM, 
                    (sim_hash, sim_id, fluid_params, SimulationStatus.CREATED)
                )
            self.logger.info(f"Inserted simulation record: {sim_hash}")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to insert simulation {sim_hash}: {e}")
            raise
            
    def update_sim_status(self, sim_hash: str, new_status: str) -> None:
        """Update simulation status.
        
        Args:
            sim_hash: Unique hash identifying the simulation
            new_status: New status to set
            
        Raises:
            sqlite3.Error: If update fails
            ValueError: If status is invalid
        """
        if new_status not in vars(SimulationStatus).values():
            raise ValueError(f"Invalid status: {new_status}")
            
        try:
            with self._get_connection() as conn:
                conn.execute(UPDATE_SIM_STATUS, (new_status, sim_hash))
            self.logger.info(f"Updated status for {sim_hash} to {new_status}")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update status for {sim_hash}: {e}")
            raise
            
    def get_sim_by_hash(self, sim_hash: str) -> Optional[Tuple[Any, ...]]:
        """Retrieve simulation record by hash.
        
        Args:
            sim_hash: Unique hash identifying the simulation
            
        Returns:
            Optional[Tuple]: Simulation record if found, None otherwise
            
        Raises:
            sqlite3.Error: If query fails
        """
        try:
            with self._get_connection() as conn:
                cur = conn.execute(GET_SIM_BY_HASH, (sim_hash,))
                row = cur.fetchone()
                if row:
                    self.logger.debug(f"Retrieved simulation record: {sim_hash}")
                else:
                    self.logger.debug(f"No record found for simulation: {sim_hash}")
                return row
        except sqlite3.Error as e:
            self.logger.error(f"Failed to retrieve simulation {sim_hash}: {e}")
            raise

    def get_fluid_params_by_hash(self, sim_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve and parse the fluid_params dictionary for a given simulation hash."""
        query = "SELECT fluid_params FROM simulations WHERE sim_hash = ?"
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(query, (sim_hash,))
                row = cursor.fetchone()
            
            if row and row[0]:
                params_str = row[0]
                try:
                    # Use ast.literal_eval for safe parsing of the dict string
                    params_dict = ast.literal_eval(params_str)
                    if isinstance(params_dict, dict):
                        self.logger.debug(f"Retrieved fluid parameters for hash {sim_hash}.")
                        return params_dict
                    else:
                        # This case should ideally not happen if stored correctly
                        self.logger.error(f"Parsed fluid_params for hash {sim_hash} is not a dict: {type(params_dict)}")
                        return None
                except (ValueError, SyntaxError) as parse_error:
                    self.logger.error(f"Failed to parse fluid_params string for hash {sim_hash}: {parse_error}")
                    self.logger.debug(f"Invalid string was: {params_str}")
                    return None
            else:
                self.logger.warning(f"No fluid_params found in database for sim_hash: {sim_hash}")
                return None
        except sqlite3.Error as e:
            self.logger.error(f"Database error getting fluid_params for hash {sim_hash}: {e}")
            return None
