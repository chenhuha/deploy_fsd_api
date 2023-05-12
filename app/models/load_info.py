import logging
import sqlite3
from flask import current_app

class LoadInfoModel:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.DB_NAME = current_app.config['DB_NAME']
        self.conn = sqlite3.connect(self.DB_NAME)

    def create_load_info_table(self):
        try:
            c = self.conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS load_info (
                    uuid INTEGER PRIMARY KEY,
                    info TEXT
                    );
            ''')
            c.close()
            self.conn.commit()
            self._logger.info("Table load_info created successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while creating table load_info: {e}")

    def add_load_info(self, info):
        try:
            c = self.conn.cursor()
            c.execute("SELECT * FROM load_info")
            result = c.fetchone()
            if result:
                c.execute("UPDATE load_info SET info = ? ", (info,))
            else:
                c.execute('''
                    INSERT INTO load_info (info) VALUES (?)
                ''', (info,))
            c.close()
            self.conn.commit()
            self._logger.info("New load_info added successfully")
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while adding new load_info: {e}")

    def get_load_info(self):
        try:
            c = self.conn.cursor()
            c.execute("SELECT info FROM load_info")
            result = c.fetchone()
            c.close()
            return result
        except sqlite3.Error as e:
            self._logger.error(
                f"Error occurred while getting load_info: {e}")
            return None
        