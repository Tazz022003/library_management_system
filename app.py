from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

# DASHBOARD
@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'index.html',
        total_books=total_books
    )

# DISPLAY BOOKS
# DISPLAY BOOKS
@app.route('/books')
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
def delete_book(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("DELETE FROM books WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect('/books')
# EDIT BOOK
@app.route('/edit_book/<int:id>', methods=['GET', 'POST'])
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
def borrow_book(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # GET BOOK
    cursor.execute("SELECT * FROM books WHERE id = ?", (id,))
    book = cursor.fetchone()

    if request.method == 'POST':

        student_name = request.form['student_name']
        borrow_date = request.form['borrow_date']

        # SAVE BORROW RECORD
        cursor.execute("""
        INSERT INTO borrow_books
        (student_name, book_id, book_title, borrow_date, status)
        VALUES (?, ?, ?, ?, ?)
        """, (
            student_name,
            book[0],
            book[1],
            borrow_date,
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
def borrow_records():

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM borrow_books")
    records = cursor.fetchall()

    conn.close()

    return render_template(
        'borrow_records.html',
        records=records
    )
# RETURN BOOK
@app.route('/return_book/<int:id>')
def return_book(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # GET BORROW RECORD
    cursor.execute("""
    SELECT * FROM borrow_books
    WHERE id = ?
    """, (id,))

    record = cursor.fetchone()

    # UPDATE STATUS
    cursor.execute("""
    UPDATE borrow_books
    SET status = 'Returned'
    WHERE id = ?
    """, (id,))

    # RETURN BOOK QUANTITY
    cursor.execute("""
    UPDATE books
    SET quantity = quantity + 1
    WHERE id = ?
    """, (record[2],))

    conn.commit()
    conn.close()

    return redirect('/borrow_records')

if __name__ == '__main__':
    app.run(debug=True)

