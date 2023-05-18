import logging
import sqlite3
from flask import current_app

class ExtendHistoryModel:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.DB_NAME = current_app.config['DB_NAME']

    def create_extend_history_table(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS extend_history (
                    id INTEGER PRIMARY KEY,
                    params_json TEXT,
                    log TEXT,
                    message TEXT,
                    result TEXT,
                    start_time INTEGER,
                    endtime INTEGER
                );
            ''')
            c.close()
            conn.commit()
            self._logger.info("Table extend_history created successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while creating table extend_history: {e}")
        finally:
            conn.close()

    def add_extend_history(self, params_json, log, message, result, start_time, endtime):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                DELETE FROM extend_history;
            ''')
            c.execute('''
                INSERT INTO extend_history (params_json, log, message, result, start_time, endtime)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (params_json, log, message, result, start_time, endtime,))
            c.close()
            conn.commit()
            self._logger.info("New extend info added successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while adding new extend info: {e}")
        finally:
            conn.close()

    def get_extend_history(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                SELECT * FROM extend_history;
            ''')
            result = c.fetchone()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.warning(
                f"Error occurred while getting extendment: {e}")
            return None
        finally:
            conn.close()
