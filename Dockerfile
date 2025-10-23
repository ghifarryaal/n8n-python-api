# LANGKAH 1: Gunakan base image Python 3.12 (versi penuh, bukan slim)
# Versi penuh membawa lebih banyak library sistem yang dibutuhkan
FROM python:3.12

# LANGKAH 2: Instalasi dependensi sistem
# - build-essential: Diperlukan untuk meng-compile library C
# - wget & tar: Diperlukan untuk mengunduh dan mengekstrak TA-Lib
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# LANGKAH 3: Instalasi TA-Lib (Library C)
# Ini adalah fondasi yang dibutuhkan oleh pandas-ta dan TA-Lib (Python)
WORKDIR /tmp
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/ta-lib*

# LANGKAH 4: Siapkan direktori aplikasi
WORKDIR /app

# LANGKAH 5: Upgrade pip (Penting)
RUN pip install --no-cache-dir --upgrade pip

# LANGKAH 6: Salin file requirements dan instal
# Ini disalin terlebih dahulu untuk caching Docker
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# LANGKAH 7: Salin sisa kode proyek
COPY . .

# LANGKAH 8: Ekspos port (sesuai Gunicorn)
EXPOSE 10000

# LANGKAH 9: Jalankan server produksi Gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:10000", "api.index:app"]

