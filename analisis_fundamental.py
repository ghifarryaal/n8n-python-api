import yfinance as yf
import pandas as pd
import traceback
from datetime import datetime

# === Database Rata-Rata Sektor dari IDX ===
SECTOR_RATIOS = {
    'A. Energy': {'PER': 13.14, 'PBV': 3.63, 'DER': 0.57},
    'B. Basic Materials': {'PER': 14.04, 'PBV': 2.77, 'DER': 0.62},
    'C. Industrials': {'PER': 12.31, 'PBV': 1.11, 'DER': 0.48},
    'D. Consumer Non-Cyclicals': {'PER': 14.31, 'PBV': 1.96, 'DER': 0.73},
    'E. Consumer Cyclicals': {'PER': 17.32, 'PBV': 1.78, 'DER': 0.46},
    'F. Healthcare': {'PER': 15.51, 'PBV': 3.74, 'DER': 0.52},
    'G. Financials': {'PER': 14.67, 'PBV': 1.66, 'DER': 2.06},
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

# ========= FUNGSI ANALISIS FUNDAMENTAL (UNTUK API) =========
def get_fundamental_analysis(ticker_symbol):
    """
    Mengambil dan menganalisis data fundamental (PER, PBV, ROE, DER, Yield)
    dan membandingkannya dengan rata-rata sektor IDX.
    Memprioritaskan perhitungan manual untuk PBV, ROE, dan DER.
    Mengembalikan hasilnya sebagai (list_of_strings, structured_dict, success_status).
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
    
    analysis_log.append(f"🔍 Mengambil data fundamental untuk: {ticker_symbol}...")
    
    ticker = yf.Ticker(ticker_symbol)

    try:
        info = ticker.info
        if not info or 'regularMarketPrice' not in info or info.get('regularMarketPrice') is None:
            analysis_log.append(f"❌ Gagal mengambil data fundamental lengkap untuk {ticker_symbol}.")
            analysis_log.append("💡 Pastikan kode ticker benar (contoh: BBCA.JK untuk BCA)")
            return analysis_log, structured_data, False # Mengembalikan status Gagal

        # ==================================
        # LANGKAH 1: PULL SEMUA DATA
        # ==================================
        nama = info.get('shortName', ticker_symbol.replace(".JK",""))
        harga = info.get('regularMarketPrice')
        yfinance_sektor = info.get('sector')
        industri = info.get('industry')
        market_cap = info.get('marketCap')
        shares_outstanding = info.get('sharesOutstanding')

        # Data Rasio Langsung (digunakan sebagai fallback)
        per = info.get('trailingPE') 
        pbv_yfinance = info.get('priceToBook') # PBV langsung
        roe_yfinance = info.get('returnOnEquity') # ROE langsung
        der_percent_yfinance = info.get('debtToEquity') # DER langsung (% dari yfinance)
        dps_tahunan = info.get('dividendRate')
        div_yield_yfinance = info.get('dividendYield')
        book_value_ps = info.get('bookValue') # BVPS langsung
        
        # Data Fallback dari .info (kurang akurat, akan ditimpa jika ada data LK)
        total_equity_info = info.get('totalStockholderEquity') 
        net_income_info = info.get('netIncomeToCommon')
        total_debt_info = info.get('totalDebt') 
        
        analysis_log.append("   -> Data Pasar (dari .info) berhasil diambil.")

        # ==================================
        # LANGKAH 1.B: PULL DATA LAPORAN KEUANGAN (LEBIH AKURAT)
        # ==================================
        analysis_log.append("   -> Mengambil Laporan Keuangan (untuk akurasi)...")
        
        balance_sheet_q = ticker.quarterly_balance_sheet
        balance_sheet_a = ticker.balance_sheet 

        net_income = net_income_info # Default ke data .info
        total_equity = total_equity_info # Default ke data .info
        total_debt = total_debt_info # Default ke data .info

        net_income_new = None
        total_equity_new = None
        total_debt_new = None
        sumber_laporan_income = "Fallback (.info)"
        sumber_laporan_balance = "Fallback (.info)"
        
        try:
            # Prioritas 1: Coba ambil data TTM
            try:
                financials_ttm = ticker.financials_ttm
                if not financials_ttm.empty and 'Net Income' in financials_ttm.index:
                    net_income_new = financials_ttm.loc['Net Income'].iloc[0]
                    sumber_laporan_income = "TTM"
            except AttributeError:
                analysis_log.append("   -> Atribut 'financials_ttm' tidak ditemukan.")
                # Fallback ke data tahunan jika TTM gagal
                financials_annual = ticker.financials
                if not financials_annual.empty and 'Net Income To Common Stockholders' in financials_annual.index:
                    net_income_new = financials_annual.loc['Net Income To Common Stockholders'].iloc[0]
                    sumber_laporan_income = "Tahunan Terakhir"
                elif not financials_annual.empty and 'Net Income' in financials_annual.index: # Coba key lain
                    net_income_new = financials_annual.loc['Net Income'].iloc[0]
                    sumber_laporan_income = "Tahunan Terakhir (key: Net Income)"

            # Prioritas 1: Ambil Ekuitas Kuartal Terakhir (paling update)
            # Mencoba beberapa kemungkinan key untuk ekuitas
            equity_keys = ['Stockholder Equity', 'Total Equity Gross Minority Interest', 'Total Stockholder Equity']
            for key in equity_keys:
                 if not balance_sheet_q.empty and key in balance_sheet_q.index:
                     total_equity_new = balance_sheet_q.loc[key].iloc[0]
                     sumber_laporan_balance = "Kuartal Terakhir"
                     break
            # Fallback: Ambil Ekuitas Tahunan Terakhir
            if total_equity_new is None:
                for key in equity_keys:
                    if not balance_sheet_a.empty and key in balance_sheet_a.index:
                        total_equity_new = balance_sheet_a.loc[key].iloc[0]
                        sumber_laporan_balance = "Tahunan Terakhir"
                        break
                
            # Prioritas 1: Ambil Total Utang Kuartal Terakhir
            debt_keys = ['Total Debt', 'Total Liabilities Net Minority Interest']
            for key in debt_keys:
                if not balance_sheet_q.empty and key in balance_sheet_q.index:
                    total_debt_new = balance_sheet_q.loc[key].iloc[0]
                    break
            # Fallback: Ambil Total Utang Tahunan Terakhir
            if total_debt_new is None:
                 for key in debt_keys:
                     if not balance_sheet_a.empty and key in balance_sheet_a.index:
                         total_debt_new = balance_sheet_a.loc[key].iloc[0]
                         break
                
            # Timpa data .info yang kurang akurat dengan data baru yang lebih akurat
            data_lk_found = False
            if net_income_new is not None:
                net_income = net_income_new
                data_lk_found = True
            if total_equity_new is not None:
                total_equity = total_equity_new
                data_lk_found = True
            if total_debt_new is not None:
                total_debt = total_debt_new
                data_lk_found = True
                
            if data_lk_found:
                analysis_log.append(f"   -> Data Laporan Keuangan berhasil diambil:")
                analysis_log.append(f"      -> Sumber Laba Bersih: {sumber_laporan_income}")
                analysis_log.append(f"      -> Sumber Ekuitas/Utang: {sumber_laporan_balance}")
                if net_income is not None: analysis_log.append(f"      -> Laba Bersih (Akurat): Rp {net_income:,.0f}")
                if total_equity is not None: analysis_log.append(f"      -> Total Ekuitas (Akurat): Rp {total_equity:,.0f}")
                if total_debt is not None: analysis_log.append(f"      -> Total Utang (Akurat): Rp {total_debt:,.0f}")
            else:
                 analysis_log.append("   -> Tidak ada data laporan keuangan (TTM/Tahunan/Kuartal) yang ditemukan.")
                 analysis_log.append("   -> Menggunakan data fallback dari .info (mungkin kurang akurat).")

        except Exception as e:
            analysis_log.append(f"   ⚠️  Gagal memproses data laporan keuangan: {e}")
            analysis_log.append("   -> Menggunakan data fallback dari .info (mungkin kurang akurat).")
        
        # Simpan data yang sudah divalidasi/dihitung ke structured_data
        structured_data["emiten"]["nama"] = nama
        structured_data["emiten"]["harga"] = harga
        structured_data["emiten"]["sektor"] = yfinance_sektor
        structured_data["emiten"]["industri"] = industri
        structured_data["emiten"]["market_cap"] = market_cap
        structured_data["emiten"]["shares_outstanding"] = shares_outstanding
        structured_data["emiten"]["PER_yfinance"] = per # Simpan PER dari info
        structured_data["emiten"]["PBV_yfinance"] = pbv_yfinance
        structured_data["emiten"]["ROE_yfinance"] = roe_yfinance
        structured_data["emiten"]["DER_percent_yfinance"] = der_percent_yfinance
        structured_data["emiten"]["DPS"] = dps_tahunan
        structured_data["emiten"]["yield_yfinance"] = div_yield_yfinance
        structured_data["emiten"]["net_income"] = net_income
        structured_data["emiten"]["total_equity"] = total_equity
        structured_data["emiten"]["total_debt"] = total_debt
        structured_data["emiten"]["book_value_ps_yfinance"] = book_value_ps


        # ==================================
        # LANGKAH 2: TAMPILKAN INFO DASAR
        # ==================================
        analysis_log.append(f"\n📊 HASIL ANALISIS FUNDAMENTAL")
        analysis_log.append(f"{'='*70}")
        analysis_log.append(f"📌 Nama Perusahaan : {nama}")
        analysis_log.append(f"💰 Harga Saat Ini  : Rp {harga:,.0f}")
        
        if yfinance_sektor:
            analysis_log.append(f"🏢 Sektor          : {yfinance_sektor}")
        if industri:
            analysis_log.append(f"🏭 Industri        : {industri}")
        
        if market_cap:
            market_cap_T = market_cap / 1_000_000_000_000
            analysis_log.append(f"💼 Kapitalisasi    : Rp {market_cap_T:,.2f} Triliun")
        
        analysis_log.append(f"{'='*70}")

        # ==================================
        # LANGKAH 3: TAMPILKAN BENCHMARK
        # ==================================
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

                analysis_log.append(f"\n📈 BENCHMARK SEKTOR & PASAR")
                analysis_log.append(f"{'─'*70}")
                analysis_log.append(f"Rata-rata Sektor ({idx_sektor_key}):")
                analysis_log.append(f"   • PER : {avg_per:.2f}x")
                analysis_log.append(f"   • PBV : {avg_pbv:.2f}x")
                analysis_log.append(f"   • DER : {avg_der:.2f}x")
                analysis_log.append(f"\nRata-rata Pasar (IHSG):")
                analysis_log.append(f"   • PER : {SECTOR_RATIOS['Market PER']:.2f}x")
                analysis_log.append(f"   • PBV : {SECTOR_RATIOS['Market PBV']:.2f}x")
        else:
            analysis_log.append(f"\n⚠️ Tidak dapat menemukan pemetaan sektor untuk '{yfinance_sektor}'")
        
        analysis_log.append(f"{'='*70}")

        # ==================================
        # LANGKAH 4: MULAI ANALISIS RASIO
        # ==================================

        # --- 1. Price-to-Earnings Ratio (PER) ---
        analysis_log.append(f"\n📊 1. PRICE-TO-EARNINGS RATIO (PER)")
        analysis_log.append(f"{'─'*70}")
        if per is not None:
            analysis_log.append(f"   📍 PER Emiten: {per:.2f}x (Data TTM dari yfinance .info)")
            structured_data["emiten"]["PER_final"] = per
            
            if avg_per:
                diff_per = ((per - avg_per) / avg_per) * 100
                if per < avg_per:
                    analysis_log.append(f"   ✅ Komparasi: {diff_per:.1f}% DI BAWAH rata-rata sektor ({avg_per:.2f}x)")
                    analysis_log.append(f"   💡 Indikasi: Potensi Undervalued (Murah)")
                else:
                    analysis_log.append(f"   ⚠️  Komparasi: {diff_per:.1f}% DI ATAS rata-rata sektor ({avg_per:.2f}x)")
                    analysis_log.append(f"   💡 Indikasi: Potensi Overvalued (Mahal)")
            
            analysis_log.append(f"\n   💬 INTERPRETASI:")
            if per < 0:
                analysis_log.append(f"      🔴 Perusahaan merugi (PER negatif)")
            elif per < 15:
                analysis_log.append(f"      🟢 Potensi Undervalued")
            else:
                analysis_log.append(f"      🟡 Potensi Overvalued")
        else:
            analysis_log.append("   ❌ Data PER tidak tersedia (perusahaan mungkin merugi atau baru IPO)")
            structured_data["emiten"]["PER_final"] = None

        # --- 2. Price-to-Book Value (PBV) & Book Value Per Share (BVPS) ---
        analysis_log.append(f"\n📊 2. PRICE-TO-BOOK VALUE (PBV)")
        analysis_log.append(f"{'─'*70}")

        pbv_final = None
        bvps_final = None
        sumber_data_pbv = ""
        sumber_bvps = ""

        # Hitung BVPS dulu (diperlukan untuk PBV manual)
        if total_equity is not None and shares_outstanding is not None and shares_outstanding > 0:
            bvps_final = total_equity / shares_outstanding
            sumber_bvps = f"Manual (Ekuitas LK {sumber_laporan_balance} / Saham Beredar)"
        elif book_value_ps is not None: # Fallback ke BVPS langsung
             bvps_final = book_value_ps
             sumber_bvps = "Data Langsung yfinance (.info)"
             
        structured_data["emiten"]["BVPS_final"] = bvps_final
        structured_data["emiten"]["BVPS_source"] = sumber_bvps

        # Prioritas 1: Hitung PBV Manual
        if bvps_final is not None and bvps_final != 0 and harga is not None:
             pbv_final = harga / bvps_final
             sumber_data_pbv = "Hitungan Manual (Harga / BVPS Manual)"
             
             analysis_log.append(f"   🧮 PERHITUNGAN MANUAL PBV (Prioritas):")
             analysis_log.append(f"      • Harga Saham : Rp {harga:,.0f}")
             analysis_log.append(f"      • BVPS        : Rp {bvps_final:,.2f} (Sumber: {sumber_bvps})")
             analysis_log.append(f"      • Rumus: PBV = Harga Saham / BVPS")
        
        # Prioritas 2 (Fallback): Data PBV Langsung
        elif pbv_yfinance is not None:
             pbv_final = pbv_yfinance
             sumber_data_pbv = "Data Langsung yfinance (.info)"
             analysis_log.append("   ℹ️  Perhitungan manual PBV tidak memungkinkan, menggunakan data PBV langsung dari .info.")

        # Tampilkan hasil jika ada
        if pbv_final is not None:
            structured_data["emiten"]["PBV_final"] = pbv_final
            structured_data["emiten"]["PBV_source"] = sumber_data_pbv
            analysis_log.append(f"\n   📍 PBV Emiten: {pbv_final:.2f}x")
            analysis_log.append(f"      (Sumber: {sumber_data_pbv})")
            
            # Komparasi dengan sektor
            if avg_pbv:
                diff_pbv = ((pbv_final - avg_pbv) / avg_pbv) * 100
                analysis_log.append(f"\n   📊 KOMPARASI:")
                if pbv_final < avg_pbv:
                    analysis_log.append(f"      ✅ {abs(diff_pbv):.1f}% DI BAWAH rata-rata sektor ({avg_pbv:.2f}x)")
                    analysis_log.append(f"      💡 Indikasi: Potensi Undervalued (Murah)")
                else:
                    analysis_log.append(f"      ⚠️  {diff_pbv:.1f}% DI ATAS rata-rata sektor ({avg_pbv:.2f}x)")
                    analysis_log.append(f"      💡 Indikasi: Potensi Overvalued (Mahal)")
            
            # Interpretasi
            analysis_log.append(f"\n   💬 INTERPRETASI:")
            if pbv_final < 0:
                analysis_log.append(f"      🔴 Nilai buku negatif (liabilitas > aset)")
            elif pbv_final < 1:
                analysis_log.append(f"      🟢 Undervalued (harga di bawah nilai buku)")
                analysis_log.append(f"         Investor membeli saham dengan diskon {((1-pbv_final)*100):.1f}%")
            else:
                analysis_log.append(f"      🟡 Premium (diperdagangkan di atas nilai buku)")
                analysis_log.append(f"         Investor membayar premium {((pbv_final-1)*100):.1f}%")
                
            # Tampilkan BVPS sebagai info tambahan jika belum ditampilkan
            if bvps_final is not None and sumber_data_pbv != "Hitungan Manual (Harga / BVPS Manual)":
                 analysis_log.append(f"\n   📖 INFO TAMBAHAN (BVPS):")
                 analysis_log.append(f"      └─ Book Value Per Share: Rp {bvps_final:,.2f} ({sumber_bvps})")
                 
        else:
            analysis_log.append("   ❌ Data PBV tidak tersedia")
            structured_data["emiten"]["PBV_final"] = None
            
        # --- 3. Debt-to-Equity Ratio (DER) --- 
        analysis_log.append(f"\n📊 3. DEBT-TO-EQUITY RATIO (DER)")
        analysis_log.append(f"{'─'*70}")
        
        der_final_ratio = None
        sumber_data_der = ""
        
        # Prioritas 1: Hitung Manual (Total Utang / Total Ekuitas dari Laporan Keuangan)
        if total_debt is not None and total_equity is not None and total_equity > 0:
            der_final_ratio = total_debt / total_equity
            sumber_data_der = f"Hitungan Manual (LK {sumber_laporan_balance})"
            
            analysis_log.append(f"   🧮 PERHITUNGAN MANUAL DER (Prioritas):")
            analysis_log.append(f"      • Total Utang      : Rp {total_debt:,.0f}")
            analysis_log.append(f"      • Total Ekuitas    : Rp {total_equity:,.0f}")
            analysis_log.append(f"      • Rumus: DER = Total Utang / Total Ekuitas")
        
        # Prioritas 2 (Fallback): Data DER Langsung (%) dari yfinance
        elif der_percent_yfinance is not None:
            der_final_ratio = der_percent_yfinance / 100
            sumber_data_der = "Data Langsung yfinance (.info)"
            analysis_log.append("   ℹ️  Perhitungan manual tidak tersedia, menggunakan data DER langsung dari .info.")

        # Tampilkan hasil jika ada
        if der_final_ratio is not None:
            structured_data["emiten"]["DER_final"] = der_final_ratio
            structured_data["emiten"]["DER_source"] = sumber_data_der
            analysis_log.append(f"\n   📍 DER Emiten: {der_final_ratio:.2f}x (atau {der_final_ratio*100:.2f}%)")
            analysis_log.append(f"      (Sumber: {sumber_data_der})")
            
            if avg_der is not None:
                diff_der = ((der_final_ratio - avg_der) / avg_der) * 100
                analysis_log.append(f"\n   📊 KOMPARASI:")
                if der_final_ratio < avg_der:
                    analysis_log.append(f"      ✅ {abs(diff_der):.1f}% LEBIH RENDAH dari rata-rata sektor ({avg_der:.2f}x)")
                    analysis_log.append(f"      💡 Indikasi: Risiko Utang Rendah")
                else:
                    analysis_log.append(f"      ⚠️  {diff_der:.1f}% LEBIH TINGGI dari rata-rata sektor ({avg_der:.2f}x)")
                    analysis_log.append(f"      💡 Indikasi: Risiko Utang Tinggi")

            analysis_log.append(f"\n   💬 INTERPRETASI:")
            if der_final_ratio < 0.5:
                analysis_log.append(f"      🟢 Konservatif (modal > utang)")
            elif der_final_ratio <= 1.0:
                analysis_log.append(f"      🟡 Seimbang (umumnya sehat)")
            else: 
                analysis_log.append(f"      🔴 Agresif (utang > modal)")
            
            analysis_log.append(f"      ℹ️  Catatan: Sektor 'Financials' wajar memiliki DER tinggi")
        else:
            analysis_log.append("   ❌ Data DER tidak tersedia")
            structured_data["emiten"]["DER_final"] = None

        # --- 4. RETURN ON EQUITY (ROE) --- 
        analysis_log.append(f"\n📊 4. RETURN ON EQUITY (ROE)")
        analysis_log.append(f"{'─'*70}")
        
        roe_final = None
        sumber_data_roe = ""

        # Prioritas 1: Hitung Manual (Laba Bersih / Total Ekuitas dari Laporan Keuangan)
        if net_income is not None and total_equity is not None and total_equity > 0:
            roe_final = net_income / total_equity
            sumber_data_roe = f"Hitungan Manual (LK {sumber_laporan_income}/{sumber_laporan_balance})"
            
            analysis_log.append(f"   🧮 PERHITUNGAN MANUAL ROE (Prioritas):")
            analysis_log.append(f"      • Laba Bersih      : Rp {net_income:,.0f}")
            analysis_log.append(f"      • Total Ekuitas    : Rp {total_equity:,.0f}")
            analysis_log.append(f"      • Rumus: ROE = (Laba Bersih / Total Ekuitas) * 100%")
        
        # Prioritas 2 (Fallback): Data ROE TTM langsung dari yfinance
        elif roe_yfinance is not None:
            roe_final = roe_yfinance
            sumber_data_roe = "Data Langsung yfinance (.info)"
            analysis_log.append("   ℹ️  Perhitungan manual tidak tersedia, menggunakan data ROE langsung dari .info.")
        
        # Tampilkan hasil jika ada
        if roe_final is not None:
            structured_data["emiten"]["ROE_final"] = roe_final
            structured_data["emiten"]["ROE_source"] = sumber_data_roe
            roe_pct = roe_final * 100
            analysis_log.append(f"\n   📍 ROE: {roe_pct:.2f}%")
            analysis_log.append(f"      (Sumber: {sumber_data_roe})")
            
            analysis_log.append(f"\n   💬 INTERPRETASI:")
            if roe_final < 0:
                analysis_log.append(f"      🔴 Perusahaan tidak profitabel (merugi)")
            elif roe_final < 0.10: 
                analysis_log.append(f"      🟡 Profitabilitas rendah")
            elif roe_final <= 0.20:
                analysis_log.append(f"      🟢 Profitabilitas baik dan sehat")
            else: 
                analysis_log.append(f"      🔥 Profitabilitas sangat tinggi (excellent!)")
            
            analysis_log.append(f"      💡 Semakin tinggi ROE, semakin efisien perusahaan menggunakan modal")
        else:
            analysis_log.append("   ❌ Data ROE tidak tersedia (data laba bersih/ekuitas tidak lengkap)")
            structured_data["emiten"]["ROE_final"] = None

        # --- 5. Dividend Yield ---
        analysis_log.append(f"\n📊 5. DIVIDEND YIELD")
        analysis_log.append(f"{'─'*70}")
        
        div_yield_final = None
        sumber_data_yield = ""
        
        if dps_tahunan is not None and dps_tahunan > 0 and harga is not None and harga > 0:
            div_yield_final = (dps_tahunan / harga)
            sumber_data_yield = "Hitungan Manual (DPS / Harga)"
            
            analysis_log.append(f"   📍 Dividen per Lembar (Tahunan): Rp {dps_tahunan:,.2f}")
            analysis_log.append(f"   📍 Harga per Lembar Saham: Rp {harga:,.0f}")
            analysis_log.append(f"   🧮 Rumus: Dividend Yield = (DPS / Harga) × 100%")
            analysis_log.append(f"           = (Rp {dps_tahunan:,.2f} / Rp {harga:,.0f}) × 100%")
            
        elif div_yield_yfinance is not None and div_yield_yfinance > 0:
             div_yield_final = div_yield_yfinance
             sumber_data_yield = "Data Langsung yfinance (.info)"
             analysis_log.append(f"   ℹ️  Perhitungan manual tidak tersedia (data DPS kosong), menggunakan data Yield langsung dari .info.")
        
        if div_yield_final is not None:
             structured_data["emiten"]["yield_final"] = div_yield_final
             structured_data["emiten"]["yield_source"] = sumber_data_yield
             yield_pct = div_yield_final * 100
             analysis_log.append(f"\n   📍 Hasil Dividend Yield: {yield_pct:.2f}%")
             analysis_log.append(f"      (Sumber: {sumber_data_yield})")
             
             analysis_log.append(f"\n   💬 INTERPRETASI:")
             if yield_pct > 5:
                 analysis_log.append(f"      🔥 Yield sangat tinggi (attractive untuk dividend investor)")
             elif yield_pct > 3:
                 analysis_log.append(f"      🟢 Yield baik")
             elif yield_pct > 0:
                 analysis_log.append(f"      🟡 Yield rendah")
        else:
             analysis_log.append("   ❌ Perusahaan tidak membagikan dividen / data tidak tersedia")
             structured_data["emiten"]["yield_final"] = None
        
        analysis_log.append(f"\n{'='*70}")
        analysis_log.append(f"✅ Analisis selesai!")
             
        return analysis_log, structured_data, True # Mengembalikan status Sukses

    except Exception as e:
        error_msg = f"\n❌ Terjadi error saat memproses {ticker_symbol}: {e}"
        analysis_log.append(error_msg)
        # traceback.print_exc() # Jangan print traceback ke log API
        print(f"Error for {ticker_symbol}: {e}") # Print error ke log server
        return analysis_log, structured_data, False # Mengembalikan status Gagal


# ========= ENDPOINT API =========
@app.route('/api/fundamental', methods=['POST'])
def handle_fundamental_analysis():
    """
    Endpoint untuk analisis fundamental saham.
    Menerima JSON: {"ticker": "BBCA"}
    Mengembalikan analisis lengkap dalam format JSON.
    """
    try:
        req_data = request.get_json()
        if not req_data or 'ticker' not in req_data:
            return jsonify({
                "status": "error",
                "message": "Mohon kirim {'ticker': 'KODE_SAHAM'} dalam body JSON."
            }), 400

        ticker_input = req_data['ticker'].upper()
        ticker_symbol = ticker_input + ".JK"
        
        log_outputs, structured_outputs, success = get_fundamental_analysis(ticker_symbol)
        final_analysis_text = "\n".join(log_outputs)

        if not success:
            return jsonify({
                "status": "error", 
                "ticker": ticker_input,
                "analysis_text": final_analysis_text
                # Tidak menyertakan structured_data jika gagal
            }), 404 # Atau 500 tergantung errornya

        return jsonify({
            "status": "success",
            "ticker": ticker_input,
            "analysis_text": final_analysis_text,
            "structured_data": structured_outputs
        })

    except Exception as e:
        print(f"Internal server error: {e}") # Log error ke server
        # traceback.print_exc() # Bisa ditambahkan untuk detail di log server
        return jsonify({
            "status": "error",
            "message": f"Error internal server: Terjadi kesalahan tak terduga."
            # Jangan tampilkan detail error ke user
        }), 500


@app.route('/', methods=['GET'])
def home():
    """Endpoint untuk mengetes apakah server aktif."""
    return jsonify({
        "status": "active",
        "message": "Server Analisis Fundamental Aktif",
        "endpoints": {
            "/api/fundamental": "POST - Analisis fundamental saham (body: {'ticker': 'KODE_SAHAM'})"
        }
    })


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint untuk monitoring."""
    return jsonify({"status": "healthy"}), 200


# if __name__ == '__main__':
#     # Baris ini HANYA untuk testing lokal, JANGAN aktifkan di Vercel/Render
#     app.run(debug=True, host='0.0.0.0', port=5000)

