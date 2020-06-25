# suricatajs

Suricatajs is a python program that can be used to monitor webpages, in order to detect unauthorised changes in production javascript. In a commonly used technique, hacking groups alter the code of javascript running on pages, such as those handling credit card or personal information, in order to steal sensitive information. 

By taking snapshots of javascript in scope using cryptographic hashes, Suricatajs can detect unauthorized changes and provide an early warning to defenders.

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

Suricatajs uses an sqlite database and monitors all urls defined in targets.txt. The checksum of each javascript file running on these webpages is generated and saved in the database. With each run a new checksum is generated and compared with the one existing in the database. If these do not match, an alert is created and stored in the database. 

### Extensions and Discussion

The current code is intended to be used as a template and can be greatly extended and customised. As examples of improvements, alerts can be posted to slack channels, new checksums can be set as "accepted" and replace old checksums in the database, ignore-lists of javascript can be created etc.
