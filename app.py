from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = os.path.join('static', 'book_covers')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='admin',
        database='book_shell'
    )


from datetime import datetime, date

@app.route('/')
def home():
    today = date.today()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # Только книги, добавленные сегодня
    cursor.execute('SELECT * FROM books WHERE DATE(created_at) = %s', (today,))
    books_new = cursor.fetchall()
    conn.close()
    return render_template('base.html', books=books_new)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            flash('Пользователь уже существует.', 'danger')
            conn.close()
            return render_template('register.html')
        password_hash = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (%s, %s)', (username, password_hash))
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        # Авторизация
        session['user_id'] = user_id
        session['username'] = username
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('profile'))  # Перенаправление в профиль
    return render_template('register.html')


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Сначала войдите в аккаунт.', 'danger')
        return redirect(url_for('login'))
    return render_template('profile.html', username=session['username'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Добро пожаловать, {}!'.format(username), 'success')
            return redirect(url_for('home'))
        else:
            flash('Неверный логин или пароль.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('login'))


@app.route('/shelf')
def shelf():
    if 'user_id' not in session:
        flash('Сначала войдите в аккаунт.', 'danger')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM books WHERE user_id = %s', (session['user_id'],))
    books = cursor.fetchall()
    conn.close()
    return render_template('shelf.html', books=books)


@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'user_id' not in session:
        flash('Сначала войдите в аккаунт.', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        ebook_link = request.form.get('ebook_link') or None

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO books (user_id, title, author, ebook_link) VALUES (%s, %s, %s, %s)',
            (session['user_id'], title, author, ebook_link)
        )
        conn.commit()
        conn.close()
        flash('Книга добавлена!', 'success')
        return redirect(url_for('shelf'))
    return render_template('add_book.html')


@app.route('/books')
def all_books():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM books')
    books = cursor.fetchall()
    conn.close()
    return render_template('books.html', books=books)


@app.route('/book/<int:book_id>')
def book_detail(book_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
    book = cursor.fetchone()
    conn.close()
    if not book:
        abort(404)
    return render_template('book_detail.html', book=book)


if __name__ == '__main__':
    app.run(debug=True)