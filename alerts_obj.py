import datetime
from sqlalchemy import text
from db.database import get_connection


class Alerts:
    def __init__(self, javascript, stored_checksum, new_checksum, date=None):
        self.javascript = javascript
        self.stored_checksum = stored_checksum
        self.new_checksum = new_checksum
        if date is None:
            now = datetime.datetime.now()
            self.date = now.strftime('%Y%m%d_%H%M%S')
        else:
            self.date = date
        self.alert_msg = None
        self.alert_type = None

    def save_to_db(self):
        with get_connection() as conn:
            conn.execute(
                text("INSERT INTO alerts "
                     "(javascript, stored_checksum, new_checksum, date, alert_msg, alert_type) "
                     "VALUES (:javascript, :stored_checksum, :new_checksum, :date, :alert_msg, :alert_type)"),
                {
                    "javascript": self.javascript,
                    "stored_checksum": self.stored_checksum,
                    "new_checksum": self.new_checksum,
                    "date": self.date,
                    "alert_msg": self.alert_msg,
                    "alert_type": self.alert_type,
                },
            )

    def missmatch_alert(self):
        self.alert_msg = (
            f"ALERT: Checksum mismatch for JavaScript: {self.javascript}\n"
            f"Stored Checksum: {self.stored_checksum}\n"
            f"New Checksum: {self.new_checksum}\n"
            f"Date: {self.date}"
        )
        self.alert_type = "checksum"
        return self.alert_msg

    def new_script_alert(self):
        self.alert_msg = (
            f"ALERT: New script detected: {self.javascript}\n"
            f"Checksum: {self.stored_checksum}\n"
            f"Date: {self.date}"
        )
        self.alert_type = "new_script"
        return self.alert_msg
