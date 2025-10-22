from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
import traceback

# === Database Rata-Rata Sektor dari IDX (DER ditambahkan) ===
SECTOR_RATIOS = {
    'A. Energy': {'PER': 13.14, 'PBV': 3.63, 'DER': 0.57},
    'B. Basic Materials': {'PER': 14.04, 'PBV': 2.77, 'DER': 0.62},
    'C. Industrials': {'PER': 12.31, 'PBV': 1.11, 'DER': 0.48},
    'D. Consumer Non-Cyclicals': {'PER': 14.31, 'PBV': 1.96, 'DER': 0.73},
    'E. Consumer Cyclicals': {'PER': 17.32, 'PBV': 1.78, 'DER': 0.46},
    'F. Healthcare': {'PER': 15.51, 'PBV': 3.74, 'DER': 0.52},
    'G. Financials': {'PER': 14.67, 'PBV': 1.66, 'DER': 2.06}, # DER tinggi wajar untuk bank
    'H. Properties & Real Estate': {'PER': 17.89, 'PBV': 1.48, 'DER': 0.37},
    'I. Technology': {'PER': 21.06, 'PBV': 6.98, 'DER': 0.44},
    'J. Infrastructures': {'PER': 13.67, 'PBV': 4.26, 'DER': 0.75},
    'K. Transportation & Logistic': {'PER': 10.26, 'PBV': 7.90, 'DER': 0.66},
    'Market PER': 14.55,
    'Market PBV': 2.42
}

# === Pemetaan Sektor yfinance ke IDX ===
YFINANCE_TO_IDX_SECTOR = {
    'Energy': 'A. Energy',
    'Basic Materials': 'B. Basic Materials',
    'Industrials': 'C. Industrials',
    'Consumer Defensive': 'D. Consumer Non-Cyclicals',
    'Consumer Cyclical': 'E. Consumer Cyclicals',
    'Healthcare': 'F. Healthcare',
    'Financial Services': 'G. Financials',
    'Real Estate': 'H. Properties & Real Estate',
    'Technology': 'I. Technology',
    'Communication Services': 'J. Infrastructures',
    'Utilities': 'J. Infrastructures',
    'Transportation': 'K. Transportation & Logistic'
}
# ===============================================================

# Inisialisasi Flask App
app = Flask(__name__)

