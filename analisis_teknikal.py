import yfinance as yf
import pandas_ta as pta
import pandas as pd
import numpy as np
import traceback
import io

# === Fungsi Pembantu ===
def bulatkan_fraksi(harga):
    if harga is None: return None
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
    rounded_levels = {key: bulatkan_fraksi(value) for key, value in levels_raw.items()}
    return rounded_levels, swing_high, swing_low

def hitung_pivot_points_auto(data, periode=15):
    pivot_list, r1_list, r2_list, s1_list, s2_list = [], [], [], [], []
    for i in range(len(data)):
        window = data.iloc[max(0, i - periode + 1):i + 1]
        high, low, close = window['High'].max(), window['Low'].min(), window['Close'].iloc[-1]
        pivot_raw = (high + low + close) / 3
        pivot_list.append(bulatkan_fraksi(pivot_raw))
        r1_list.append(bulatkan_fraksi((2 * pivot_raw) - low))
        s1_list.append(bulatkan_fraksi((2 * pivot_raw) - high))
        r2_list.append(bulatkan_fraksi(pivot_raw + (high - low)))
        s2_list.append(bulatkan_fraksi(pivot_raw - (high - low)))
    return pivot_list, r1_list, r2_list, s1_list, s2_list

def interpretasi_fibonacci(current_price, fib_levels):
    output_lines = [f"\n[Fibonacci Retracement & Extension (Fraksi BEI)]", f"Harga Saat Ini: {current_price:.0f}", "-" * 50]
    if not fib_levels:
        output_lines.append("   -> Level Fibonacci tidak dapat dihitung.")
        return output_lines
    sorted_levels = sorted(fib_levels.items(), key=lambda item: item[1], reverse=True)
    for level_name, level_value in sorted_levels:
        output_lines.append(f"Fib {level_name:<15}: {level_value:.0f}")
    output_lines.append("-" * 50)
    # (Logika interpretasi disalin di sini)
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

