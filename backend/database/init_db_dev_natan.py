import mysql.connector

from subprocess import Popen, PIPE

dbName = "agents"

process = Popen(['mysql', dbName, '-u', 'root'],
                stdout=PIPE, stdin=PIPE)
output = process.communicate(b'source ' + b'schema.sql')[0]
connection = mysql.connector.connect(
    user='root',
    unix_socket='/tmp/mysql.sock',
    database=dbName,
)

# Create a cursor
cur = connection.cursor()

# Close the connection
connection.close()