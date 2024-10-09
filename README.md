# suricatajs

Suricatajs is used to detect unauthorized changes in javascript code, a method often used to inject malware in and digital skimming software in webpages.  Suricatajs works by taking snapshots of a webpage's javascript and comparing those to its database. Snapshots are calculated as hashes to detect changes and when a change is detected an alert is created. 

### Installation

Python 3.X required.

pip install -r requirements.txt

Test by ```python run.py```

### How to use

Update targets.txt with the urls in scope as shown below:

```
https://www.yourwebsite1.com/test1
https://www.yourwebsite2.com/test2
````

Run manually or schedule the command
```
python run.py
````

### Functionality

Suricatajs uses an sqlite database and monitors all urls defined in targets.txt. The checksum of each javascript file running on these webpages is generated and saved in the database. With each run a new checksum is generated and compared with the one existing in the database. If these do not match, an alert is created and stored in the database. 

### Extensions and Discussion

The current code is intended to be used as a template and can be greatly extended and customised. As examples of improvements, alerts can be posted to slack channels, new checksums can be set as "accepted" and replace old checksums in the database, ignore-lists of javascript can be created etc.

### Starting the Flask API

Make sure that flask is installed
```
pip3 install flask
```

Then export the env variable for mac OS

```
export FLASK_APP=app.py
```

Do ``` flask run ``` from the directory hosting app.py
