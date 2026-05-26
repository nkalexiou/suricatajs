import hashlib
import datetime
from sqlalchemy import text
from db.database import get_connection


class SuricataJSObject:
    def __init__(self, url, javascript, checksum=None, date=None):
        self.url = url
        self.javascript = javascript
        self.checksum = checksum or self._calculate_checksum(javascript)
        if date is None:
            now = datetime.datetime.now()
            self.date = now.strftime('%Y%m%d_%H%M%S%f')
        else:
            self.date = date

    def _calculate_checksum(self, javascript):
        return hashlib.sha256(javascript.encode('utf-8')).hexdigest()

    def save_to_db(self):
        with get_connection() as conn:
            conn.execute(
                text("INSERT INTO suricatajs (uri, javascript, checksum, date) "
                     "VALUES (:uri, :javascript, :checksum, :date)"),
                {"uri": self.url, "javascript": self.javascript,
                 "checksum": self.checksum, "date": self.date},
            )

    def compare_with_db(self):
        with get_connection() as conn:
            row = conn.execute(
                text("SELECT checksum FROM suricatajs WHERE uri=:uri "
                     "ORDER BY date DESC LIMIT 1"),
                {"uri": self.url},
            ).fetchone()
        if row:
            stored = row[0]
            return self.checksum == stored, stored
        return False, None

    def find_source_in_db(self, source):
        with get_connection() as conn:
            row = conn.execute(
                text("SELECT checksum FROM suricatajs WHERE javascript=:javascript"),
                {"javascript": source},
            ).fetchone()
        if row:
            return row[0], True
        return None, False