# === FUNGSI UTAMA TEKNIKAL ===
def get_technical_analysis(ticker_symbol_with_jk):
    analysis_log = []
    try:
        analysis_log.append(f"Mengambil data teknikal untuk: {ticker_symbol_with_jk}")
        data = yf.Ticker(ticker_symbol_with_jk).history(period="2y", interval="1d")
        if data.empty:
            analysis_log.append("Gagal mengambil data.")
            return analysis_log, {}, False
        analysis_log.append(f"✅ Data berhasil diambil: {len(data)} baris data")

        # Hitung Indikator
        analysis_log.append("⏳ Menghitung indikator teknikal...")
        data.ta.macd(append=True)
        data.ta.rsi(length=14, append=True)
        data.ta.stochrsi(append=True)
        data.ta.mfi(length=14, append=True)
        
        pivot_list, r1_list, r2_list, s1_list, s2_list = hitung_pivot_points_auto(data)
        data['P_auto15'], data['R1_auto15'], data['S1_auto15'], data['R2_auto15'], data['S2_auto15'] = pivot_list, r1_list, s1_list, r2_list, s2_list
        
        fib_levels, swing_high, swing_low = hitung_fibonacci(data)
        
        # Analisis Data Terakhir
        data_bersih = data.dropna()
        if data_bersih.empty:
            analysis_log.append("   -> GAGAL: Tidak ada data valid setelah dihitung.")
            return analysis_log, {}, False
            
        last_data = data_bersih.iloc[-1]
        current_close = data['Close'].iloc[-1]
        
        analysis_log.extend(["\n" + "=" * 70, "ANALISIS TEKNIKAL TERAKHIR", "=" * 70, f"\nHarga Penutupan Terakhir: {current_close:.0f}"])
        analysis_log.extend(interpretasi_fibonacci(current_close, fib_levels))
        
        # (Logika interpretasi indikator disalin di sini)
        # === RSI ===
        rsi_val = last_data.get('RSI_14')
        if rsi_val is not None:
            analysis_log.append(f"\n[RSI_14]: {rsi_val:.2f}")
            if rsi_val > 70: analysis_log.append("   -> Overbought (Jenuh Beli)")
            elif rsi_val < 30: analysis_log.append("   -> Oversold (Jenuh Jual)")
            else: analysis_log.append("   -> Netral")
        # === MFI ===
        mfi_val = last_data.get('MFI_14')
        if mfi_val is not None:
            analysis_log.append(f"\n[MFI_14]: {mfi_val:.2f}")
            if mfi_val > 80: analysis_log.append("   -> Overbought (Aliran Uang Keluar Kuat)")
            elif mfi_val < 20: analysis_log.append("   -> Oversold (Aliran Uang Masuk Kuat)")
            else: analysis_log.append("   -> Netral")
        # === STOCH RSI ===
        stoch_k, stoch_d = last_data.get('STOCHRSIk_14_14_3_3'), last_data.get('STOCHRSId_14_14_3_3')
        if stoch_k is not None and stoch_d is not None:
            analysis_log.append(f"\n[Stoch RSI]: K={stoch_k:.2f}, D={stoch_d:.2f}")
            if stoch_k > 80: analysis_log.append("   -> Overbought (Momentum Jangka Pendek Kuat)")
            elif stoch_k < 20: analysis_log.append("   -> Oversold (Momentum Jangka Pendek Lemah)")
            if stoch_k > stoch_d: analysis_log.append("   -> K di atas D (Potensi Bullish)")
            else: analysis_log.append("   -> K di bawah D (Potensi Bearish)")
        # === MACD ===
        macd_val, signal_val, hist_val = last_data.get('MACD_12_26_9'), last_data.get('MACDs_12_26_9'), last_data.get('MACDh_12_26_9')
        if macd_val is not None and signal_val is not None and hist_val is not None:
            analysis_log.append(f"\n[MACD]: MACD={macd_val:.2f}, Signal={signal_val:.2f}, Hist={hist_val:.2f}")
            if macd_val > signal_val and hist_val > 0: analysis_log.append("   -> Golden Cross (Tren Bullish Menguat)")
            elif macd_val < signal_val and hist_val < 0: analysis_log.append("   -> Death Cross (Tren Bearish Menguat)")
        # === PIVOT POINTS ===
        p, s1, r1, s2, r2 = last_data.get('P_auto15'), last_data.get('S1_auto15'), last_data.get('R1_auto15'), last_data.get('S2_auto15'), last_data.get('R2_auto15')
        if p is not None:
            analysis_log.append(f"\n[Pivot Points Auto 15 Hari (Fraksi BEI)]")
            analysis_log.append(f"   R2={r2:.0f}, R1={r1:.0f}, P={p:.0f}, S1={s1:.0f}, S2={s2:.0f}")
            if current_close > r2: analysis_log.append(f"   -> Harga ({current_close:.0f}) di atas R2 (Breakout Kuat!)")
            elif current_close > r1: analysis_log.append(f"   -> Harga ({current_close:.0f}) di atas R1 (Area Resisten)")
            elif current_close > p: analysis_log.append(f"   -> Harga ({current_close:.0f}) di atas Pivot (Bullish Zone)")
            else: analysis_log.append(f"   -> Harga ({current_close:.0f}) di bawah Pivot (Bearish Zone)")
        
        # Rekomendasi
        analysis_log.extend(["\n" + "=" * 70, "REKOMENDASI TRADING (GUNAKAN DENGAN RISIKO SENDIRI)", "=" * 70])
        sinyal_bullish, sinyal_bearish = 0, 0
        if rsi_val < 30: sinyal_bullish += 1
        if rsi_val > 70: sinyal_bearish += 1
        if mfi_val < 20: sinyal_bullish += 1
        if mfi_val > 80: sinyal_bearish += 1
        if stoch_k < 20: sinyal_bullish += 1
        if stoch_k > 80: sinyal_bearish += 1
        if macd_val > signal_val: sinyal_bullish += 1
        if macd_val < signal_val: sinyal_bearish += 1
        if current_close > fib_levels.get('1.0 (High)', float('inf')): sinyal_bullish += 1
        
        if sinyal_bullish > sinyal_bearish:
            analysis_log.append("🟢 SINYAL: BULLISH (Pertimbangkan BUY)")
            # (Logika target & support disalin di sini)
            if current_close > fib_levels['1.0 (High)']:
                analysis_log.append("   -> Status: Breakout (Harga di atas Swing High)")
                analysis_log.append(f"   Target 1: Ext 1.272 ({fib_levels.get('1.272 (Ext)'):.0f})")
                analysis_log.append(f"   Target 2: Ext 1.618 ({fib_levels.get('1.618 (Ext)'):.0f})")
                analysis_log.append(f"   Support : High 1.0 ({fib_levels.get('1.0 (High)'):.0f})")
            else:
                analysis_log.append("   -> Status: Retracement (Harga pullback, cari support)")
                analysis_log.append(f"   Support : Fib 0.618 ({fib_levels.get('0.618 (Golden)'):.0f}) / Fib 0.500 ({fib_levels.get('0.500'):.0f})")
                analysis_log.append(f"   Target 2: High 1.0 ({fib_levels.get('1.0 (High)'):.0f})")
        elif sinyal_bearish > sinyal_bullish:
            analysis_log.append("🔴 SINYAL: BEARISH (Pertimbangkan SELL/Hindari)")
        else:
            analysis_log.append("⚪ SINYAL: NETRAL (Tunggu Konfirmasi)")

        analysis_log.append("\n⚠️  DISCLAIMER: Ini bukan saran investasi resmi.")
        
        return analysis_log, last_data.to_dict(), True

    except Exception as e:
        analysis_log.append(f"Terjadi error teknikal: {e}")
        traceback.print_exc(file=io.StringIO())
        return analysis_log, {}, False
