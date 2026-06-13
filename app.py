from flask import Flask, render_template, request, redirect, session
import sqlite3
from functools import wraps
from datetime import datetime, timedelta
from flask import make_response
from reportlab.pdfgen import canvas
from io import BytesIO
import qrcode
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'library_secret_key'
# LOGIN REQUIRED
def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if 'user_id' not in session:
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
            session['user_id'] = user[0] 
            session['user'] = user [2]
            session['username'] = user[2]
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

    session.clear()

    return redirect('/login')

# DASHBOARD/Index route
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
    SELECT COUNT(*)
    FROM borrow_books
    WHERE status = 'Borrowed'
    """)
    borrowed_books = cursor.fetchone()[0]

    # RETURNED BOOKS
    cursor.execute("""
    SELECT COUNT(*)
    FROM borrow_books
    WHERE status = 'Returned'
    """)
    returned_books = cursor.fetchone()[0]

    # OVERDUE BOOKS
    cursor.execute("""
    SELECT COUNT(*)
    FROM borrow_books
    WHERE status = 'Overdue'
    """)
    overdue_books = cursor.fetchone()[0]

    # MONTHLY BORROW STATISTICS
    cursor.execute("""
    SELECT
        strftime('%m', borrow_date) AS month,
        COUNT(*)
    FROM borrow_books
    GROUP BY month
    ORDER BY month
    """)

    monthly_data = cursor.fetchall()

    # RECENT ACTIVITIES
    cursor.execute("""
    SELECT *
    FROM activities
    ORDER BY id DESC
    LIMIT 5
    """)
    activities = cursor.fetchall()

    conn.close()

    return render_template(
        'index.html',
        total_books=total_books,
        borrowed_books=borrowed_books,
        returned_books=returned_books,
        overdue_books=overdue_books,
        monthly_data=monthly_data,
        activities=activities
    )
@app.route('/upload_profile', methods=['POST'])
@login_required
def upload_profile():

    image = request.files['photo']

    if image and image.filename != '':

        filename = secure_filename(image.filename)

        image.save(
            os.path.join(
                app.config['UPLOAD_FOLDER'],
                filename
            )
        )

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE users
        SET profile_image = ?
        WHERE id = ?
        """, (
            filename,
            session['user_id']
        ))

        conn.commit()
        conn.close()

    return redirect('/profile')

# ADMIN PROFILE
@app.route('/profile')
@login_required
def profile():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM users
    WHERE username = ?
    """, (session['user'],))

    user = cursor.fetchone()

    conn.close()

    return render_template(
        'profile.html',
        user=user
    )
@app.route('/change_password', methods=['POST'])
@login_required
def change_password():

    old_password = request.form['old_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM users
    WHERE id = ?
    """, (session['user_id'],))

    user = cursor.fetchone()

    # CHECK OLD PASSWORD
    if user[3] != old_password:

        conn.close()

        return """
        <script>
        alert('Old password is incorrect!');
        window.location='/profile';
        </script>
        """

    # CHECK CONFIRM PASSWORD
    if new_password != confirm_password:

        conn.close()

        return """
        <script>
        alert('Passwords do not match!');
        window.location='/profile';
        </script>
        """

    # UPDATE PASSWORD
    cursor.execute("""
    UPDATE users
    SET password = ?
    WHERE id = ?
    """, (
        new_password,
        session['user_id']
    ))

    # SAVE ACTIVITY
    cursor.execute("""
    INSERT INTO activities(activity)
    VALUES(?)
    """, (
        f"Password changed by {user[1]}",
    ))

    conn.commit()
    conn.close()

    return """
    <script>
    alert('Password updated successfully!');
    window.location='/profile';
    </script>
    """

# DISPLAY BOOKS
@app.route('/books')
@login_required
def books():

    search = request.args.get('search', '')
    category = request.args.get('category', '')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if category:

        cursor.execute("""
        SELECT * FROM books
        WHERE title LIKE ?
        AND category = ?
        ORDER BY title COLLATE NOCASE ASC
        """, (
            '%' + search + '%',
            category
        ))

    else:

        cursor.execute("""
        SELECT * FROM books
        WHERE title LIKE ?
        ORDER BY title COLLATE NOCASE ASC
        """, (
            '%' + search + '%',
        ))

    books = cursor.fetchall()

    cursor.execute("""
    SELECT DISTINCT category
    FROM books
    ORDER BY category COLLATE NOCASE ASC
    """)

    categories = cursor.fetchall()

    conn.close()

    return render_template(
        'books.html',
        books=books,
        categories=categories,
        selected_category=category,
        search=search
    )


@app.route('/book/<int:id>')
def book_details(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM books WHERE id = ?",
        (id,)
    )

    book = cursor.fetchone()

    conn.close()

    return render_template(
        'book_details.html',
        book=book
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

        # IMAGE UPLOAD
        image = request.files['cover_image']

        filename = ''

        if image and image.filename != '':

            filename = secure_filename(image.filename)

            image.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO books
        (title, author, category, quantity, cover_image)
        VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            author,
            category,
            quantity,
            filename
        ))

        conn.commit()

        # SAVE ACTIVITY FIRST
        cursor.execute("""
        INSERT INTO activities (activity)
        VALUES (?)
        """, (
        f"New book added: {title}",
        ))

        conn.commit()

        # GET LAST INSERTED BOOK ID
        book_id = cursor.lastrowid

        # GENERATE QR CODE
        #qr = qrcode.make(
       #     f"http://127.0.0.1:5000/book/{book_id}"
       # )
        qr = qrcode.make(
            f"http://192.168.1.5:5000/book/{book_id}"
        )

        # SAVE QR IMAGE
        qr.save(
            f"static/qr_codes/book_{book_id}.png"
        )

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

        #SAVE ACTIVITY
        cursor.execute("""
        INSERT INTO activities (activity)
        VALUES (?)
        """,(
        f"{student_name} borrowed '{book[1]}'",
        ))

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
    current_date = datetime.now()

    updated_records = []

    for record in records:

        due_date = datetime.strptime(record[5], '%Y-%m-%d')

        late_days = 0
        penalty = 0
        status = record[6]

        # CHECK OVERDUE
        if (
            current_date > due_date
            and status == 'Borrowed'
        ):

            late_days = (
                current_date - due_date
            ).days

            penalty = late_days * 5

            status = 'Overdue'

        updated_records.append({
            'id': record[0],
            'student': record[1],
            'book': record[3],
            'borrow_date': record[4],
            'due_date': record[5],
            'status': status,
            'late_days': late_days,
            'penalty': penalty
        })

    return render_template(
        'borrow_records.html',
        records=updated_records
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

    #SAVE ACTIVITY
    cursor.execute("""
     INSERT INTO activities (activity)
     VALUES (?)
      """,(
        f"Book retured: {record[3]}",
                       
    ))

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
        #SAVE ACTIVITY
        cursor.execute("""
         INSERT INTO activities(activity)
        VALUES(?)
        """, (
            f"New member registered: {fullname}",
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
    app.run(host='0.0.0.0', port=5000, debug=True)