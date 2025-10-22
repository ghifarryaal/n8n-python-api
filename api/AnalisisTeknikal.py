from flask import Flask, request, jsonify
import yfinance as yf
import pandas_ta as pta
import pandas as pd
import numpy as np
import traceback
import io

# Inisialisasi Flask App
app = Flask(__name__)

# ========= SALIN SEMUA FUNGSI HELPER ANDA DI SINI =========
# (Fungsi bulatkan_fraksi, hitung_fibonacci, hitung_pivot_points_auto)

def bulatkan_fraksi(harga):
    if harga > 5000: tick = 25
    elif harga > 2000: tick = 10
    elif harga > 500: tick = 5
    elif harga >= 200: tick = 2
    else: tick = 1
    return round(harga / tick) * tick

def hitung_fibonacci(data, periode=60):
    if len(data) < periode: recent_data = data
    else: recent_data = data.tail(periode)
    if recent_data.empty: return {}, 0, 0
    swing_high = recent_data['High'].max()
    swing_low = recent_data['Low'].min()
    if swing_high == swing_low: return {}, swing_high, swing_low
    diff = swing_high - swing_low
    levels_raw = {
        '2.618 (Ext)': swing_high + (diff * 1.618),
        '1.618 (Ext)': swing_high + (diff * 0.618),
        '1.272 (Ext)': swing_high + (diff * 0.272),
        '1.0 (High)': swing_high,
        '0.786': swing_low + (diff * 0.786),
        '0.618 (Golden)': swing_low + (diff * 0.618),
        '0.500': swing_low + (diff * 0.500),
        '0.382': swing_low + (diff * 0.382),
        '0.236': swing_low + (diff * 0.236),
        '0.0 (Low)': swing_low
    }
    rounded_levels = {}
    for key, value in levels_raw.items():
        if value is not None:
            rounded_levels[key] = bulatkan_fraksi(value)
    return rounded_levels, swing_high, swing_low

def hitung_pivot_points_auto(data, periode=15):
    pivot_list, r1_list, r2_list, s1_list, s2_list = [], [], [], [], []
    for i in range(len(data)):
        if i < periode: window = data.iloc[:i+1]
        else: window = data.iloc[i-periode+1:i+1]
        high, low, close = window['High'].max(), window['Low'].min(), window['Close'].iloc[-1]
        pivot_raw = (high + low + close) / 3
        r1_raw = (2 * pivot_raw) - low
        s1_raw = (2 * pivot_raw) - high
        r2_raw = pivot_raw + (high - low)
        s2_raw = pivot_raw - (high - low)
        pivot_list.append(bulatkan_fraksi(pivot_raw))
        r1_list.append(bulatkan_fraksi(r1_raw))
        r2_list.append(bulatkan_fraksi(r2_raw))
        s1_list.append(bulatkan_fraksi(s1_raw))
        s2_list.append(bulatkan_fraksi(s2_raw))
    return pivot_list, r1_list, r2_list, s1_list, s2_list

# ========= FUNGSI INTERPRETASI DIUBAH (TIDAK PRINT, TAPI RETURN) =========
def interpretasi_fibonacci(current_price, fib_levels):
    """
    Menginterpretasikan posisi harga relatif terhadap level Fibonacci (High=1.0, Low=0.0)
    dan mengembalikan hasilnya sebagai list of strings.
    """
    output_lines = []
    output_lines.append(f"\n[Fibonacci Retracement & Extension (Fraksi BEI)]")
    output_lines.append(f"Harga Saat Ini: {current_price:.0f}")
    output_lines.append("-" * 50)

    if not fib_levels:
        output_lines.append("   -> Level Fibonacci tidak dapat dihitung.")
        return output_lines

    sorted_levels = sorted(fib_levels.items(), key=lambda item: item[1], reverse=True)
    for level_name, level_value in sorted_levels:
        output_lines.append(f"Fib {level_name:<15}: {level_value:.0f}")
    output_lines.append("-" * 50)

    if current_price >= fib_levels.get('2.618 (Ext)', float('inf')):
        output_lines.append("   -> Harga DI ATAS target ekstensi 2.618 (Sangat Bullish)")
    elif current_price >= fib_levels.get('1.618 (Ext)', float('inf')):
        output_lines.append("   -> Harga di zona target 1.618 - 2.618")
    elif current_price >= fib_levels.get('1.272 (Ext)', float('inf')):
        output_lines.append("   -> Harga di zona target 1.272 - 1.618")
    elif current_price >= fib_levels.get('1.0 (High)', float('inf')):
        output_lines.append("   -> Harga DI ATAS swing high (Breakout Bullish)")
    elif current_price >= fib_levels.get('0.786', float('inf')):
        output_lines.append("   -> Harga di zona 0.786 - 1.0 (Retracement Ringan)")
    elif current_price >= fib_levels.get('0.618 (Golden)', float('inf')):
        output_lines.append("   -> Harga di zona 0.618 - 0.786 (Golden Ratio)")
        output_lines.append("   -> SUPPORT KRITIS di Fib 0.618")
    elif current_price >= fib_levels.get('0.500', float('inf')):
        output_lines.append("   -> Harga di zona 0.500 - 0.618 (Retracement Sedang)")
    elif current_price >= fib_levels.get('0.382', float('inf')):
        output_lines.append("   -> Harga di zona 0.382 - 0.500 (Retracement Dalam)")
    elif current_price >= fib_levels.get('0.236', float('inf')):
        output_lines.append("   -> Harga di zona 0.236 - 0.382 (Retracement Sangat Dalam)")
    elif current_price >= fib_levels.get('0.0 (Low)', float('inf')):
        output_lines.append("   -> Harga mendekati swing low")
    else:
        output_lines.append("   -> Harga DI BAWAH swing low (Breakdown Bearish)")
    
    return output_lines


