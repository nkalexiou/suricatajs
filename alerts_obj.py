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
        self.alert_msg = None
        self.alert_type = None


    def save_to_db(self, cursor, connection):
        """
        Save the alert to the database.
        """
        cursor.execute('INSERT INTO alerts (javascript, stored_checksum, new_checksum, date, alert_msg, alert_type) VALUES (?,?,?,?,?,?)',
                       (self.javascript, self.stored_checksum, self.new_checksum, self.date, self.alert_msg, self.alert_type))
        connection.commit()


    def missmatch_alert(self):
        """
        String representation of the alert.
        """
        self.alert_msg = (f"ALERT: Checksum mismatch for JavaScript: {self.javascript}\n"
                f"Stored Checksum: {self.stored_checksum}\n"
                f"New Checksum: {self.new_checksum}\n"
                f"Date: {self.date}")
        
        self.alert_type = 'checksum'
        
        return self.alert_msg    


    def new_script_alert(self):
        """
        String representation of the alert.
        """
        self.alert_msg = (f"ALERT: New script detected: {self.javascript}\n"
                f"Checksum: {self.stored_checksum}\n"
                f"Date: {self.date}")
        
        self.alert_type = 'new_script'
        
        return self.alert_msg
