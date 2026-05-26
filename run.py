"""
Main suricatajs file. Scanner logic lives in check().
"""
import configparser
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from alerts_obj import Alerts
from db.database import init_db
from suricatajs_obj import SuricataJSObject

logger = logging.getLogger("suricatajs")


def configure_logger(log_file):
    logger.setLevel(logging.DEBUG)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=7)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def check(targets_file="targets.txt"):
    """
    Scan all targets, compute checksums, create alerts on change or new script.
    targets_file: path to the targets list (one URL per line).
    """
    config = configparser.ConfigParser()
    config.read("./config/properties.ini")

    with open(targets_file, "r") as f:
        for line in f:
            targeturl = line.strip()
            if not targeturl:
                continue

            logger.info(f"Scanning {targeturl}")

            try:
                html_resp = requests.get(targeturl, timeout=30).text
                soup = BeautifulSoup(html_resp, features="lxml")

                for script in soup.find_all("script"):
                    if not script.get("src"):
                        continue
                    try:
                        script_url = urljoin(targeturl, script["src"])
                        logger.info(f"Processing {script_url}")
                        jssource = requests.get(script_url, timeout=30).text
                        suricata_js = SuricataJSObject(script_url, jssource)

                        is_match, stored_checksum = suricata_js.compare_with_db()

                        if stored_checksum is not None:
                            if not is_match:
                                alert = Alerts(script_url, stored_checksum, suricata_js.checksum)
                                logger.warning(alert.missmatch_alert())
                                alert.save_to_db()
                                suricata_js.save_to_db()
                        else:
                            alert = Alerts(script_url, None, None)
                            logger.info(alert.new_script_alert())
                            alert.save_to_db()
                            suricata_js.save_to_db()

                    except requests.RequestException as e:
                        logger.error(f"Error fetching script: {e}")

            except requests.RequestException as e:
                logger.error(f"Error fetching {targeturl}: {e}")


if __name__ == "__main__":
    init_db()
    configure_logger(os.path.expanduser("./log/app.log"))
    check()
