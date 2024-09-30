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
from suricatajs_obj import SuricataJSObject as SuricataJSObject
from alerts_obj import Alerts as Alerts

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
    Scans urls, finds javascript, calculates checksums, creates alerts.
    """

    # read config
    config = configparser.ConfigParser()
    config.read('./config/properties.ini')

    with open('targets.txt','r') as targets:
        for targeturl in targets:
            logger.info(f'Suricatajs working on {targeturl}')

            # Find all scripts in webpage
            html_resp = requests.get(targeturl).text
            soup2 = BeautifulSoup(html_resp, features='lxml')
            script_list = soup2.find_all('script')
            
            for script in script_list:
                try:
                    if script.get('src'):
                        logger.debug(script)
                        script_url = urljoin(targeturl,script['src'])
                        jssource = requests.get(script_url).text
                        suricata_js = SuricataJSObject(script_url, jssource)

                        is_match, stored_checksum = suricata_js.compare_with_db(c_cursor)
                        logger.debug('is match: '+str(is_match))
                        logger.debug('stored_checksum: '+str(stored_checksum))

                        if stored_checksum:
                            if not is_match:
                                # Create an alert and log it
                                alert = Alerts(script_url, stored_checksum, suricata_js.checksum)
                                log_msg = alert.__str__()
                                alert.save_to_db(c_cursor, conn)
                                logger.warning(log_msg)
                                conn.commit()

                        else:
                            # when new script is detected                            
                            # Calculate the checksum
                            logger.info(f'New scrupt detected: {script_url}')
                            suricata_js.save_to_db(c_cursor,conn)

                except requests.RequestException as e:
                    logger.error(f"Error fetching script from {targeturl}: {e}")
                except KeyError as e:
                    logger.error(f"KeyError processing script in {targeturl}: {e}")

    

if __name__ == "__main__":

    db_initiate()
    configure_logger(os.path.expanduser('app.log'))
    check()
    conn.close()