# ========= FUNGSI ANALISIS ANDA (DI-REFACTOR) =========
def get_fundamental_analysis(ticker_symbol):
    """
    Mengambil dan menganalisis data fundamental, kemudian mengembalikan
    hasilnya sebagai (list_of_strings, structured_dict).
    TIDAK MENGGUNAKAN PRINT().
    """
    analysis_log = [] # List untuk menampung semua output teks
    structured_data = { # Dict untuk menampung data mentah
        "emiten": {},
        "sektor": {},
        "market": {
            "PER": SECTOR_RATIOS['Market PER'],
            "PBV": SECTOR_RATIOS['Market PBV']
        }
    }
    
    analysis_log.append(f"Mengambil data fundamental untuk: {ticker_symbol}...")
    ticker = yf.Ticker(ticker_symbol)

    try:
        info = ticker.info
        if not info or 'regularMarketPrice' not in info or info.get('regularMarketPrice') is None:
            analysis_log.append(f"Gagal mengambil data fundamental lengkap untuk {ticker_symbol}.")
            return analysis_log, structured_data, False # Mengembalikan status Gagal

        # --- Ambil Data ---
        nama = info.get('shortName', ticker_symbol)
        harga = info.get('regularMarketPrice')
        yfinance_sektor = info.get('sector')
        industri = info.get('industry')
        per = info.get('trailingPE') 
        pbv = info.get('priceToBook')
        roe = info.get('returnOnEquity')
        der_percent = info.get('debtToEquity') 
        market_cap = info.get('marketCap')
        dps_tahunan = info.get('dividendRate')
        div_yield_yfinance = info.get('dividendYield')
        
        # Simpan data mentah ke dict
        structured_data["emiten"] = {
            "nama": nama, "harga": harga, "sektor": yfinance_sektor, "industri": industri,
            "PER": per, "PBV": pbv, "ROE": roe, "DER_percent": der_percent,
            "market_cap": market_cap, "DPS": dps_tahunan, "yield_yfinance": div_yield_yfinance
        }

        analysis_log.append("\n" + "="*50)
        analysis_log.append(f"HASIL ANALISIS FUNDAMENTAL - {nama} ({ticker_symbol})")
        analysis_log.append(f"Harga Saat Ini: Rp {harga:,.0f}")
        if yfinance_sektor: analysis_log.append(f"Sektor   : {yfinance_sektor}")
        if industri: analysis_log.append(f"Industri : {industri}")
        analysis_log.append(f"Kapitalisasi Pasar: Rp {market_cap:,.0f}")
        analysis_log.append("="*50)

        # --- Cari Rata-Rata Sektor ---
        avg_per, avg_pbv, avg_der = None, None, None
        if yfinance_sektor in YFINANCE_TO_IDX_SECTOR:
            idx_sektor_key = YFINANCE_TO_IDX_SECTOR[yfinance_sektor]
            if idx_sektor_key in SECTOR_RATIOS:
                sektor_data = SECTOR_RATIOS[idx_sektor_key]
                avg_per = sektor_data.get('PER')
                avg_pbv = sektor_data.get('PBV')
                avg_der = sektor_data.get('DER')
                
                # Simpan data sektor ke dict
                structured_data["sektor"] = {"nama": idx_sektor_key, "PER": avg_per, "PBV": avg_pbv, "DER": avg_der}
                
                analysis_log.append(f"Rata-rata Sektor ({idx_sektor_key}):")
                analysis_log.append(f"   -> Avg PER: {avg_per:.2f}x | Avg PBV: {avg_pbv:.2f}x | Avg DER: {avg_der:.2f}x")
                analysis_log.append(f"Rata-rata Pasar (IHSG):")
                analysis_log.append(f"   -> Avg PER: {SECTOR_RATIOS['Market PER']:.2f}x | Avg PBV: {SECTOR_RATIOS['Market PBV']:.2f}x")
        else:
            analysis_log.append(f"Tidak dapat menemukan pemetaan sektor untuk '{yfinance_sektor}'")
        analysis_log.append("-" * 50)
        
        # --- 1. Price-to-Earnings Ratio (PER) ---
        analysis_log.append(f"\n## 1. Price-to-Earnings Ratio (PER)")
        if per is not None:
            analysis_log.append(f"   -> PER Emiten: {per:.2f}x")
            if avg_per:
                if per < avg_per:
                    analysis_log.append(f"   -> Komparasi: DI BAWAH rata-rata sektor ({avg_per:.2f}x). 👍 (Potensi Murah)")
                else:
                    analysis_log.append(f"   -> Komparasi: DI ATAS rata-rata sektor ({avg_per:.2f}x). ⚠️ (Potensi Mahal)")
            if per < 0: analysis_log.append("   -> Interpretasi: Perusahaan merugi (PER negatif). 📉")
            elif per < 15: analysis_log.append("   -> Interpretasi: Potensi Undervalued (murah).")
            else: analysis_log.append("   -> Interpretasi: Potensi Overvalued (mahal).")
        else:
            analysis_log.append("   -> Data PER tidak tersedia (kemungkinan perusahaan merugi atau baru IPO).")

        # --- 2. Price-to-Book Value (PBV) ---
        analysis_log.append(f"\n## 2. Price-to-Book Value (PBV)")
        if pbv is not None:
            analysis_log.append(f"   -> PBV Emiten: {pbv:.2f}x")
            if avg_pbv:
                if pbv < avg_pbv:
                    analysis_log.append(f"   -> Komparasi: DI BAWAH rata-rata sektor ({avg_pbv:.2f}x). 👍 (Potensi Murah)")
                else:
                    analysis_log.append(f"   -> Komparasi: DI ATAS rata-rata sektor ({avg_pbv:.2f}x). ⚠️ (Potensi Mahal)")
            if pbv < 0: analysis_log.append("   -> Interpretasi: Nilai buku negatif (liabilitas > aset). 🚨")
            elif pbv < 1: analysis_log.append("   -> Interpretasi: Potensi Undervalued (harga di bawah nilai buku).")
            else: analysis_log.append("   -> Interpretasi: Potensi Overvalued (diperdagangkan premium).")
        else:
            analysis_log.append("   -> Data PBV tidak tersedia.")
            
        # --- 3. Debt-to-Equity Ratio (DER) ---
        analysis_log.append(f"\n## 3. Debt-to-Equity Ratio (DER)")
        if der_percent is not None:
            der_ratio = der_percent / 100
            structured_data["emiten"]["DER_ratio"] = der_ratio # Simpan rasio
            analysis_log.append(f"   -> DER Emiten: {der_ratio:.2f}x (atau {der_percent:.2f}%)")
            if avg_der is not None:
                if der_ratio < avg_der:
                    analysis_log.append(f"   -> Komparasi: LEBIH RENDAH dari rata-rata sektor ({avg_der:.2f}x). 👍 (Risiko Rendah)")
                else:
                    analysis_log.append(f"   -> Komparasi: LEBIH TINGGI dari rata-rata sektor ({avg_der:.2f}x). ⚠️ (Risiko Tinggi)")
            if der_ratio < 0.5: analysis_log.append("   -> Interpretasi: Perusahaan konservatif (modal besar, utang kecil).")
            elif der_ratio <= 1.0: analysis_log.append("   -> Interpretasi: Utang seimbang dengan modal (umumnya sehat). 😐")
            else: analysis_log.append("   -> Interpretasi: Agresif (utang lebih besar dari modal). ⚠️")
            analysis_log.append("   -> Konteks: Sektor 'Financials' wajar memiliki DER tinggi.")
        else:
            analysis_log.append("   -> Data DER tidak tersedia.")

        # --- 4. Return on Equity (ROE) ---
        analysis_log.append(f"\n## 4. Return on Equity (ROE)")
        if roe is not None:
            analysis_log.append(f"   -> ROE: {roe * 100:.2f}%") 
            if roe < 0: analysis_log.append("   -> Interpretasi: Perusahaan tidak profitabel (merugi). 📉")
            elif roe < 0.10: analysis_log.append("   -> Interpretasi: Profitabilitas rendah. 😐")
            elif roe <= 0.20: analysis_log.append("   -> Interpretasi: Profitabilitas baik dan sehat. 👍")
            else: analysis_log.append("   -> Interpretasi: Profitabilitas sangat tinggi (luar biasa). 🔥")
            analysis_log.append("   -> Konteks: Semakin tinggi semakin baik. Bandingkan dengan kompetitor.")
        else:
            analysis_log.append("   -> Data ROE tidak tersedia.")

        # --- 5. Dividend Yield ---
        analysis_log.append(f"\n## 5. Dividend Yield")
        div_yield_calc = None
        if dps_tahunan is not None and dps_tahunan > 0 and harga is not None and harga > 0:
            div_yield_calc = (dps_tahunan / harga)
            analysis_log.append(f"   -> Dividen per Lembar (Tahunan): Rp {dps_tahunan:,.2f}")
            analysis_log.append(f"   -> Harga per Lembar Saham    : Rp {harga:,.0f}")
            analysis_log.append(f"   -> Rumus Yield   : (Rp {dps_tahunan:,.2f} / Rp {harga:,.0f}) * 100%")
            analysis_log.append(f"   -> Hasil Dividend Yield: {div_yield_calc * 100:.2f}%")
        elif div_yield_yfinance is not None and div_yield_yfinance > 0:
             div_yield_calc = div_yield_yfinance
             analysis_log.append(f"   -> Dividend Yield (Data yfinance): {div_yield_yfinance * 100:.2f}%")
             analysis_log.append(f"   -> (Data DPS per lembar tidak tersedia untuk perhitungan manual)")
        else:
             analysis_log.append("   -> Perusahaan tidak membagikan dividen / data tidak tersedia.")
        
        structured_data["emiten"]["yield_calc"] = div_yield_calc
        
        return analysis_log, structured_data, True # Mengembalikan status Sukses

    except Exception as e:
        error_msg = f"\nTerjadi error saat memproses {ticker_symbol}: {e}"
        analysis_log.append(error_msg)
        traceback.print_exc() # Ini akan print ke log Vercel
        return analysis_log, structured_data, False # Mengembalikan status Gagal