# ========= FUNGSI PLOT_CHART DIHAPUS KARENA TIDAK BISA JALAN DI VERCEL =========
# def plot_chart(...):
#     ... (KODE DIHAPUS) ...


# ========= INI ADALAH ENDPOINT API UTAMA KITA =========
@app.route('/api/analisis', methods=['POST'])
def handle_analysis():
    # List untuk menampung semua output teks
    analysis_log = []

    try:
        # 1. Ambil ticker dari JSON body yang dikirim n8n
        req_data = request.get_json()
        if not req_data or 'ticker' not in req_data:
            return jsonify({"status": "error", "message": "Mohon kirim {'ticker': 'KODE_SAHAM'} dalam body JSON."}), 400

        # Tambahkan .JK untuk pasar Indonesia
        ticker_symbol = req_data['ticker'].upper() + ".JK"
        analysis_log.append(f"Memulai analisis untuk: {ticker_symbol}")

        # 2. Inisialisasi Ticker dan Ambil Data
        ticker_obj = yf.Ticker(ticker_symbol)
        data = ticker_obj.history(period="2y", interval="1d")

        if data.empty:
            return jsonify({"status": "error", "message": f"Tidak ada data yang ditemukan untuk {ticker_symbol}."}), 404
        
        analysis_log.append(f"✅ Data berhasil diambil: {len(data)} baris data")

        # 3. Hitung Indikator Analisis Teknikal
        analysis_log.append("⏳ Menghitung indikator teknikal...")
        
        macd = data.ta.macd(append=False); data = pd.concat([data, macd], axis=1) if macd is not None else data
        rsi = data.ta.rsi(length=14, append=False); data['RSI_14'] = rsi if rsi is not None else np.nan
        stochrsi = data.ta.stochrsi(append=False); data = pd.concat([data, stochrsi], axis=1) if stochrsi is not None else data
        mfi = data.ta.mfi(length=14, append=False); data['MFI_14'] = mfi if mfi is not None else np.nan

        analysis_log.append("⏳ Menghitung Pivot Points (periode 15 hari) dengan Fraksi BEI...")
        pivot_list, r1_list, r2_list, s1_list, s2_list = hitung_pivot_points_auto(data, periode=15)
        data['P_auto15'] = pivot_list
        data['R1_auto15'] = r1_list
        data['S1_auto15'] = s1_list
        data['R2_auto15'] = r2_list
        data['S2_auto15'] = s2_list

        analysis_log.append("⏳ Menghitung Fibonacci (periode 60 hari) dengan Fraksi BEI...")
        fib_levels, swing_high, swing_low = hitung_fibonacci(data, periode=60)

        # 4. Tampilkan Hasil (Hanya data terakhir)
        kolom_tampil = ['Close', 'Volume', 'MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9',
                        'RSI_14', 'MFI_14', 'STOCHRSIk_14_14_3_3', 'STOCHRSId_14_14_3_3',
                        'P_auto15', 'S1_auto15', 'R1_auto15', 'S2_auto15', 'R2_auto15']
        
        kolom_ada = [col for col in kolom_tampil if col in data.columns]
        data_bersih = data[kolom_ada].dropna()
        
        last_data_dict = {}
        if data_bersih.empty:
            analysis_log.append(f"   -> GAGAL: Tidak ada data yang valid setelah dihitung.")
        else:
            last_data = data_bersih.iloc[-1]
            current_close = data['Close'].iloc[-1]
            if pd.isna(current_close): current_close = last_data['Close']
            
            # Ubah data terakhir menjadi dictionary untuk JSON
            last_data_dict = last_data.to_dict()

            analysis_log.append("\n" + "=" * 70)
            analysis_log.append("ANALISIS TEKNIKAL TERAKHIR")
            analysis_log.append("=" * 70)
            analysis_log.append(f"\nHarga Penutupan Terakhir: {current_close:.0f}")
            analysis_log.append(f"Swing High (60 hari): {swing_high:.0f}")
            analysis_log.append(f"Swing Low (60 hari): {swing_low:.0f}")

            # === FIBONACCI (DIUBAH) ===
            fib_lines = interpretasi_fibonacci(current_close, fib_levels)
            analysis_log.extend(fib_lines) # Tambahkan hasil fibonacci ke log

            # === RSI ===
            if 'RSI_14' in last_data.index:
                rsi_val = last_data['RSI_14']
                analysis_log.append(f"\n[RSI_14]: {rsi_val:.2f}")
                if rsi_val > 70: analysis_log.append("   -> Overbought (Jenuh Beli)")
                elif rsi_val < 30: analysis_log.append("   -> Oversold (Jenuh Jual)")
                else: analysis_log.append("   -> Netral")

            # === MFI ===
            if 'MFI_14' in last_data.index:
                mfi_val = last_data['MFI_14']
                analysis_log.append(f"\n[MFI_14]: {mfi_val:.2f}")
                if mfi_val > 80: analysis_log.append("   -> Overbought (Aliran Uang Keluar Kuat)")
                elif mfi_val < 20: analysis_log.append("   -> Oversold (Aliran Uang Masuk Kuat)")
                else: analysis_log.append("   -> Netral")

            # === STOCH RSI ===
            if 'STOCHRSIk_14_14_3_3' in last_data.index:
                stoch_k, stoch_d = last_data['STOCHRSIk_14_14_3_3'], last_data['STOCHRSId_14_14_3_3']
                analysis_log.append(f"\n[Stoch RSI]: K={stoch_k:.2f}, D={stoch_d:.2f}")
                if stoch_k > 80: analysis_log.append("   -> Overbought (Momentum Jangka Pendek Kuat)")
                elif stoch_k < 20: analysis_log.append("   -> Oversold (Momentum Jangka Pendek Lemah)")
                if stoch_k > stoch_d: analysis_log.append("   -> K di atas D (Potensi Bullish)")
                else: analysis_log.append("   -> K di bawah D (Potensi Bearish)")

            # === MACD ===
            if 'MACD_12_26_9' in last_data.index:
                macd_val, signal_val, hist_val = last_data['MACD_12_26_9'], last_data['MACDs_12_26_9'], last_data['MACDh_12_26_9']
                analysis_log.append(f"\n[MACD]: MACD={macd_val:.2f}, Signal={signal_val:.2f}, Hist={hist_val:.2f}")
                if macd_val > signal_val and hist_val > 0: analysis_log.append("   -> Golden Cross (Tren Bullish Menguat)")
                elif macd_val < signal_val and hist_val < 0: analysis_log.append("   -> Death Cross (Tren Bearish Menguat)")

            # === PIVOT POINTS ===
            if 'P_auto15' in last_data.index:
                p, s1, r1, s2, r2 = last_data['P_auto15'], last_data['S1_auto15'], last_data['R1_auto15'], last_data['S2_auto15'], last_data['R2_auto15']
                analysis_log.append(f"\n[Pivot Points Auto 15 Hari (Fraksi BEI)]")
                analysis_log.append(f"   R2={r2:.0f}, R1={r1:.0f}, P={p:.0f}, S1={s1:.0f}, S2={s2:.0f}")
                if current_close > r2: analysis_log.append(f"   -> Harga ({current_close:.0f}) di atas R2 (Breakout Kuat!)")
                elif current_close > r1: analysis_log.append(f"   -> Harga ({current_close:.0f}) di atas R1 (Area Resisten)")
                elif current_close > p: analysis_log.append(f"   -> Harga ({current_close:.0f}) di atas Pivot (Bullish Zone)")
                elif current_close > s1: analysis_log.append(f"   -> Harga ({current_close:.0f}) di bawah Pivot (Bearish Zone)")
                elif current_close > s2: analysis_log.append(f"   -> Harga ({current_close:.0f}) di bawah S1 (Area Support)")
                else: analysis_log.append(f"   -> Harga ({current_close:.0f}) di bawah S2 (Breakdown Kuat!)")

            # === KESIMPULAN TRADING ===
            analysis_log.append("\n" + "=" * 70)
            analysis_log.append("REKOMENDASI TRADING (GUNAKAN DENGAN RISIKO SENDIRI)")
            analysis_log.append("=" * 70)

            sinyal_bullish, sinyal_bearish = 0, 0
            if 'RSI_14' in last_data.index and last_data['RSI_14'] < 30: sinyal_bullish += 1
            if 'RSI_14' in last_data.index and last_data['RSI_14'] > 70: sinyal_bearish += 1
            if 'MFI_14' in last_data.index and last_data['MFI_14'] < 20: sinyal_bullish += 1
            if 'MFI_14' in last_data.index and last_data['MFI_14'] > 80: sinyal_bearish += 1
            if 'STOCHRSIk_14_14_3_3' in last_data.index and last_data['STOCHRSIk_14_14_3_3'] < 20: sinyal_bullish += 1
            if 'STOCHRSIk_14_14_3_3' in last_data.index and last_data['STOCHRSIk_14_14_3_3'] > 80: sinyal_bearish += 1
            if 'MACD_12_26_9' in last_data.index and last_data['MACD_12_26_9'] > last_data['MACDs_12_26_9']: sinyal_bullish += 1
            if 'MACD_12_26_9' in last_data.index and last_data['MACD_12_26_9'] < last_data['MACDs_12_26_9']: sinyal_bearish += 1
            if fib_levels:
                if current_close < fib_levels['0.618 (Golden)'] and current_close > fib_levels['0.382']: sinyal_bullish += 2
                if current_close > fib_levels['1.0 (High)']: sinyal_bullish += 1
                if current_close < fib_levels['0.618 (Golden)']: sinyal_bearish += 1

            if sinyal_bullish > sinyal_bearish:
                analysis_log.append("🟢 SINYAL: BULLISH (Pertimbangkan BUY)")
                if fib_levels:
                    if current_close > fib_levels['1.0 (High)']:
                        analysis_log.append("   -> Status: Breakout (Harga di atas Swing High)")
                        analysis_log.append(f"   Target 1: Ext 1.272 ({fib_levels['1.272 (Ext)']:.0f})")
                        analysis_log.append(f"   Target 2: Ext 1.618 ({fib_levels['1.618 (Ext)']:.0f})")
                        analysis_log.append(f"   Support : High 1.0 ({fib_levels['1.0 (High)']:.0f})")
                    else:
                        analysis_log.append("   -> Status: Retracement (Harga pullback, cari support)")
                        analysis_log.append(f"   Support : Fib 0.618 ({fib_levels['0.618 (Golden)']:.0f}) / Fib 0.500 ({fib_levels['0.500']:.0f})")
                        analysis_log.append(f"   Target 1: Fib 0.786 ({fib_levels['0.786']:.0f})")
                        analysis_log.append(f"   Target 2: High 1.0 ({fib_levels['1.0 (High)']:.0f})")

            elif sinyal_bearish > sinyal_bullish:
                analysis_log.append("🔴 SINYAL: BEARISH (Pertimbangkan SELL/Hindari)")
                if fib_levels:
                    analysis_log.append(f"   Resistance: Fib 0.618 ({fib_levels['0.618 (Golden)']:.0f})")
                    analysis_log.append(f"   Support 1 : Fib 0.500 ({fib_levels['0.500']:.0f})")
                    analysis_log.append(f"   Support 2 : Fib 0.382 ({fib_levels['0.382']:.0f})")
                    analysis_log.append(f"   Support 3 : Low 0.0 ({fib_levels['0.0 (Low)']:.0f})")
            else:
                analysis_log.append("⚪ SINYAL: NETRAL (Tunggu Konfirmasi)")

            analysis_log.append("\n⚠️  DISCLAIMER: Ini bukan saran investasi resmi.")
            analysis_log.append("    Lakukan analisis sendiri dan konsultasikan dengan advisor.")

            # === FUNGSI PLOT_CHART DIHAPUS DARI SINI ===
        
        # 5. Kembalikan semua log analisis sebagai satu string JSON
        final_analysis_text = "\n".join(analysis_log)
        
        return jsonify({
            "status": "success",
            "ticker": req_data['ticker'].upper(),
            "analysis_text": final_analysis_text,
            "last_indicators": last_data_dict
        })

    except Exception as e:
        # Tangani error dan kembalikan sebagai JSON
        error_message = f"Terjadi error: {e}"
        traceback.print_exc(file=io.StringIO()) # Cetak ke log server
        return jsonify({"status": "error", "message": error_message}), 500

# Baris ini hanya untuk testing lokal, Vercel akan mengabaikannya
if __name__ == "__main__":
    app.run(debug=True, port=5000)