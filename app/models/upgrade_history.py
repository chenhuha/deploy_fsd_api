import logging
import sqlite3
from flask import current_app

class UpgradeHistoryModel:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.DB_NAME = current_app.config['DB_NAME']

    def create_upgrade_history_table(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS upgrade_history (
                    id INTEGER PRIMARY KEY,
                    version TEXT,
                    new_version TEXT,
                    result TEXT,
                    message TEXT,
                    endtime INTEGER,
                    upgrade_path TEXT
                );
            ''')
            c.close()
            conn.commit()
            self._logger.info("Table upgrade_history created successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while creating table upgrade_history: {e}")
        finally:
            conn.close()

    def add_upgrade_history(self, version, new_version, result, message, endtime):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                DELETE FROM upgrade_history;
            ''')
            c.execute('''
                INSERT INTO upgrade_history (version, new_version, result, message, endtime)
                VALUES (?, ?, ?, ?, ?)
            ''', (version, new_version, result, message, endtime))
            c.close()
            conn.commit()
            self._logger.info("New upgrade_history added successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while adding new upgrade_history: {e}")
        finally:
            conn.close()
    
    def update_upgrade_history(self, result, message, endtime, upgrade_path):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                UPDATE upgrade_history SET result = ?, message = ?, endtime = ?, upgrade_path = ? WHERE id = (
                SELECT id FROM upgrade_history ORDER BY id DESC LIMIT 1);
            ''', (result, message, endtime, upgrade_path))
            c.close()
            conn.commit()
            self._logger.info("upgrade_history update successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while update new upgrade_history: {e}")
        finally:
            conn.close()

    def get_upgrade_all_history(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                SELECT * FROM upgrade_history;
            ''')
            result = c.fetchall()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting upgrade_history : {e}")
            return None
        finally:
            conn.close()
    
    def get_upgrade_version(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                SELECT new_version FROM upgrade_history ORDER BY id DESC LIMIT 1;
            ''')
            result = c.fetchone()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting version : {e}")
            return None
        finally:
            conn.close()

    def get_upgrade_path(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                SELECT upgrade_path FROM upgrade_history 
                WHERE result = 'true' and  version IS NOT NULL
                ORDER BY id DESC LIMIT 1;
            ''')
            result = c.fetchone()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting version : {e}")
            return None
        finally:
            conn.close()