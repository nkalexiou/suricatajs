import sqlite3

conn = sqlite3.connect('surikatajs.db')

c = conn.cursor()
c.execute('DROP TABLE alerts')
c.execute('DROP TABLE suricatajs')
conn.commit()
conn.close()