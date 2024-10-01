import hashlib
import datetime

class SuricataJSObject:
    def __init__(self, url, javascript, checksum=None, date=None):
        """
        Initialize a SuricataJS object with the URL, JavaScript content, checksum, and timestamp.
        """
        self.url = url
        self.javascript = javascript
        self.checksum = checksum or self.calculate_checksum(javascript)
        self.date = date or datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    def calculate_checksum(self, javascript):
        """
        Calculate the SHA-256 checksum of the JavaScript content.
        """
        return hashlib.sha256(javascript.encode('utf-8')).hexdigest()

    def save_to_db(self, cursor, connection):
        """
        Save the SuricataJS object to the database.
        """
        cursor.execute('INSERT INTO suricatajs VALUES (?,?,?,?)', (self.url, self.javascript, self.checksum, self.date))
        connection.commit()

    def compare_with_db(self, cursor):
        """
        Compare the current object's checksum with the one stored in the database.
        """

        stored_checksum_cur = cursor.execute('SELECT checksum FROM suricatajs WHERE uri=? ORDER BY date DESC LIMIT 1', (self.url,)).fetchone()
        if stored_checksum_cur:
            stored_checksum = stored_checksum_cur[0]
            return self.checksum == stored_checksum, stored_checksum
        else:
            return False, None
    
    def find_source_in_db(self, source, cursor):
        """
        Fetch script from db using the Javascript content
        """
        stored_checksum_cur = cursor.execute('SELECT checksum FROM suricatajs WHERE javascript=?', (source,)).fetchone()

        if stored_checksum_cur:
            stored_checksum = stored_checksum_cur[0]
            return stored_checksum, True
        else:
            return None, False

