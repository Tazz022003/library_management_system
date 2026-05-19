from flask import Flask, render_template, request, redirect, session
import sqlite3
from functools import wraps
from datetime import datetime, timedelta
from flask import make_response
from reportlab.pdfgen import canvas
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'library_secret_key'

# LOGIN REQUIRED
def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'user' not in session:
            return redirect('/login')

        return f(*args, **kwargs)

    return decorated_function


# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM users
        WHERE username = ? AND password = ?
        """, (username, password))

        user = cursor.fetchone()

        conn.close()

        if user:

            session['user'] = user[2]
            session['role'] = user[4]

            if user[4] == 'admin':
                return redirect('/')

            else:
                return redirect('/student_dashboard')

        else:

            return "Invalid username or password"

    return render_template('login.html')


# LOGOUT
@app.route('/logout')
def logout():

    session.pop('user', None)

    return redirect('/login')


# DASHBOARD
@app.route('/')
@login_required
def index():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # TOTAL BOOKS
    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    # BORROWED BOOKS
    cursor.execute("""
    SELECT COUNT(*) FROM borrow_books
    WHERE status = 'Borrowed'
    """)
    borrowed_books = cursor.fetchone()[0]

    # RETURNED BOOKS
    cursor.execute("""
    SELECT COUNT(*) FROM borrow_books
    WHERE status = 'Returned'
    """)
    returned_books = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'index.html',
        total_books=total_books,
        borrowed_books=borrowed_books,
        returned_books=returned_books
    )


# DISPLAY BOOKS
@app.route('/books')
@login_required
def books():

    search = request.args.get('search', '')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM books
    WHERE title LIKE ?
    """, ('%' + search + '%',))

    books = cursor.fetchall()

    conn.close()

    return render_template(
        'books.html',
        books=books
    )


# ADD BOOK
@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():

    if request.method == 'POST':

        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        quantity = request.form['quantity']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO books (title, author, category, quantity)
        VALUES (?, ?, ?, ?)
        """, (title, author, category, quantity))

        conn.commit()
        conn.close()

        return redirect('/books')

    return render_template('add_book.html')


# DELETE BOOK
@app.route('/delete_book/<int:id>')
@login_required
def delete_book(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM books WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect('/books')


# EDIT BOOK
@app.route('/edit_book/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_book(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':

        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        quantity = request.form['quantity']

        cursor.execute("""
        UPDATE books
        SET title=?, author=?, category=?, quantity=?
        WHERE id=?
        """, (title, author, category, quantity, id))

        conn.commit()
        conn.close()

        return redirect('/books')

    cursor.execute("SELECT * FROM books WHERE id = ?", (id,))
    book = cursor.fetchone()

    conn.close()

    return render_template(
        'edit_book.html',
        book=book
    )

# BORROW BOOK
@app.route('/borrow_book/<int:id>', methods=['GET', 'POST'])
@login_required
def borrow_book(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # GET BOOK
    cursor.execute("SELECT * FROM books WHERE id = ?", (id,))
    book = cursor.fetchone()

    if request.method == 'POST':

        # CHECK IF BOOK AVAILABLE
        if book[4] <= 0:

            conn.close()

            return "Book is out of stock"

        student_name = request.form['student_name']
        borrow_date = request.form['borrow_date']

        # AUTO DUE DATE = 7 DAYS
        due_date = (
            datetime.strptime(borrow_date, '%Y-%m-%d')
            + timedelta(days=7)
        ).strftime('%Y-%m-%d')

        # SAVE BORROW RECORD
        cursor.execute("""
        INSERT INTO borrow_books
        (student_name, book_id, book_title, borrow_date, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            student_name,
            book[0],
            book[1],
            borrow_date,
            due_date,
            'Borrowed'
        ))

        # REDUCE QUANTITY
        new_quantity = book[4] - 1

        cursor.execute("""
        UPDATE books
        SET quantity = ?
        WHERE id = ?
        """, (new_quantity, id))

        conn.commit()
        conn.close()

        return redirect('/borrow_records')

    conn.close()

    return render_template(
        'borrow_book.html',
        book=book
    )


# BORROW RECORDS
@app.route('/borrow_records')
@login_required
def borrow_records():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM borrow_books")
    records = cursor.fetchall()

    conn.close()

    # CURRENT DATE
    current_date = datetime.now().strftime('%Y-%m-%d')

    return render_template(
        'borrow_records.html',
        records=records,
        current_date=current_date
    )


# RETURN BOOK
@app.route('/return_book/<int:id>')
@login_required
def return_book(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM borrow_books
    WHERE id = ?
    """, (id,))

    record = cursor.fetchone()

    cursor.execute("""
    UPDATE borrow_books
    SET status = 'Returned'
    WHERE id = ?
    """, (id,))

    cursor.execute("""
    UPDATE books
    SET quantity = quantity + 1
    WHERE id = ?
    """, (record[2],))

    conn.commit()
    conn.close()

    return redirect('/borrow_records')

# STUDENT REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO users
        (fullname, username, password, role)
        VALUES (?, ?, ?, ?)
        """, (
            fullname,
            username,
            password,
            'student'
        ))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')

# STUDENT DASHBOARD
@app.route('/student_dashboard')
@login_required
def student_dashboard():

    if session['role'] != 'student':
        return redirect('/')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()

    conn.close()

    return render_template(
        'student_dashboard.html',
        books=books
    )
# PDF REPORT
@app.route('/generate_report')
@login_required
def generate_report():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM borrow_books
    """)

    records = cursor.fetchall()

    conn.close()

    # CREATE PDF
    buffer = BytesIO()

    p = canvas.Canvas(buffer)

    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "Library Borrow Report")

    y = 760

    p.setFont("Helvetica", 11)

    for record in records:

        text = (
            f"Student: {record[1]} | "
            f"Book: {record[3]} | "
            f"Borrow Date: {record[4]} | "
            f"Due Date: {record[5]} | "
            f"Status: {record[6]}"
        )

        p.drawString(40, y, text)

        y -= 25

        # NEW PAGE IF FULL
        if y < 50:

            p.showPage()

            y = 800

    p.save()

    buffer.seek(0)

    response = make_response(buffer.getvalue())

    response.headers['Content-Type'] = 'application/pdf'

    response.headers['Content-Disposition'] = (
        'inline; filename=library_report.pdf'
    )

    return response


if __name__ == '__main__':
    app.run(debug=True)