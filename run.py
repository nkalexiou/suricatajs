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

    # Create the 'jsmap' table to map URLs to JavaScript code
    c_cursor.execute('''
        CREATE TABLE IF NOT EXISTS jsmap (
            url TEXT,
            javascript TEXT
        )
    ''')

    # Create the 'jschecksum' table to store JavaScript checksums and their dates
    c_cursor.execute('''
        CREATE TABLE IF NOT EXISTS jschecksum (
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


def check():
    """
    Main functionality
    Scans urls, finds javascript, calculates checksums, creates alerts
    """

    # read config
    config = configparser.ConfigParser()
    config.read('./config/properties.ini')

    db_initiate()
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
                    if 'src' in str(script):
                        logger.info(script)
                        script_url = urljoin(targeturl,script['src'])
                        # Add all scipts to set and map javascript to webpage
                        javascript_set.add(script_url)
                        c_cursor.execute('INSERT INTO jsmap SELECT ?,? WHERE NOT EXISTS (SELECT 1 FROM jsmap WHERE url=? AND javascript=?)', (targeturl, script_url, targeturl, script_url))
                        conn.commit()
                except KeyError:
                    print("Error reading script source")

    # For each of the detected scripts
    for j_script in javascript_set:
        jssource = requests.get(j_script).text
        # Calculate the checksum
        new_checksum = hashlib.sha256(jssource.encode(encoding='utf-8')).hexdigest()

        # Check if checksum alrady exists in database
        stored_checksum_cur = c_cursor.execute('SELECT checksum FROM jschecksum WHERE javascript=?', (j_script,)).fetchone()

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        # If checksum already exists then compare with new checksum
        if stored_checksum_cur:
            print(stored_checksum_cur[0])
            stored_checksum=stored_checksum_cur[0]
            # If new and old checksum do not match then create alert
            if new_checksum != stored_checksum:
                print()
                print("//////////////////////////")
                print("//////   WARNING   ///////")
                print("//////////////////////////")
                print("A new checksum was detected: "+new_checksum+" that doesn't match the value stored in the database.")
                print("Creating alert for : "+j_script)
                print()
                c_cursor.execute('INSERT INTO alerts VALUES (?,?,?,?)', (j_script,stored_checksum, new_checksum, timestamp))
                conn.commit()
        # If checksum does not exist in database insert a new entry
        else:
            print("checksum insert for :"+j_script)
            c_cursor.execute('INSERT INTO jschecksum VALUES (?,?,?)', (str(j_script), new_checksum, timestamp))
            conn.commit()

    conn.close()

if __name__ == "__main__":

    db_initiate()
    configure_logger(os.path.expanduser('app.log'))
    check()
