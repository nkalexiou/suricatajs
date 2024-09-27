"""
Main suricatejs file. Contains all scanning login in check() function
"""
import sqlite3
import hashlib
from urllib.parse import urljoin
import datetime
from logging.handlers import TimedRotatingFileHandler
import configparser
import requests
import logging
from bs4 import BeautifulSoup
import os

conn = sqlite3.connect('surikatajs.db')
c_cursor = conn.cursor()

logger = logging.getLogger("my_logger")

def configure_logger(log_file):
    # Create a logger
    logger.setLevel(logging.DEBUG)

    # Create a formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Create a file handler and set the formatter
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)

    return logger


def db_initiate():
    logger.info('Creating database tables')

    c_cursor.execute('''
        CREATE TABLE IF NOT EXISTS suricatajs (
            uri TEXT,
            javascript TEXT,
            checksum TEXT,
            date TEXT
        )
    ''')

    # Create the 'alerts' table to store alerts related to checksum changes
    c_cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            javascript TEXT,
            stored_checksum TEXT,
            new_checksum TEXT,
            date TEXT
        )
    ''')

    logger.info('Database tables created successfully')


def compare(stored_checksum, new_checksum):
    if stored_checksum == new_checksum:
        return True
    else:
        logger.warning(f'Checksum mismatch! Stored: {stored_checksum}, New: {new_checksum}')
        return False


def check():
    """
    Main functionality
    Scans urls, finds javascript, calculates checksums, creates alerts
    """

    # read config
    config = configparser.ConfigParser()
    config.read('./config/properties.ini')

    javascript_set = set()

    with open('targets.txt','r') as targets:
        for targeturl in targets:
            logger.info(f'Suricatajs working on {targeturl}')
            # Find all scripts in webpage
            html_resp = requests.get(targeturl).text
            soup2 = BeautifulSoup(html_resp, features='lxml')
            script_list = soup2.find_all('script')
            # Get src link for each javascript
            for script in script_list:
                try:
                    if script.get('src'):
                        logger.debug(script)
                        script_url = urljoin(targeturl,script['src'])
                        #javascript_set.add(script_url)
                        stored_checksum_cur = c_cursor.execute('SELECT checksum FROM suricatajs WHERE javascript=?', (script_url,)).fetchone()
                        if stored_checksum_cur:
                            jssource = requests.get(script_url).text
                            # Calculate the checksum
                            new_checksum = hashlib.sha256(jssource.encode(encoding='utf-8')).hexdigest()
                            result = compare(stored_checksum_cur[0],new_checksum)
                            if result == False:
                                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                                c_cursor.execute('INSERT INTO alerts VALUES (?,?,?,?)', (script_url, stored_checksum_cur[0] , new_checksum,timestamp))
                                conn.commit()

                        else:
                            # when new script is detected
                            jssource = requests.get(script_url).text
                            # Calculate the checksum
                            new_checksum = hashlib.sha256(jssource.encode(encoding='utf-8')).hexdigest()
                            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            c_cursor.execute('INSERT INTO suricatajs VALUES (?,?,?,?)', (targeturl, script_url, new_checksum,timestamp))
                            conn.commit()
                        
                except (KeyError, requests.RequestsException) as e:
                    logger.error(f"Error reading script or fetching JavaScript source from {targeturl}: {e}")

    

if __name__ == "__main__":

    db_initiate()
    configure_logger(os.path.expanduser('app.log'))
    check()
    conn.close()
