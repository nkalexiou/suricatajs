"""
Main suricatejs file. Contains all scanning login in check() function
"""
import re
import os
import sqlite3
import hashlib
from urllib.parse import urljoin
import subprocess
import datetime
import configparser
import requests
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth

"""
Main functionality
Scans urls, finds javascript, calculates checksums, creates alerts
"""
def check():

    # read config
    config = configparser.ConfigParser()
    config.read('./config/properties.ini')

    http_proxy = ''

    if config['CONFIG']['http_proxy']!='' and config['CONFIG']['port']!='':
        http_proxy = config['CONFIG']['http_proxy']+config['CONFIG']['port']

    conn = sqlite3.connect('surikatajs.db')
    c_cursor = conn.cursor()

    c_cursor.execute('CREATE TABLE IF NOT EXISTS jsmap (url text, javascript text)')
    c_cursor.execute('CREATE TABLE IF NOT EXISTS jschecksum (javascript text, checksum text, date text)')
    c_cursor.execute('CREATE TABLE IF NOT EXISTS alerts (javascript text, stored_checksum text, new_checksum, date text)')

    javascript_set = set()

    with open('targets.txt','r') as targets:
        for targeturl in targets:
            # Find all scripts in webpage
            html_resp = requests.get(targeturl).text
            soup2 = BeautifulSoup(html_resp,features='lxml')
            script_list = soup2.find_all('script')
            # Get src link for each javascript
            for script in script_list:
                try:
                    if 'src' in str(script):
                        print(script)
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
        stored_checksum_cur = c_cursor.execute('SELECT checksum FROM jschecksum WHERE javascript=?',(js,)).fetchone()

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
                print("Creating alert for : "+js)
                print()
                c_cursor.execute('INSERT INTO alerts VALUES (?,?,?,?)', (js,stored_checksum,new_checksum,timestamp))
                conn.commit()
        # If checksum does not exist in database insert a new entry
        else:
            print("checksum insert for :"+js)
            c_cursor.execute('INSERT INTO jschecksum VALUES (?,?,?)',(str(js), new_checksum,timestamp))
            conn.commit()

    conn.close()

if __name__ == "__main__":
    check()
