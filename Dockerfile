# Gunakan base image Python yang ringan dan efisien
FROM python:3.9-slim

# Tetapkan direktori kerja di dalam kontainer
WORKDIR /app

# Salin file requirements.txt terlebih dahulu untuk memanfaatkan caching Docker
COPY requirements.txt requirements.txt

# Install semua library yang dibutuhkan
# --no-cache-dir digunakan untuk mengurangi ukuran image
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua sisa kode proyek ke dalam direktori kerja di kontainer
COPY . .

# Beritahu Docker bahwa kontainer akan berjalan di port 10000
EXPOSE 10000

# Perintah untuk menjalankan aplikasi Flask menggunakan Gunicorn (server WSGI produksi)
# --workers 4: Menjalankan 4 proses worker untuk menangani permintaan secara paralel
# --bind 0.0.0.0:10000: Menjalankan server di semua interface jaringan pada port 10000
# api.index:app: Menunjuk ke variabel 'app' di dalam file 'api/index.py'
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:10000", "api.index:app"]
