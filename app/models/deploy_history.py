import logging
import sqlite3
from flask import current_app

class DeployHistoryModel:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.DB_NAME = current_app.config['DB_NAME']

    def create_deploy_history_table(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS deploy_history (
                    id INTEGER PRIMARY KEY,
                    params_json TEXT,
                    log TEXT,
                    message TEXT,
                    uuid TEXT,
                    result TEXT,
                    start_time INTEGER,
                    endtime INTEGER,
                    key TEXT
                );
            ''')
            c.close()
            conn.commit()
            self._logger.info("Table historyDeploy created successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while creating table historyDeploy: {e}")
        finally:
            conn.close()

    def add_deploy_history(self, params_json, log, message, uuid, result, start_time, endtime, key):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                DELETE FROM deploy_history;
            ''')
            c.execute('''
                INSERT INTO deploy_history (params_json, log, message, uuid, result, start_time, endtime, key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (params_json, log, message, uuid, result, start_time, endtime, key,))
            c.close()
            conn.commit()
            self._logger.info("New deployment added successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while adding new deployment: {e}")
        finally:
            conn.close()

    def get_deploy_history(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                SELECT * FROM deploy_history;
            ''')
            result = c.fetchone()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting deployment by uuid: {e}")
            return None
        finally:
            conn.close()


    def del_deploy_history(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                DELETE FROM deploy_history;
            ''')   
            conn.commit()   
            c.close()
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while DEL deployment: {e}")
        finally:
            conn.close()
            return None

