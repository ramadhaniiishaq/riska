from flask import Flask, flash, render_template, request, redirect, session, url_for
from flask_mysqldb import MySQL
from functools import wraps
import bcrypt
from datetime import date
from MySQLdb.cursors import DictCursor
from secrets import token_hex

app = Flask(__name__)
app.secret_key = token_hex(16)

# ================= KONFIGURASI DATABASE =================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'db_ekskul'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# ================= MIDDLEWARE =================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'admin':
            flash('Akses ditolak!', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ================= HOME =================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/seeder')
def seeder():
    username = 'admin'
    password = '123'
    
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT IGNORE INTO admin (username,password) VALUES (%s,%s)",
        (username, hashed.decode('utf-8'))
    )
    mysql.connection.commit()
    cursor.close()
    
    return "Seeder berhasil dijalankan"
# ================= LOGIN ADMIN =================
@app.route('/login/admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin WHERE username = %s", (username,))
        admin = cursor.fetchone()
        cursor.close()

        if admin and bcrypt.checkpw(password.encode(), admin['password'].encode()):
            session['user_id'] = admin['id_admin']
            session['role'] = 'admin'
            session['username'] = admin['username']
            flash('Login berhasil!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Username atau password salah', 'error')

    return render_template('login_admin.html')

# ================= LOGIN SISWA =================
@app.route('/login/siswa', methods=['GET', 'POST'])
def login_siswa():
    if request.method == 'POST':
        nis = request.form.get('nis')
        nama = request.form.get('nama_siswa')

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM siswa WHERE nis = %s AND nama_siswa = %s", (nis, nama))
        siswa = cursor.fetchone()
        cursor.close()

        if siswa:
            session['user_id'] = siswa['id_siswa']
            session['role'] = 'siswa'
            session['nama_siswa'] = siswa['nama_siswa']
            session['nis'] = siswa['nis']
            flash('Login berhasil!', 'success')
            return redirect(url_for('siswa_dashboard'))
        else:
            flash('NIS atau Nama Siswa salah', 'error')

    return render_template('login_siswa.html')

# ================= DASHBOARD ADMIN =================
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    cursor = mysql.connection.cursor()
    
    # Statistik
    cursor.execute("SELECT COUNT(*) as total FROM ekskul")
    total_ekskul = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM siswa")
    total_siswa = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM pendaftaran")
    total_pendaftaran = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM pendaftaran WHERE status = 'pending'")
    pending = cursor.fetchone()['total']
    
    # Data chart
    cursor.execute("""
        SELECT e.nama_ekskul, COUNT(p.id_pendaftaran) as jumlah
        FROM ekskul e
        LEFT JOIN pendaftaran p ON e.id_ekskul = p.id_ekskul
        GROUP BY e.id_ekskul
        ORDER BY jumlah DESC
        LIMIT 5
    """)
    chart_data = cursor.fetchall()
    
    # Pendaftaran terbaru
    cursor.execute("""
        SELECT p.*, s.nama_siswa, e.nama_ekskul, p.tanggal_daftar, p.status
        FROM pendaftaran p
        JOIN siswa s ON p.id_siswa = s.id_siswa
        JOIN ekskul e ON p.id_ekskul = e.id_ekskul
        ORDER BY p.tanggal_daftar DESC
        LIMIT 5
    """)
    pendaftaran_terbaru = cursor.fetchall()
    
    cursor.close()
    
    return render_template('admin/dashboard.html', 
                         total_ekskul=total_ekskul,
                         total_siswa=total_siswa,
                         total_pendaftaran=total_pendaftaran,
                         pending=pending,
                         chart_data=chart_data,
                         pendaftaran_terbaru=pendaftaran_terbaru,
                         username=session.get('username'))
# ================= TAMBAH EKSKUL =================
@app.route('/admin/ekskul/tambah', methods=['POST'])
@admin_required
def tambah_ekskul():
    nama = request.form.get('nama_ekskul')
    pembina = request.form.get('pembina')
    jadwal = request.form.get('jadwal')
    deskripsi = request.form.get('deskripsi')
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO ekskul (nama_ekskul, pembina, jadwal, deskripsi) VALUES (%s, %s, %s, %s)",
        (nama, pembina, jadwal, deskripsi)
    )
    mysql.connection.commit()
    cursor.close()
    
    flash('Ekskul berhasil ditambahkan!', 'success')
    return redirect(url_for('admin_dashboard'))

