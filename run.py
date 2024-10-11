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

conn = sqlite3.connect('./db/surikatajs.db')
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

    # Create a console handler and set the formatter
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

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
    # alert_type: checksum, new_script
    c_cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            javascript TEXT,
            stored_checksum TEXT,
            new_checksum TEXT,
            date TEXT,
            alert_msg TEXT,
            alert_type TEXT
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

            inline_scripts_set = set()

            logger.info(f'Suricatajs working on {targeturl}')

            # Find all scripts in webpage
            html_resp = requests.get(targeturl).text
            soup2 = BeautifulSoup(html_resp, features='lxml')
            script_list = soup2.find_all('script')
            
            for script in script_list:
                try:
                    # Scripts with tags
                    if script.get('src'):
                        script_url = urljoin(targeturl,script['src'])
                        logger.info(f'Working on {script_url}')
                        jssource = requests.get(script_url).text
                        suricata_js = SuricataJSObject(script_url, jssource)

                        # Compare new object and new checksum with database value based on url of script
                        # Compares with the latest available entry from the db (date based)
                        is_match, stored_checksum = suricata_js.compare_with_db(c_cursor)

                        # If there is a previous checksum and there is no match
                        if stored_checksum:
                            if not is_match:
                                # Create a checksum missmatch alert and log it
                                # suricata_js.checksum is the new checksum
                                alert = Alerts(script_url, stored_checksum, suricata_js.checksum)
                                log_msg = alert.missmatch_alert()
                                alert.save_to_db(c_cursor, conn)
                                logger.warning(log_msg)
                                logger.debug(suricata_js.checksum)

                                # store a new object in db with the new checksum and details
                                suricata_js.save_to_db(c_cursor,conn)
                                conn.commit()
                        
                        # when new script is detected
                        else:    
                            # Store script details to db and create new script detected alert
                            alert = Alerts(script_url, None, None)
                            log_msg = alert.new_script_alert()
                            alert.save_to_db(c_cursor,conn)
                            logger.info(log_msg)
                            suricata_js.save_to_db(c_cursor,conn)
                            conn.commit()
                    
                    '''
                    elif script.string:
                        inline_script = script.string.strip()  # Get the inline script content
                        
                        # add the set of inline scripts detected during this run
                        inline_scripts_set.add(inline_script)
                        
                        suricata_js = SuricataJSObject(None, inline_script)

                        checksum, source_exists = suricata_js.find_source_in_db(inline_script,c_cursor)

                        if not source_exists:
                            alert = Alerts(source_exists, None, None)
                            log_msg = alert.new_script_alert()
                            alert.save_to_db(c_cursor,conn)
                            logger.info(log_msg)
                            suricata_js.save_to_db(c_cursor,conn)
                            conn.commit()
                    '''



                except requests.RequestException as e:
                    logger.error(f"Error fetching script from {targeturl}: {e}")
                except KeyError as e:
                    logger.error(f"KeyError processing script in {targeturl}: {e}")
            


    

if __name__ == "__main__":

    db_initiate()
    configure_logger(os.path.expanduser('./log/app.log'))
    check()
    conn.close()