# ========= ENDPOINT API UTAMA KITA =========
@app.route('/api/fundamental', methods=['POST'])
def handle_fundamental_analysis():
    try:
        # 1. Ambil ticker dari JSON body yang dikirim n8n
        req_data = request.get_json()
        if not req_data or 'ticker' not in req_data:
            return jsonify({"status": "error", "message": "Mohon kirim {'ticker': 'KODE_SAHAM'} dalam body JSON."}), 400

        # Tambahkan .JK untuk pasar Indonesia
        ticker_input = req_data['ticker'].upper()
        ticker_symbol = ticker_input + ".JK"
        
        # 2. Jalankan fungsi analisis Anda
        log_outputs, structured_outputs, success = get_fundamental_analysis(ticker_symbol)
        
        # 3. Gabungkan log list menjadi satu string panjang
        final_analysis_text = "\n".join(log_outputs)

        if not success:
            # Jika gagal (misal 404), kirim pesan error
            return jsonify({
                "status": "error", 
                "ticker": ticker_input,
                "analysis_text": final_analysis_text
            }), 404

        # 4. Kirim kembali respons JSON yang lengkap
        return jsonify({
            "status": "success",
            "ticker": ticker_input,
            "analysis_text": final_analysis_text,
            "structured_data": structured_outputs
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Error internal server: {e}"}), 500

# Endpoint untuk mengetes apakah server jalan
@app.route('/', methods=['GET'])
def home():
    return "Server Analisis Fundamental Aktif. Gunakan endpoint /api/fundamental dengan method POST."
