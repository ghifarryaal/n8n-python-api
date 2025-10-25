from flask import Flask, request, jsonify
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import traceback
import re

app = Flask(__name__)

# ============================================
# FUNGSI PENCARIAN BERITA DARI YFINANCE
# ============================================

def get_news_from_yfinance(ticker_symbol):
    """
    Mengambil berita dari Yahoo Finance untuk ticker tertentu
    """
    try:
        ticker = yf.Ticker(ticker_symbol)

        # Ambil info dasar
        info = ticker.info
        company_name = info.get('shortName', ticker_symbol)

        # Ambil berita
        news = ticker.news

        if not news:
            return [], company_name

        news_list = []
        for article in news[:10]:  # Ambil max 10 berita terbaru
            # Parse timestamp
            pub_time = datetime.fromtimestamp(article.get('providerPublishTime', 0))
            time_ago = get_time_ago(pub_time)

            news_item = {
                "title": article.get('title', 'No Title'),
                "publisher": article.get('publisher', 'Unknown'),
                "link": article.get('link', ''),
                "published_time": pub_time.strftime('%Y-%m-%d %H:%M:%S'),
                "time_ago": time_ago,
                "type": article.get('type', 'STORY'),
                "thumbnail": article.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', '') if article.get('thumbnail') else ''
            }
            news_list.append(news_item)

        return news_list, company_name

    except Exception as e:
        print(f"Error fetching news from yfinance: {e}")
        return [], None

def get_time_ago(pub_time):
    """
    Menghitung berapa lama artikel dipublikasikan
    """
    now = datetime.now()
    diff = now - pub_time

    if diff.days > 0:
        if diff.days == 1:
            return "1 hari yang lalu"
        else:
            return f"{diff.days} hari yang lalu"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"{hours} jam yang lalu"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"{minutes} menit yang lalu"
    else:
        return "Baru saja"

# ============================================
# FUNGSI PENCARIAN BERITA DARI GOOGLE NEWS
# ============================================

def search_google_news(company_name, max_results=10):
    """
    Mencari berita dari Google News (scraping sederhana)
    """
    try:
        # Format query untuk pencarian
        query = f"{company_name} saham Indonesia"
        query_encoded = query.replace(' ', '+')

        # URL Google News
        url = f"https://news.google.com/search?q={query_encoded}&hl=id&gl=ID&ceid=ID:id"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.content, 'html.parser')

        # Parse artikel berita
        news_list = []
        articles = soup.find_all('article', limit=max_results)

        for article in articles:
            try:
                # Ambil judul
                title_elem = article.find('a', class_='JtKRv')
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                link = "https://news.google.com" + title_elem['href'][1:]  # Remove leading '.'

                # Ambil sumber
                source_elem = article.find('div', class_='vr1PYe')
                source = source_elem.text.strip() if source_elem else "Unknown"

                # Ambil waktu
                time_elem = article.find('time')
                time_ago = time_elem.text.strip() if time_elem else "Unknown"

                news_item = {
                    "title": title,
                    "publisher": source,
                    "link": link,
                    "time_ago": time_ago,
                    "source": "Google News"
                }

                news_list.append(news_item)

            except Exception as e:
                continue

        return news_list

    except Exception as e:
        print(f"Error scraping Google News: {e}")
        return []

# ============================================
# FUNGSI ANALISIS SENTIMEN BERITA (SEDERHANA)
# ============================================

