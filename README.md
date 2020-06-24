# suricatajs

Monitor javascript files for unauthorized changes and generate alerts when they are detected. 

### Installation

Python 3.X required.
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

Suricatajs uses a sqlite database and is written in python. It works by parsing urls defined in targets.txt, for javascript references. When a scipr is found a checksum is calculated and inserted in the database if no previous reference for the script exists in the database. 

If the javascript is already monitored (or else exists in the database) then a new checksum is created and compared with the stored one. In case of missmatch an alert is created and inserted in the database.
