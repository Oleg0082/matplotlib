import re
import os
import sqlite3
import matplotlib.pyplot as plt
from matplotlib import use
from flask import Flask, request, render_template, jsonify, redirect, url_for, session
from werkzeug.middleware.proxy_fix import ProxyFix

use('Agg')

app = Flask(__name__)
app.secret_key = 'some_very_secret_key'  # Cambiar por una clave segura
app.wsgi_app = ProxyFix(app.wsgi_app)

DB_NAME = 'graficaspersonales.sqlite3'
STATIC_DIR = 'static'

def is_valid_stat_name(name):
    return bool(re.match(r'^[A-Za-z0-9_]+$', name))

def get_db_conn():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    # Tabla de usuarios
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    ''')
    # Tabla de configuracion de dataset
    c.execute('''
    CREATE TABLE IF NOT EXISTS dataset_config (
        stat_name TEXT,
        user_id INTEGER,
        chart_type TEXT,
        chart_color TEXT,
        PRIMARY KEY(stat_name, user_id)
    )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user_id():
    return session.get('user_id')

def user_is_logged_in():
    return 'user_id' in session

def get_datasets_for_user(user_id):
    if not os.path.exists(DB_NAME):
        return []
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT stat_name FROM dataset_config WHERE user_id = ?", (user_id,))
    datasets = [row[0] for row in c.fetchall()]
    conn.close()
    return datasets

def get_dataset_config(user_id, stat_name):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT chart_type, chart_color FROM dataset_config WHERE stat_name=? AND user_id=?", (stat_name, user_id))
    row = c.fetchone()
    conn.close()
    if row:
        return {'chart_type': row[0], 'chart_color': row[1]}
    return {'chart_type': 'bar', 'chart_color': '#4CAF50'}

def full_table_name(user_id, stat_name):
    return f"user_{user_id}_{stat_name}"

