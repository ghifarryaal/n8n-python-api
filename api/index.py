from flask import Flask, request, jsonify
import sys
import os

# --- Trik untuk Vercel agar bisa import dari folder root ---
# Menambahkan folder root (tempat analisis_fundamental.py berada) ke path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# -----------------------------------------------------------

# Impor fungsi-fungsi dari file logika Anda
from analisis_fundamental import get_fundamental_analysis
from analisis_teknikal import get_technical_analysis

# Inisialisasi Flask App
app = Flask(__name__)

# === ENDPOINT 1: FUNDAMENTAL ===
@app.route('/api/fundamental', methods=['POST'])
def handle_fundamental():
    try:
        req_data = request.get_json()
        if not req_data or 'ticker' not in req_data:
            return jsonify({"status": "error", "message": "Mohon kirim {'ticker': 'KODE_SAHAM'}"}), 400
        
        ticker_input = req_data['ticker'].upper()
        ticker_symbol_jk = ticker_input + ".JK"
        
        # Panggil fungsi dari file fundamental
        log, data, success = get_fundamental_analysis(ticker_symbol_jk)
        
        if not success:
            return jsonify({"status": "error", "ticker": ticker_input, "analysis_text": "\n".join(log)}), 404
            
        return jsonify({
            "status": "success",
            "ticker": ticker_input,
            "analysis_text": "\n".join(log),
            "structured_data": data
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Internal server error: {e}"}), 500

# === ENDPOINT 2: TEKNIKAL ===
@app.route('/api/teknikal', methods=['POST'])
def handle_teknikal():
    try:
        req_data = request.get_json()
        if not req_data or 'ticker' not in req_data:
            return jsonify({"status": "error", "message": "Mohon kirim {'ticker': 'KODE_SAHAM'}"}), 400

        ticker_input = req_data['ticker'].upper()
        ticker_symbol_jk = ticker_input + ".JK"

        # Panggil fungsi dari file teknikal
        log, data, success = get_technical_analysis(ticker_symbol_jk)

        if not success:
            return jsonify({"status": "error", "ticker": ticker_input, "analysis_text": "\n".join(log)}), 404

        return jsonify({
            "status": "success",
            "ticker": ticker_input,
            "analysis_text": "\n".join(log),
            "last_indicators": data
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Internal server error: {e}"}), 500

# === ENDPOINT 3: SENTIMEN ===
from analisis_sentimen import get_sentiment_analysis

@app.route('/api/sentimen', methods=['POST'])
def handle_sentimen():
    try:
        req_data = request.get_json()
        if not req_data or 'ticker' not in req_data:
            return jsonify({"status": "error", "message": "Mohon kirim {'ticker': 'KODE_SAHAM'}"}), 400

        ticker_input = req_data['ticker'].upper()
        ticker_symbol_jk = ticker_input + ".JK"

        log, data, success = get_sentiment_analysis(ticker_symbol_jk)
        if not success:
            return jsonify({"status": "error", "ticker": ticker_input, "analysis_text": "\n".join(log)}), 404

        return jsonify({
            "status": "success",
            "ticker": ticker_input,
            "analysis_text": "\n".join(log),
            "structured_data": data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Internal server error: {e}"}), 500


# Endpoint untuk mengetes apakah server jalan
@app.route('/', methods=['GET'])
def home():
    return "Server Analisis Gabungan Aktif. Gunakan /api/fundamental atau /api/teknikal."

