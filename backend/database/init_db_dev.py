import mysql.connector

from subprocess import Popen, PIPE

dbName = "agents"

# (Old block, commented out)
process = Popen(['mysql', dbName, '-u', 'root'],
                stdout=PIPE, stdin=PIPE)
output = process.communicate(b'source ' + b'schema.sql')[0]
connection = mysql.connector.connect(
    user='root',
    unix_socket='/tmp/mysql.sock',
    database=dbName,
)

# (New block, using TCP connection via Docker service 'db')
# connection = mysql.connector.connect(
#     host="db",  # Use the Docker service name (db) for TCP connection
#     # port=3306,  # (Optional) specify the port if not default
#     user="root",
#     # (Removed password parameter so that no password is passed, as in the commented block)
#     database=dbName,
# )

# Create a cursor
cur = connection.cursor()

# Close the connection
connection.close()

# import mysql.connector
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # Connect to MySQL using Docker service 'db'
# print("Connecting to MySQL database...")

# options = {
#     "host": os.getenv("DB_HOST", "db"),
#     "user": os.getenv("DB_USER", "root"),
#     "password": os.getenv("DB_PASSWORD", "").strip('"') or None,
#     "database": os.getenv("DB_NAME", "agents"),
#     "port": int(os.getenv("DB_PORT", 3306)),
# }

# connection = mysql.connector.connect(
#     host=options["host"],
#     user=options["user"],
#     password=options["password"],
#     database=options["database"],
#     port=options["port"],
# )

# cur = connection.cursor()

# # Read and execute schema
# project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")

# with open(schema_path, encoding='utf8') as f:
#     sql_script = f.read()
#     for result in cur.execute(sql_script, multi=True):
#         pass  # Optionally log result

# cur.execute("SELECT * FROM users WHERE id = 1")
# result = cur.fetchone()

# if result is None:
#     print("Inserting dummy user with ID 1...")
#     cur.execute("""
#         INSERT INTO users (id, email, person_name, credits)
#         VALUES (0, 'anon@anote.ai', 'Anonymous', 0)
#     """)
#     connection.commit()
# else:
#     print("Dummy user already exists.")

# connection.commit()
# cur.close()
# connection.close()

# print("Database initialized successfully.")