def generate_charts_for_user(user_id):
    datasets = get_datasets_for_user(user_id)
    conn = get_db_conn()
    c = conn.cursor()
    for ds in datasets:
        table = full_table_name(user_id, ds)
        c.execute(f'SELECT etiqueta, valor FROM "{table}"')
        rows = c.fetchall()
        etiquetas = [r[0] for r in rows if r[1] is not None]
        valores = [float(r[1]) for r in rows if r[1] is not None]

        plt.figure().clear()
        plt.close()
        plt.clf()

        if len(etiquetas) > 0 and len(valores) > 0:
            config = get_dataset_config(user_id, ds)
            chart_type = config['chart_type']
            chart_color = config['chart_color']

            plt.figure(figsize=(4,3))
            if chart_type == 'bar':
                plt.bar(etiquetas, valores, color=chart_color)
                plt.title(f'{ds}', fontsize=12, fontweight='bold')
            elif chart_type == 'pie':
                plt.pie(valores, labels=etiquetas, autopct='%1.1f%%')
                plt.title(f'{ds}', fontsize=12, fontweight='bold')

            plt.tight_layout()
            plt.savefig(f"{STATIC_DIR}/{user_id}_{ds}.png")
            plt.close()
        else:
            # Si no hay datos, borrar imagen existente
            img_path = os.path.join(STATIC_DIR, f"{user_id}_{ds}.png")
            if os.path.exists(img_path):
                os.remove(img_path)
    conn.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        conn = get_db_conn()
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username=?", (username,))
        row = c.fetchone()
        conn.close()
        if row and row[1] == password:
            session['user_id'] = row[0]
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Usuario o contraseña incorrectos")
    return render_template('login.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        if not username or not password:
            return render_template('signup.html', error="Se requieren nombre de usuario y contraseña")
        conn = get_db_conn()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('signup.html', error="El nombre de usuario ya existe")
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not user_is_logged_in():
        return redirect(url_for('login'))
    generate_charts_for_user(get_user_id())
    datasets = get_datasets_for_user(get_user_id())
    return render_template('index.html', datasets=datasets, user_id=get_user_id())

@app.route('/datasets', methods=['GET'])
def list_datasets():
    if not user_is_logged_in():
        return jsonify([])
    user_id = get_user_id()
    datasets = get_datasets_for_user(user_id)
    return jsonify(datasets)

@app.route('/create_dataset', methods=['POST'])
def create_dataset():
    if not user_is_logged_in():
        return jsonify({'error': 'No ha iniciado sesión'}), 403

    user_id = get_user_id()
    stat_name = request.form.get('stat_name', '').strip()
    chart_type = request.form.get('chart_type', 'bar').strip()
    chart_color = request.form.get('chart_color', '#4CAF50').strip()

    if not stat_name:
        return jsonify({'error': 'El nombre de la estadística no puede estar vacío'}), 400
    if not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Nombre de estadística inválido. Use solo letras, dígitos y guiones bajos.'}), 400
    if chart_type not in ['bar', 'pie']:
        return jsonify({'error': 'Tipo de gráfico inválido. Debe ser barras o pastel.'}), 400
    if chart_type == 'pie':
        chart_color = ''

    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dataset_config WHERE user_id=? AND stat_name=?", (user_id, stat_name))
    if c.fetchone()[0] > 0:
        conn.close()
        return jsonify({'error': 'Ya existe una estadística con ese nombre para este usuario.'}), 400

    table_name = full_table_name(user_id, stat_name)
    c.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" (etiqueta TEXT, valor REAL)')
    c.execute('REPLACE INTO dataset_config (stat_name, user_id, chart_type, chart_color) VALUES (?,?,?,?)',
              (stat_name, user_id, chart_type, chart_color))
    conn.commit()
    conn.close()

    generate_charts_for_user(user_id)

    return jsonify({'result': 'ok', 'dataset': stat_name})

@app.route('/envia', methods=['POST'])
def envia():
    if not user_is_logged_in():
        return jsonify({'error': 'No ha iniciado sesión'}), 403

    user_id = get_user_id()
    stat_name = request.form.get('stat_name', '').strip()
    etiqueta = request.form.get('etiqueta', '').strip()
    valor = request.form.get('valor', '').strip()

    if not stat_name or not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Nombre de estadística inválido.'}), 400
    if not etiqueta:
        return jsonify({'error': 'La etiqueta no puede estar vacía.'}), 400
    try:
        valor = float(valor)
    except (ValueError, TypeError):
        return jsonify({'error': 'El valor debe ser un número válido.'}), 400

    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dataset_config WHERE user_id=? AND stat_name=?", (user_id, stat_name))
    if c.fetchone()[0] == 0:
        conn.close()
        return jsonify({'error': 'No existe esta estadística para el usuario actual.'}), 404

    table_name = full_table_name(user_id, stat_name)
    c.execute(f'INSERT INTO "{table_name}" (etiqueta, valor) VALUES (?,?)', (etiqueta, valor))
    conn.commit()
    conn.close()

    generate_charts_for_user(user_id)

    return jsonify({'resultado': 'ok'})

@app.route('/labels_for_dataset', methods=['GET'])
def labels_for_dataset():
    if not user_is_logged_in():
        return jsonify([])

    user_id = get_user_id()
    stat_name = request.args.get('stat_name', '').strip()
    if not stat_name or not is_valid_stat_name(stat_name):
        return jsonify([])
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dataset_config WHERE user_id=? AND stat_name=?", (user_id, stat_name))
    if c.fetchone()[0] == 0:
        conn.close()
        return jsonify([])
    table_name = full_table_name(user_id, stat_name)
    c.execute(f'SELECT etiqueta FROM "{table_name}"')
    labels = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify(labels)

@app.route('/delete_record', methods=['POST'])
def delete_record():
    if not user_is_logged_in():
        return jsonify({'error': 'No ha iniciado sesión'}), 403

    user_id = get_user_id()
    stat_name = request.form.get('stat_name', '').strip()
    etiqueta = request.form.get('etiqueta', '').strip()

    if not stat_name or not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Nombre de estadística inválido'}), 400
    if not etiqueta:
        return jsonify({'error': 'La etiqueta no puede estar vacía.'}), 400

    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dataset_config WHERE user_id=? AND stat_name=?", (user_id, stat_name))
    if c.fetchone()[0] == 0:
        conn.close()
        return jsonify({'error': 'No existe esta estadística para el usuario actual'}), 404

    table_name = full_table_name(user_id, stat_name)
    c.execute(f'DELETE FROM "{table_name}" WHERE etiqueta = ?', (etiqueta,))
    conn.commit()
    conn.close()

    generate_charts_for_user(user_id)

    return jsonify({'result': 'ok'})

@app.route('/update_record', methods=['POST'])
def update_record():
    if not user_is_logged_in():
        return jsonify({'error': 'No ha iniciado sesión'}), 403

    user_id = get_user_id()
    stat_name = request.form.get('stat_name', '').strip()
    etiqueta = request.form.get('etiqueta', '').strip()
    valor = request.form.get('valor', '').strip()

    if not stat_name or not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Nombre de estadística inválido'}), 400
    if not etiqueta:
        return jsonify({'error': 'La etiqueta no puede estar vacía.'}), 400
    try:
        valor = float(valor)
    except ValueError:
        return jsonify({'error': 'El valor debe ser un número válido'}), 400

    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dataset_config WHERE user_id=? AND stat_name=?", (user_id, stat_name))
    if c.fetchone()[0] == 0:
        conn.close()
        return jsonify({'error': 'No existe esta estadística para el usuario actual'}), 404

    table_name = full_table_name(user_id, stat_name)
    c.execute(f'UPDATE "{table_name}" SET valor=? WHERE etiqueta=?', (valor, etiqueta))
    if c.rowcount == 0:
        conn.close()
        return jsonify({'error': 'No se encontró un registro con esa etiqueta'}), 404
    conn.commit()
    conn.close()

    generate_charts_for_user(user_id)

    return jsonify({'result': 'ok'})

@app.route('/get_record_value', methods=['GET'])
def get_record_value():
    if not user_is_logged_in():
        return jsonify({'error': 'No ha iniciado sesión'}), 403

    user_id = get_user_id()
    stat_name = request.args.get('stat_name', '').strip()
    etiqueta = request.args.get('etiqueta', '').strip()

    if not stat_name or not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Nombre de estadística inválido'}), 400
    if not etiqueta:
        return jsonify({'error': 'La etiqueta no puede estar vacía'}), 400

    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM dataset_config WHERE user_id=? AND stat_name=?", (user_id, stat_name))
    if c.fetchone()[0] == 0:
        conn.close()
        return jsonify({'error': 'No existe esta estadística para el usuario actual'}), 404

    table_name = full_table_name(user_id, stat_name)
    c.execute(f'SELECT valor FROM "{table_name}" WHERE etiqueta=?', (etiqueta,))
    row = c.fetchone()
    conn.close()
    if row is None:
        return jsonify({'error': 'No se encontró un registro con esa etiqueta'}), 404

    return jsonify({'value': row[0]})

@app.route('/delete_dataset', methods=['POST'])
def delete_dataset():
    if not user_is_logged_in():
        return jsonify({'error': 'No ha iniciado sesión'}), 403

    user_id = get_user_id()
    stat_name = request.form.get('stat_name', '').strip()

    if not stat_name or not is_valid_stat_name(stat_name):
        return jsonify({'error': 'Nombre de estadística inválido'}), 400

    conn = get_db_conn()
    c = conn.cursor()
    # Check if dataset exists
    c.execute("SELECT COUNT(*) FROM dataset_config WHERE user_id=? AND stat_name=?", (user_id, stat_name))
    if c.fetchone()[0] == 0:
        conn.close()
        return jsonify({'error': 'No existe esta estadística para el usuario actual'}), 404

    # Delete from dataset_config
    c.execute("DELETE FROM dataset_config WHERE user_id=? AND stat_name=?", (user_id, stat_name))
    # Drop the table
    table_name = full_table_name(user_id, stat_name)
    c.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    conn.commit()
    conn.close()

    # Remove chart image if exists
    img_path = os.path.join(STATIC_DIR, f"{user_id}_{stat_name}.png")
    if os.path.exists(img_path):
        os.remove(img_path)

    return jsonify({'result': 'ok'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='localhost', port=3000)