def analyze_sentiment(news_list):
    """
    Analisis sentimen sederhana berdasarkan keyword dalam judul
    """
    positive_keywords = [
        'naik', 'untung', 'profit', 'meningkat', 'tumbuh', 'ekspansi', 
        'positif', 'optimis', 'rekomendasi', 'buy', 'bagus', 'kuat',
        'catat', 'raih', 'mencapai', 'tertinggi', 'recovery', 'rebound'
    ]

    negative_keywords = [
        'turun', 'rugi', 'merosot', 'anjlok', 'koreksi', 'tertekan',
        'negatif', 'pesimis', 'sell', 'lemah', 'buruk', 'krisis',
        'terendah', 'penurunan', 'susut', 'minus', 'melemah'
    ]

    neutral_keywords = [
        'stabil', 'tetap', 'konsolidasi', 'sideways', 'hold', 'tunggu'
    ]

    sentiments = {
        'positive': 0,
        'negative': 0,
        'neutral': 0
    }

    news_with_sentiment = []

    for news in news_list:
        title_lower = news['title'].lower()

        # Hitung score
        pos_score = sum(1 for keyword in positive_keywords if keyword in title_lower)
        neg_score = sum(1 for keyword in negative_keywords if keyword in title_lower)
        neu_score = sum(1 for keyword in neutral_keywords if keyword in title_lower)

        # Tentukan sentiment
        if pos_score > neg_score and pos_score > neu_score:
            sentiment = 'positive'
            emoji = '🟢'
        elif neg_score > pos_score and neg_score > neu_score:
            sentiment = 'negative'
            emoji = '🔴'
        else:
            sentiment = 'neutral'
            emoji = '🟡'

        sentiments[sentiment] += 1

        news_copy = news.copy()
        news_copy['sentiment'] = sentiment
        news_copy['sentiment_emoji'] = emoji
        news_with_sentiment.append(news_copy)

    # Hitung sentiment score keseluruhan
    total = len(news_list)
    if total > 0:
        sentiment_score = {
            'positive_percent': round((sentiments['positive'] / total) * 100, 1),
            'negative_percent': round((sentiments['negative'] / total) * 100, 1),
            'neutral_percent': round((sentiments['neutral'] / total) * 100, 1),
            'overall': 'POSITIF' if sentiments['positive'] > sentiments['negative'] else 'NEGATIF' if sentiments['negative'] > sentiments['positive'] else 'NETRAL'
        }
    else:
        sentiment_score = {
            'positive_percent': 0,
            'negative_percent': 0,
            'neutral_percent': 0,
            'overall': 'NETRAL'
        }

    return news_with_sentiment, sentiment_score

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/news/emiten', methods=['POST'])
def get_emiten_news():
    """
    Endpoint untuk mendapatkan berita emiten
    Body JSON:
    {
        "ticker": "BBCA",
        "include_google": true,
        "max_results": 10
    }
    """
    try:
        data = request.get_json()

        if not data or 'ticker' not in data:
            return jsonify({
                "status": "error",
                "message": "Mohon kirim {'ticker': 'KODE_SAHAM'} dalam body JSON."
            }), 400

        ticker_input = data['ticker'].upper()
        ticker_symbol = ticker_input + ".JK"
        include_google = data.get('include_google', True)
        max_results = data.get('max_results', 10)

        # Ambil berita dari Yahoo Finance
        yf_news, company_name = get_news_from_yfinance(ticker_symbol)

        if not company_name:
            return jsonify({
                "status": "error",
                "message": f"Ticker {ticker_input} tidak ditemukan"
            }), 404

        all_news = yf_news.copy()

        # Tambahkan berita dari Google News jika diminta
        if include_google and company_name:
            google_news = search_google_news(company_name, max_results)
            all_news.extend(google_news)

        # Analisis sentiment
        news_with_sentiment, sentiment_summary = analyze_sentiment(all_news)

        # Sort berdasarkan waktu (terbaru dulu)
        news_with_sentiment.sort(key=lambda x: x.get('published_time', ''), reverse=True)

        result = {
            "ticker": ticker_input,
            "company_name": company_name,
            "total_news": len(news_with_sentiment),
            "sources": {
                "yahoo_finance": len(yf_news),
                "google_news": len(all_news) - len(yf_news)
            },
            "sentiment_analysis": sentiment_summary,
            "news": news_with_sentiment[:max_results],
            "timestamp": datetime.now().isoformat()
        }

        return jsonify({
            "status": "success",
            "data": result
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/news/multiple', methods=['POST'])
def get_multiple_news():
    """
    Endpoint untuk mendapatkan berita dari multiple emiten
    Body JSON:
    {
        "tickers": ["BBCA", "BBRI", "TLKM"],
        "max_results_per_ticker": 5
    }
    """
    try:
        data = request.get_json()

        if not data or 'tickers' not in data:
            return jsonify({
                "status": "error",
                "message": "Mohon kirim {'tickers': ['KODE1', 'KODE2', ...]} dalam body JSON."
            }), 400

        tickers = data['tickers']
        max_results = data.get('max_results_per_ticker', 5)

        if not isinstance(tickers, list) or len(tickers) == 0:
            return jsonify({
                "status": "error",
                "message": "tickers harus berupa array dan tidak boleh kosong"
            }), 400

        results = []

        for ticker in tickers:
            ticker_symbol = ticker.upper() + ".JK"
            yf_news, company_name = get_news_from_yfinance(ticker_symbol)

            if company_name and yf_news:
                news_with_sentiment, sentiment_summary = analyze_sentiment(yf_news[:max_results])

                results.append({
                    "ticker": ticker.upper(),
                    "company_name": company_name,
                    "news_count": len(news_with_sentiment),
                    "sentiment": sentiment_summary,
                    "latest_news": news_with_sentiment
                })

        return jsonify({
            "status": "success",
            "data": {
                "tickers_processed": len(results),
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/api/news/sentiment-summary', methods=['POST'])
def sentiment_summary():
    """
    Endpoint untuk mendapatkan ringkasan sentiment berita emiten
    Body JSON:
    {
        "ticker": "BBCA"
    }
    """
    try:
        data = request.get_json()

        if not data or 'ticker' not in data:
            return jsonify({
                "status": "error",
                "message": "Mohon kirim {'ticker': 'KODE_SAHAM'} dalam body JSON."
            }), 400

        ticker_input = data['ticker'].upper()
        ticker_symbol = ticker_input + ".JK"

        # Ambil berita
        yf_news, company_name = get_news_from_yfinance(ticker_symbol)

        if not company_name:
            return jsonify({
                "status": "error",
                "message": f"Ticker {ticker_input} tidak ditemukan"
            }), 404

        # Analisis sentiment
        news_with_sentiment, sentiment_summary = analyze_sentiment(yf_news)

        # Ekstrak judul berita untuk setiap kategori
        positive_headlines = [n['title'] for n in news_with_sentiment if n['sentiment'] == 'positive'][:3]
        negative_headlines = [n['title'] for n in news_with_sentiment if n['sentiment'] == 'negative'][:3]

        result = {
            "ticker": ticker_input,
            "company_name": company_name,
            "sentiment_score": sentiment_summary,
            "sample_headlines": {
                "positive": positive_headlines,
                "negative": negative_headlines
            },
            "recommendation": generate_news_recommendation(sentiment_summary),
            "timestamp": datetime.now().isoformat()
        }

        return jsonify({
            "status": "success",
            "data": result
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

def generate_news_recommendation(sentiment_summary):
    """
    Generate rekomendasi berdasarkan sentiment berita
    """
    overall = sentiment_summary['overall']
    pos_pct = sentiment_summary['positive_percent']
    neg_pct = sentiment_summary['negative_percent']

    if overall == 'POSITIF' and pos_pct >= 60:
        return {
            "signal": "BUY",
            "description": "Sentimen berita sangat positif. Momentum bullish dari sisi berita.",
            "confidence": "HIGH"
        }
    elif overall == 'POSITIF' and pos_pct >= 40:
        return {
            "signal": "ACCUMULATE",
            "description": "Sentimen berita cukup positif. Suitable untuk akumulasi bertahap.",
            "confidence": "MEDIUM"
        }
    elif overall == 'NEGATIF' and neg_pct >= 60:
        return {
            "signal": "SELL/AVOID",
            "description": "Sentimen berita sangat negatif. Hindari atau exit position.",
            "confidence": "HIGH"
        }
    elif overall == 'NEGATIF' and neg_pct >= 40:
        return {
            "signal": "HOLD/WAIT",
            "description": "Sentimen berita negatif. Tunggu perkembangan lebih lanjut.",
            "confidence": "MEDIUM"
        }
    else:
        return {
            "signal": "HOLD",
            "description": "Sentimen berita netral. Pertahankan posisi atau tunggu sinyal lebih jelas.",
            "confidence": "LOW"
        }

@app.route('/', methods=['GET'])
def home():
    """Homepage dengan dokumentasi API"""
    return jsonify({
        "status": "active",
        "service": "Emiten News Search & Sentiment Analysis API",
        "version": "1.0",
        "endpoints": {
            "POST /api/news/emiten": "Mendapatkan berita dan sentiment analysis untuk satu emiten",
            "POST /api/news/multiple": "Mendapatkan berita dari multiple emiten sekaligus",
            "POST /api/news/sentiment-summary": "Mendapatkan ringkasan sentiment dan rekomendasi"
        },
        "example_request": {
            "single_emiten": {
                "url": "/api/news/emiten",
                "body": {
                    "ticker": "BBCA",
                    "include_google": True,
                    "max_results": 10
                }
            },
            "multiple_emiten": {
                "url": "/api/news/multiple",
                "body": {
                    "tickers": ["BBCA", "BBRI", "TLKM"],
                    "max_results_per_ticker": 5
                }
            }
        },
        "features": [
            "News from Yahoo Finance",
            "Optional Google News integration",
            "Sentiment analysis (Positive/Negative/Neutral)",
            "Investment signal recommendation",
            "Multi-emiten support"
        ]
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