# ================= EDIT EKSKUL =================
@app.route('/admin/ekskul/edit/<int:id_ekskul>', methods=['POST'])
@admin_required
def edit_ekskul(id_ekskul):
    nama = request.form.get('nama_ekskul')
    pembina = request.form.get('pembina')
    jadwal = request.form.get('jadwal')
    deskripsi = request.form.get('deskripsi')
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "UPDATE ekskul SET nama_ekskul=%s, pembina=%s, jadwal=%s, deskripsi=%s WHERE id_ekskul=%s",
        (nama, pembina, jadwal, deskripsi, id_ekskul)
    )
    mysql.connection.commit()
    cursor.close()
    
    flash('Ekskul berhasil diupdate!', 'success')
    return redirect(url_for('admin_dashboard'))

# ================= HAPUS EKSKUL =================
@app.route('/admin/ekskul/hapus/<int:id_ekskul>', methods=['POST'])
@admin_required
def hapus_ekskul(id_ekskul):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM pendaftaran WHERE id_ekskul = %s", (id_ekskul,))
    cursor.execute("DELETE FROM ekskul WHERE id_ekskul = %s", (id_ekskul,))
    mysql.connection.commit()
    cursor.close()
    
    flash('Ekskul berhasil dihapus!', 'success')
    return redirect(url_for('admin_dashboard'))

# ================= TAMBAH SISWA =================
@app.route('/admin/siswa/tambah', methods=['POST'])
@admin_required
def tambah_siswa():
    nis = request.form.get('nis')
    nama = request.form.get('nama_siswa')
    kelas = request.form.get('kelas')
    email = request.form.get('email')
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "INSERT INTO siswa (nis, nama_siswa, kelas, email) VALUES (%s, %s, %s, %s)",
        (nis, nama, kelas, email)
    )
    mysql.connection.commit()
    cursor.close()
    
    flash('Siswa berhasil ditambahkan!', 'success')
    return redirect(url_for('admin_dashboard'))

# ================= HAPUS SISWA =================
@app.route('/admin/siswa/hapus/<int:id_siswa>', methods=['POST'])
@admin_required
def hapus_siswa(id_siswa):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM pendaftaran WHERE id_siswa = %s", (id_siswa,))
    cursor.execute("DELETE FROM siswa WHERE id_siswa = %s", (id_siswa,))
    mysql.connection.commit()
    cursor.close()
    
    flash('Siswa berhasil dihapus!', 'success')
    return redirect(url_for('admin_dashboard'))

# ================= DASHBOARD SISWA =================
@app.route('/siswa/dashboard')
@login_required
def siswa_dashboard():
    if session.get('role') != 'siswa':
        return redirect(url_for('index'))
    
    cursor = mysql.connection.cursor()
    

    cursor.execute("SELECT COUNT(*) AS total FROM ekskul")
    jumlah_ekskul = cursor.fetchone()['total']
    
    # Ambil pendaftaran siswa ini
    cursor.execute("""
        SELECT p.*, e.nama_ekskul, e.pembina, e.jadwal
        FROM pendaftaran p
        JOIN ekskul e ON p.id_ekskul = e.id_ekskul
        WHERE p.id_siswa = %s
    """, (session['user_id'],))
    pendaftaran = cursor.fetchall()
    cursor.close()
    
    return render_template('siswa/dashboard.html', 
                         ekskul=jumlah_ekskul, 
                         pendaftaran=pendaftaran,
                         nama_siswa=session.get('nama_siswa'))

