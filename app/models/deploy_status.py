import logging
import sqlite3
from flask import current_app


class DeployStatusModel:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.DB_NAME = current_app.config['DB_NAME']
        self.conn = sqlite3.connect(self.DB_NAME)

    def create_deploy_status_table(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = self.conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS deploy_now_status (
                    id INTEGER PRIMARY KEY,
                    en TEXT,
                    message TEXT,
                    result TEXT,
                    sort INTEGER,
                    zh TEXT
                );
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS deploy_process_status (
                    id INTEGER PRIMARY KEY,
                    en TEXT,
                    message TEXT,
                    result TEXT,
                    sort INTEGER,
                    zh TEXT
                );
            ''')
            c.close()
            self.conn.commit()
            self._logger.info("Table status created successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while creating table status: {e}")
        finally:
            conn.close()
            
    def get_deploy_now_status(self):
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM deploy_now_status")
            result = c.fetchall()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting deploy_now_status: {e}")
            return None
    
    def get_deploy_last_status(self):
        try:
            conn = sqlite3.connect(self.DB_NAME)
            c = conn.cursor()
            c.execute("SELECT message, result FROM deploy_now_status ORDER BY id DESC LIMIT 1;")
            result = c.fetchone()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting deploy_last_status: {e}")
            return None
        finally:
            conn.close()
        
    def get_deploy_process_status(self):
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM deploy_process_status")
            result = c.fetchall()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting deploy_process_status: {e}")
            return None
