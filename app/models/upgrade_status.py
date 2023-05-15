import logging
import sqlite3
from flask import current_app


class UpgradeStatusModel:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.DB_NAME = current_app.config['DB_NAME']
        self.conn = sqlite3.connect(self.DB_NAME)

    def create_upgrade_status_table(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS upgrade_now_status (
                    id INTEGER PRIMARY KEY,
                    en TEXT,
                    message TEXT,
                    result TEXT,
                    sort INTEGER,
                    zh TEXT
                );
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS upgrade_process_status (
                    id INTEGER PRIMARY KEY,
                    en TEXT,
                    message TEXT,
                    result TEXT,
                    sort INTEGER,
                    zh TEXT
                );
            ''')
            c.close()
            conn.commit()
            self._logger.info("Table upgrade status created successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while creating table upgrade_status: {e}")
        finally:
            conn.close()
            
    def add_upgrade_now_status(self, en, message, result, sort, zh):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute('''
                INSERT INTO upgrade_now_status (en, message, result, sort, zh)
                VALUES (?, ?, ?, ?, ?)
            ''', (en, message, result, sort, zh,))
            c.close()
            conn.commit()
            self._logger.info("New upgrade added successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while adding new upgrade: {e}")
        finally:
            conn.close()
    
    def get_upgrade_now_status(self):
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM upgrade_now_status")
            result = c.fetchall()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting upgrade_now_status: {e}")
            return None
        
    def get_upgrade_process_status(self):
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM upgrade_process_status")
            result = c.fetchall()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting upgrade_process_status: {e}")
            return None

    def get_upgrade_last_status(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute("SELECT message, result FROM upgrade_last_status ORDER BY id DESC LIMIT 1;")
            result = c.fetchone()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting upgrade_last_status: {e}")
            return None
        finally:
            conn.close()
