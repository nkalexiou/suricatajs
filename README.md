# suricatajs

Suricatajs is used to detect unauthorized changes in javascript code, a method often used to inject malware in and digital skimming software in webpages.  Suricatajs works by taking snapshots of a webpage's javascript and comparing those to its database. Snapshots are calculated as hashes to detect changes and when a change is detected an alert is created.

There are two main parts in suricatajs:

* the main python runner which calculates checksums and runs the detection functionality. 
* the flask REST API which exposes the /alerts endpoint, by default on port 8085

The underlying database is sqlite. 

# How to run suricatajs

Before anything update targets.txt with the urls in scope.

## Run locally

Python 3.X required.

pip install -r requirements.txt

Use ```python run.py``` to scan the urls in targets.txt

Make sure that flask is installed
```
pip3 install flask
```

Run the flask API by first setting

```
export FLASK_APP=app.py
```

and then using the following command to run the API

```
flask run --port=8085
```

## Run in Docker

Build the docker containers and run with docker-compose. 

```
docker-compose build --no-cache

docker-compose up -d
```
