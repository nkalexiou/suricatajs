import sqlite3

conn = sqlite3.connect('surikatajs.db')

c = conn.cursor()
c.execute('DROP TABLE jsmap')
c.execute('DROP TABLE jschecksum')
c.execute('DROP TABLE alerts')
conn.commit()
conn.close()