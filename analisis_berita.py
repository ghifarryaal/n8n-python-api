import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_time_ago(pub_time):
    now = datetime.now()
    diff = now - pub_time
    if diff.days > 0:
        return f"{diff.days} hari lalu"
    elif diff.seconds >= 3600:
        return f"{diff.seconds // 3600} jam lalu"
    elif diff.seconds >= 60:
        return f"{diff.seconds // 60} menit lalu"
    else:
        return "baru saja"

def get_news_from_yfinance(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        company_name = info.get("shortName", ticker_symbol)
        news = ticker.news or []
        items = []
        for n in news[:10]:
            t = datetime.fromtimestamp(n.get("providerPublishTime", 0))
            items.append({
                "title": n.get("title"),
                "publisher": n.get("publisher"),
                "link": n.get("link"),
                "published_time": t.strftime("%Y-%m-%d %H:%M:%S"),
                "time_ago": get_time_ago(t),
            })
        return items, company_name, True
    except Exception as e:
        return [f"Error mengambil berita: {e}"], None, False


def get_news_from_google(company_name, limit=10):
    try:
        query = f"{company_name} saham Indonesia".replace(" ", "+")
        url = f"https://news.google.com/search?q={query}&hl=id&gl=ID&ceid=ID:id"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return []
        soup = BeautifulSoup(r.content, "html.parser")
        arts = soup.find_all("article", limit=limit)
        out = []
        for a in arts:
            try:
                t = a.find("a", class_="JtKRv")
                if not t: continue
                title = t.text.strip()
                link = "https://news.google.com" + t["href"][1:]
                src = a.find("div", class_="vr1PYe")
                source = src.text.strip() if src else "Unknown"
                out.append({"title": title, "publisher": source, "link": link})
            except:
                continue
        return out
    except Exception:
        return []


def analyze_sentiment(news_list):
    pos_kw = ["naik","untung","profit","bagus","positif","tumbuh","rebound"]
    neg_kw = ["turun","rugi","anjlok","negatif","koreksi","buruk","merosot"]
    summary = {"positive":0, "negative":0, "neutral":0}
    analyzed = []

    for n in news_list:
        t = n["title"].lower()
        pos = sum(1 for w in pos_kw if w in t)
        neg = sum(1 for w in neg_kw if w in t)
        if pos > neg:
            s, e = "positive", "🟢"
        elif neg > pos:
            s, e = "negative", "🔴"
        else:
            s, e = "neutral", "🟡"
        summary[s] += 1
        n["sentiment"] = s
        n["emoji"] = e
        analyzed.append(n)

    total = len(news_list) or 1
    percent = {
        "positive": round(summary["positive"]/total*100, 1),
        "negative": round(summary["negative"]/total*100, 1),
        "neutral": round(summary["neutral"]/total*100, 1),
    }
    percent["overall"] = "POSITIF" if percent["positive"]>percent["negative"] \
                         else "NEGATIF" if percent["negative"]>percent["positive"] \
                         else "NETRAL"
    return analyzed, percent


def get_sentiment_analysis(ticker_symbol):
    try:
        ynews, name, ok = get_news_from_yfinance(ticker_symbol)
        if not ok:
            return ynews, None, False

        google_news = get_news_from_google(name, 10)
        all_news = ynews + google_news
        analyzed, summary = analyze_sentiment(all_news)

        log = [
            f"Analisis sentimen untuk {name}:",
            f"🟢 Positif: {summary['positive']}%",
            f"🔴 Negatif: {summary['negative']}%",
            f"🟡 Netral: {summary['neutral']}%",
            f"Kesimpulan: {summary['overall']}"
        ]
        return log, {"company_name": name, "sentiment_summary": summary, "news": analyzed}, True
    except Exception as e:
        return [f"Error: {e}"], None, False