# ================= DAFTAR EKSKUL =================
@app.route('/siswa/daftar/<int:id_ekskul>', methods=['POST'])
@login_required
def daftar_ekskul(id_ekskul):
    if session.get('role') != 'siswa':
        flash('Anda harus login sebagai siswa', 'error')
        return redirect(url_for('login_siswa'))
    
    cursor = mysql.connection.cursor()
    
    # Cek apakah sudah terdaftar
    cursor.execute(
        "SELECT * FROM pendaftaran WHERE id_siswa = %s AND id_ekskul = %s",
        (session['user_id'], id_ekskul)
    )
    existing = cursor.fetchone()
    
    if existing:
        flash('Anda sudah mendaftar ekskul ini!', 'warning')
    else:
        cursor.execute(
            "INSERT INTO pendaftaran (id_siswa, id_ekskul, tanggal_daftar, status) VALUES (%s, %s, %s, 'pending')",
            (session['user_id'], id_ekskul, date.today())
        )
        mysql.connection.commit()
        flash('Berhasil mendaftar!', 'success')
    
    cursor.close()
    return redirect(url_for('siswa_dashboard'))

# ================= BATAL DAFTAR =================
@app.route('/siswa/batal/<int:id_pendaftaran>', methods=['POST'])
@login_required
def batal_daftar(id_pendaftaran):
    if session.get('role') != 'siswa':
        return redirect(url_for('index'))
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "DELETE FROM pendaftaran WHERE id_pendaftaran = %s AND id_siswa = %s",
        (id_pendaftaran, session['user_id'])
    )
    mysql.connection.commit()
    cursor.close()
    
    flash('Pendaftaran dibatalkan', 'success')
    return redirect(url_for('siswa_dashboard'))

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout', 'success')
    return redirect(url_for('index'))

# ================= RUTE UNTUK ADMIN (TAMBAHAN) =================

@app.route('/admin/ekskul')
@admin_required
def admin_ekskul():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT e.*, 
               COUNT(p.id_pendaftaran) as total_pendaftar
        FROM ekskul e
        LEFT JOIN pendaftaran p ON e.id_ekskul = p.id_ekskul
        GROUP BY e.id_ekskul
    """)
    ekskul = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/ekskul.html', ekskul=ekskul, username=session.get('username'))


@app.route('/admin/siswa')
@admin_required
def admin_siswa():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT s.*, 
               COUNT(p.id_pendaftaran) as total_daftar
        FROM siswa s
        LEFT JOIN pendaftaran p ON s.id_siswa = p.id_siswa
        GROUP BY s.id_siswa
    """)
    siswa = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/siswa.html', siswa=siswa, username=session.get('username'))


