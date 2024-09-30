import datetime

class Alerts:
    
    def __init__(self, javascript, stored_checksum, new_checksum, date=None):
        """
        Initialize an Alert object with JavaScript content, stored checksum, new checksum, and date.
        """
        self.javascript = javascript
        self.stored_checksum = stored_checksum
        self.new_checksum = new_checksum
        self.date = date or datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    def save_to_db(self, cursor, connection):
        """
        Save the alert to the database.
        """
        cursor.execute('INSERT INTO alerts (javascript, stored_checksum, new_checksum, date) VALUES (?,?,?,?)',
                       (self.javascript, self.stored_checksum, self.new_checksum, self.date))
        connection.commit()

    def __str__(self):
        """
        String representation of the alert.
        """
        return (f"ALERT: Checksum mismatch for JavaScript: {self.javascript}\n"
                f"Stored Checksum: {self.stored_checksum}\n"
                f"New Checksum: {self.new_checksum}\n"
                f"Date: {self.date}")
