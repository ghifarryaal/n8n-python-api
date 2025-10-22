# 1. UPGRADE ke Python 3.12. Ini adalah permintaan langsung dari log error.
FROM python:3.12

# Tetapkan direktori kerja di dalam kontainer
WORKDIR /app

# 2. Update package manager dan install build tools (tetap penting)
RUN apt-get update && apt-get install -y build-essential

# 3. Upgrade pip ke versi terbaru
RUN pip install --upgrade pip

# Salin file requirements.txt terlebih dahulu
COPY requirements.txt requirements.txt

# 4. Install library dengan timeout yang lebih panjang untuk stabilitas
RUN pip install --no-cache-dir --timeout 100 -r requirements.txt

# Salin semua sisa kode proyek
COPY . .

# Beritahu Docker port yang akan digunakan
EXPOSE 10000

# Perintah untuk menjalankan aplikasi
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:10000", "api.index:app"]