@app.route('/admin/pendaftaran')
@admin_required
def admin_pendaftaran():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT p.*, s.nama_siswa, s.nis, s.kelas, e.nama_ekskul, e.pembina
        FROM pendaftaran p
        JOIN siswa s ON p.id_siswa = s.id_siswa
        JOIN ekskul e ON p.id_ekskul = e.id_ekskul
        ORDER BY p.tanggal_daftar DESC
    """)
    pendaftaran = cursor.fetchall()
    cursor.close()
    
    return render_template('admin/pendaftaran.html', pendaftaran=pendaftaran, username=session.get('username'))


@app.route('/admin/pendaftaran/update/<int:id_pendaftaran>', methods=['POST'])
@admin_required
def update_status_pendaftaran(id_pendaftaran):
    status = request.form.get('status')
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "UPDATE pendaftaran SET status = %s WHERE id_pendaftaran = %s",
        (status, id_pendaftaran)
    )
    mysql.connection.commit()
    cursor.close()
    
    flash(f'Status pendaftaran berhasil diubah menjadi {status}', 'success')
    return redirect(url_for('admin_pendaftaran'))


@app.route('/admin/pendaftaran/hapus/<int:id_pendaftaran>', methods=['POST'])
@admin_required
def hapus_pendaftaran(id_pendaftaran):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM pendaftaran WHERE id_pendaftaran = %s", (id_pendaftaran,))
    mysql.connection.commit()
    cursor.close()
    
    flash('Pendaftaran berhasil dihapus', 'success')
    return redirect(url_for('admin_pendaftaran'))


@app.route('/admin/siswa/edit/<int:id_siswa>', methods=['POST'])
@admin_required
def edit_siswa(id_siswa):
    nis = request.form.get('nis')
    nama = request.form.get('nama_siswa')
    kelas = request.form.get('kelas')
    email = request.form.get('email')
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "UPDATE siswa SET nis=%s, nama_siswa=%s, kelas=%s, email=%s WHERE id_siswa=%s",
        (nis, nama, kelas, email, id_siswa)
    )
    mysql.connection.commit()
    cursor.close()
    
    flash('Data siswa berhasil diupdate!', 'success')
    return redirect(url_for('admin_siswa'))


# ================= RUTE UNTUK SISWA (TAMBAHAN) =================

@app.route('/siswa/semua-ekskul')
@login_required
def semua_ekskul():
    if session.get('role') != 'siswa':
        return redirect(url_for('index'))
    
    cursor = mysql.connection.cursor()
    
    # Ambil semua ekskul
    cursor.execute("SELECT * FROM ekskul")
    ekskul = cursor.fetchall()
    
    # Ambil ekskul yang sudah didaftar siswa ini
    cursor.execute(
        "SELECT id_ekskul FROM pendaftaran WHERE id_siswa = %s",
        (session['user_id'],)
    )
    terdaftar = cursor.fetchall()
    ekskul_terdaftar = [t['id_ekskul'] for t in terdaftar]
    
    cursor.close()
    
    return render_template('siswa/semua_ekskul.html', 
                         ekskul=ekskul, 
                         ekskul_terdaftar=ekskul_terdaftar,
                         nama_siswa=session.get('nama_siswa'))


@app.route('/siswa/ekskul-saya')
@login_required
def siswa_ekskul_saya():
    if session.get('role') != 'siswa':
        return redirect(url_for('index'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT p.*, e.nama_ekskul, e.pembina, e.jadwal, e.deskripsi
        FROM pendaftaran p
        JOIN ekskul e ON p.id_ekskul = e.id_ekskul
        WHERE p.id_siswa = %s
        ORDER BY p.tanggal_daftar DESC
    """, (session['user_id'],))
    pendaftaran = cursor.fetchall()
    cursor.close()
    
    return render_template('siswa/ekskul_saya.html', 
                         pendaftaran=pendaftaran,
                         nama_siswa=session.get('nama_siswa'))


@app.route('/siswa/profil')
@login_required
def siswa_profil():
    if session.get('role') != 'siswa':
        return redirect(url_for('index'))
    
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM siswa WHERE id_siswa = %s", (session['user_id'],))
    siswa = cursor.fetchone()
    
    cursor.execute("""
        SELECT p.*, e.nama_ekskul 
        FROM pendaftaran p
        JOIN ekskul e ON p.id_ekskul = e.id_ekskul
        WHERE p.id_siswa = %s 
        ORDER BY p.tanggal_daftar DESC 
        LIMIT 5
    """, (session['user_id'],))
    pendaftaran_terbaru = cursor.fetchall()
    cursor.close()
    
    return render_template('siswa/profil.html', 
                         siswa=siswa, 
                         pendaftaran_terbaru=pendaftaran_terbaru,
                         nama_siswa=session.get('nama_siswa'))


@app.route('/siswa/profil/update', methods=['POST'])
@login_required
def siswa_update_profil():
    if session.get('role') != 'siswa':
        return redirect(url_for('index'))
    
    nama = request.form.get('nama_siswa')
    kelas = request.form.get('kelas')
    email = request.form.get('email')
    
    cursor = mysql.connection.cursor()
    cursor.execute(
        "UPDATE siswa SET nama_siswa=%s, kelas=%s, email=%s WHERE id_siswa=%s",
        (nama, kelas, email, session['user_id'])
    )
    mysql.connection.commit()
    cursor.close()
    
    # Update session
    session['nama_siswa'] = nama
    
    flash('Profil berhasil diupdate!', 'success')
    return redirect(url_for('siswa_profil'))

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)