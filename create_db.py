import sqlite3

conn = sqlite3.connect('database.db')

cursor = conn.cursor()

# CREATE USERS TABLE
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fullname TEXT,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
''')

# DEFAULT ADMIN ACCOUNT
cursor.execute("""
INSERT INTO users (fullname, username, password, role)
SELECT 'Administrator', 'admin', 'admin123', 'admin'
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE username = 'admin'
)
""")

# CREATE BOOKS TABLE
cursor.execute('''
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    cover_image TEXT
)
''')

# CREATE BORROW TABLE
cursor.execute('''
CREATE TABLE IF NOT EXISTS borrow_books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    book_id INTEGER NOT NULL,
    book_title TEXT NOT NULL,
    borrow_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL
)
''')


conn.commit()
conn.close()



print("Database created successfully!")