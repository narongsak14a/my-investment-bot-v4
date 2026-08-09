import os
import requests
import feedparser
from google import genai
from tradingview_ta import TA_Handler, Interval

# ==========================================
# 1. ตั้งค่า API Key & Cloudflare Endpoint
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL")
CLOUDFLARE_AUTH_TOKEN = os.environ.get("CLOUDFLARE_AUTH_TOKEN")

# รายชื่อสินทรัพย์ ดัชนีอ้างอิง และกองทุนเป้าหมาย
ASSETS = [
    {"name": "ทองคำโลก (Gold)", "symbol": "XAUUSD", "exchange": "OANDA", "screener": "cfd"},
    {"name": "ทองคำไทย (Gold TH)", "symbol": "GOLD", "exchange": "TVC", "screener": "cfd"},
    {"name": "Tesla (TSLA)", "symbol": "TSLA", "exchange": "NASDAQ", "screener": "america"},
    {"name": "Nvidia (NVDA)", "symbol": "NVDA", "exchange": "NASDAQ", "screener": "america"},
    {"name": "ดัชนีหุ้นไทย (SET Index)", "symbol": "SET", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น DEMCO (DEMCO)", "symbol": "DEMCO", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น ASP (ASP)", "symbol": "ASP", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น KGI (KGI)", "symbol": "KGI", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น TISCO (TISCO)", "symbol": "TISCO", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น KTB (KTB)", "symbol": "KTB", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น SCB (SCB)", "symbol": "SCB", "exchange": "SET", "screener": "thailand"},
    {"name": "KTB RMF4 (อ้างอิงดัชนี SET)", "symbol": "SET", "exchange": "SET", "screener": "thailand"},
    {"name": "KTB RMF1 Benchmark (Bond Yield 10Y)", "symbol": "US10Y", "exchange": "TVC", "screener": "bond"},
    {"name": "Bitcoin (BTC/USD)", "symbol": "BTCUSD", "exchange": "BINANCE", "screener": "crypto"}
]

# ==========================================
# 2. ฟังก์ชันดึงข้อมูลเชิงลึก
# ==========================================
def fetch_all_tradingview_signals():
    print("⏳ กำลังดึงสัญญาณเทคนิคคอลเชิงลึกจาก TradingView...")
    tv_summary_report = ""
    for asset in ASSETS:
        try:
            handler = TA_Handler(
                symbol=asset["symbol"],
                exchange=asset["exchange"],
                screener=asset["screener"],
                interval=Interval.INTERVAL_1_DAY
            )
            analysis = handler.get_analysis()
            rec = analysis.summary.get('RECOMMENDATION', 'N/A')
            buy = analysis.summary.get('BUY', 0)
            sell = analysis.summary.get('SELL', 0)
            neutral = analysis.summary.get('NEUTRAL', 0)
            
            tv_summary_report += (
                f"- {asset['name']}: สัญญาณสรุป [{rec}] "
                f"(แรงซื้อ: {buy}, แรงขาย: {sell}, ถือครอง: {neutral})\n"
            )
        except Exception as e:
            tv_summary_report += f"- {asset['name']}: ดึงข้อมูลไม่สำเร็จ ({e})\n"
    return tv_summary_report

def fetch_rss_news():
    print("⏳ กำลังเชื่อมต่อดึงข้อมูลข่าวสารการเงินโลกและเนื้อหาโดยละเอียด...")
    feed_url = "https://finance.yahoo.com/news/rssindex"
    feed = feedparser.parse(feed_url)
    news_compiled = ""
    if feed.entries:
        for entry in feed.entries[:5]:
            # ดึงเนื้อหาย่อ (Summary) เพื่อเพิ่มความน่าเชื่อถือในการวิเคราะห์
            summary = getattr(entry, 'summary', '')
            clean_summary = summary.split('<')[0][:180] if summary else 'ไม่มีรายละเอียดสรุป'
            news_compiled += f"• หัวข้อข่าว: {entry.title}\n  รายละเอียด: {clean_summary}...\n"
    else:
        news_compiled = "• ไม่สามารถดึงข่าวสารได้ในขณะนี้\n"
    return news_compiled

def send_to_cloudflare(message_text):
    print("⏳ กำลังส่งข้อมูลไปยัง Cloudflare...")
    if not CLOUDFLARE_WORKER_URL:
        print("❌ ไม่พบ CLOUDFLARE_WORKER_URL ใน GitHub Secrets")
        return

    headers = {"Content-Type": "application/json"}
    if CLOUDFLARE_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {CLOUDFLARE_AUTH_TOKEN.strip()}"

    payload = {
        "email": "narongsak14@gmail.com",
        "report_type": "CIO_DAILY_REPORT",
        "content": message_text
    }

    try:
        response = requests.post(CLOUDFLARE_WORKER_URL, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            print("✅ ส่งรายงานไปยัง Cloudflare เรียบร้อยแล้ว!")
        else:
            print(f"❌ ส่งเข้า Cloudflare ไม่สำเร็จ (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการส่งไปยัง Cloudflare: {e}")

# ==========================================
# 3. ฟังก์ชันประมวลผล Gemini AI และสั่งรัน
# ==========================================
def run_investment_ai_pipeline():
    print("\n--- 🚀 เริ่มต้นกระบวนการวิเคราะห์การลงทุนระดับมืออาชีพ ---")
    raw_news_data = fetch_rss_news()
    tradingview_signals = fetch_all_tradingview_signals()

    macro_tech_prompt = f"""
คุณคือ 'ประธานคณะกรรมการฝ่ายวิจัยและจัดการกองทุน (Chief Investment Officer - CIO)' 
หน้าที่ของคุณคือวิเคราะห์ความเชื่อมโยงระดับสถาบันระหว่าง 'กระแสข่าวเศรษฐกิจมหภาค' และ 'สัญญาณกราฟเทคนิคอลสถิติเชิงลึก' ของสินทรัพย์และกองทุนเป้าหมาย เพื่อส่งต่อข้อมูลเชิงวิชาการให้วิเคราะห์เป็น Podcast ใน NotebookLM

[ชุดข้อมูลที่ 1: สัญญาณเทคนิคอลล่าสุดจาก TradingView]
----------------------------------------
{tradingview_signals}
----------------------------------------

[ชุดข้อมูลที่ 2: สภาพการณ์ข่าวสารและบริบทเศรษฐกิจโลกล่าสุด]
----------------------------------------
{raw_news_data}
----------------------------------------

จงประมวลผลอย่างเป็นระบบและเขียน 'รายงานสรุปกลยุทธ์ฟิวชันข้ามมิติ' เป็นภาษาไทย โดยแยกประเด็นออกเป็น 4 ส่วนดังนี้:

[PART 1: การตรวจสุขภาพสินทรัพย์และกองทุน (Asset & Fund Health Check)]
- วิเคราะห์สถานะแยกตามกลุ่ม: ทองคำ, หุ้นเทคโนโลยีต่างประเทศ (TSLA, NVDA), กลุ่มหุ้นการเงินและธนาคารไทย (ASP, KGI, TISCO, KTB, SCB, DEMCO), สินทรัพย์ดิจิทัล (BTC)
- **วิเคราะห์เจาะจงกองทุน KTB RMF:**
  1) **KTB RMF4 (หุ้นไทย):** ประเมินจากสัญญาณดัชนี SET ว่าอยู่ในโหมดน่าสะสม/พักการลงทุน
  2) **KTB RMF1 (ตราสารหนี้/พักเงิน):** ประเมินความเสี่ยงและอัตราผลตอบแทนผ่าน Benchmark ทิศทาง Bond Yield ว่าควรใช้เป็นที่หลบภัยหรือไม่

[PART 2: บทวิเคราะห์ความสอดคล้อง (Macro-Technical Linkage)]
- วิเคราะห์เปรียบเทียบว่าข้อมูลข่าวสารเศรษฐกิจโลก สอดคล้องหรือขัดแย้งกับสัญญาณเทคนิคอลจริงในตลาดอย่างไร (เช่น เหตุใดกราฟเทคนิคอลจึงสั่งซื้อ/ขายสวนทางกับข่าวสาร)

[PART 3: คำแนะนำการจัดพอร์ตเชิงกลยุทธ์ (Action Plan & Switching Strategy)]
- ฟันธงแนวทางการปรับน้ำหนักพอร์ตประจำวัน
- ระบุสัดส่วนการ DCA หรือการสับเปลี่ยนกองทุน (Switching) ระหว่าง **KTB RMF4 (หุ้นไทย)** และ **KTB RMF1 (ตราสารหนี้)** อย่างชัดเจนและมีเหตุผลประกอบ

[PART 4: สคริปต์รวบยอดสำหรับสร้าง Podcast ใน NotebookLM]
- แปลงบทวิเคราะห์ให้กลายเป็น 'สคริปต์บทพูดสั้น เร้าใจ และเป็นทางการ' (ความยาว 3-4 ย่อหน้า) ภาษาไทย เพื่อป้อนให้ระบบ NotebookLM สร้างเสียง Podcast ประจำวัน

เขียนรายงานด้วยน้ำเสียงสถาบันการเงิน เฉียบคม ตรงไปตรงมา กระชับ และไม่มีคำเกริ่นนำที่ไม่จำเป็น
"""
    print("\n🧠 กำลังส่งข้อมูลฟิวชันป้อนเข้า Gemini...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # เรียกใช้ Gemini 2.5 Flash รุ่นมาตรฐาน
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=macro_tech_prompt
        )
        report_text = response.text
        print("\n--- ✨ รายงานจาก Gemini ---")
        print(report_text)

        print("\n📤 กำลังส่งรายงานไปยัง Cloudflare...")
        
        # ดึงชื่อ Repository มาแสดงใน Header
        repo_name = os.environ.get("GITHUB_REPOSITORY", "narongsak14a/my-investment-bot-v4")
        
        header = (
            f"📦 Repository: {repo_name}\n"
            f"📊 [รายงานสรุปกลยุทธ์การลงทุน CIO Report (วิเคราะห์พอร์ต KTB RMF)]\n"
            f"--------------------------------------------------\n\n"
        )

        send_to_cloudflare(header + report_text)

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในระบบ AI: {e}")

# เรียกใช้งานโปรแกรม
if __name__ == "__main__":
    run_investment_ai_pipeline()
import os
import requests
import feedparser
from google import genai
from tradingview_ta import TA_Handler, Interval

# ==========================================
# 1. ตั้งค่า API Key & Cloudflare Endpoint
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL")
CLOUDFLARE_AUTH_TOKEN = os.environ.get("CLOUDFLARE_AUTH_TOKEN")

# รายชื่อสินทรัพย์ ดัชนีอ้างอิง และกองทุนเป้าหมาย
ASSETS = [
    {"name": "ทองคำโลก (Gold)", "symbol": "XAUUSD", "exchange": "OANDA", "screener": "cfd"},
    {"name": "ทองคำไทย (Gold TH)", "symbol": "GOLD", "exchange": "TVC", "screener": "cfd"},
    {"name": "Tesla (TSLA)", "symbol": "TSLA", "exchange": "NASDAQ", "screener": "america"},
    {"name": "Nvidia (NVDA)", "symbol": "NVDA", "exchange": "NASDAQ", "screener": "america"},
    {"name": "ดัชนีหุ้นไทย (SET Index)", "symbol": "SET", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น DEMCO (DEMCO)", "symbol": "DEMCO", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น ASP (ASP)", "symbol": "ASP", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น KGI (KGI)", "symbol": "KGI", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น TISCO (TISCO)", "symbol": "TISCO", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น KTB (KTB)", "symbol": "KTB", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น SCB (SCB)", "symbol": "SCB", "exchange": "SET", "screener": "thailand"},
    {"name": "KTB RMF4 (อ้างอิงดัชนี SET)", "symbol": "SET", "exchange": "SET", "screener": "thailand"},
    {"name": "KTB RMF1 Benchmark (Bond Yield 10Y)", "symbol": "US10Y", "exchange": "TVC", "screener": "bond"},
    {"name": "Bitcoin (BTC/USD)", "symbol": "BTCUSD", "exchange": "BINANCE", "screener": "crypto"}
]

# ==========================================
# 2. ฟังก์ชันดึงข้อมูลเชิงลึก
# ==========================================
def fetch_all_tradingview_signals():
    print("⏳ กำลังดึงสัญญาณเทคนิคคอลเชิงลึกจาก TradingView...")
    tv_summary_report = ""
    for asset in ASSETS:
        try:
            handler = TA_Handler(
                symbol=asset["symbol"],
                exchange=asset["exchange"],
                screener=asset["screener"],
                interval=Interval.INTERVAL_1_DAY
            )
            analysis = handler.get_analysis()
            rec = analysis.summary.get('RECOMMENDATION', 'N/A')
            buy = analysis.summary.get('BUY', 0)
            sell = analysis.summary.get('SELL', 0)
            neutral = analysis.summary.get('NEUTRAL', 0)
            
            tv_summary_report += (
                f"- {asset['name']}: สัญญาณสรุป [{rec}] "
                f"(แรงซื้อ: {buy}, แรงขาย: {sell}, ถือครอง: {neutral})\n"
            )
        except Exception as e:
            tv_summary_report += f"- {asset['name']}: ดึงข้อมูลไม่สำเร็จ ({e})\n"
    return tv_summary_report

def fetch_rss_news():
    print("⏳ กำลังเชื่อมต่อดึงข้อมูลข่าวสารการเงินโลกและตลาดไทย...")
    # รวม RSS Feed ทั้งโลกและไทยเพื่อเพิ่มมิติความน่าเชื่อถือ
    feed_urls = [
        "https://finance.yahoo.com/news/rssindex",
        "https://www.thunhoon.com/feed"
    ]
    news_compiled = ""
    
    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for entry in feed.entries[:3]:
                    summary = getattr(entry, 'summary', '')
                    clean_summary = summary.split('<')[0][:150] if summary else 'ไม่มีรายละเอียดสรุป'
                    news_compiled += f"• หัวข้อข่าว: {entry.title}\n  รายละเอียด: {clean_summary}...\n"
        except Exception:
            continue

    if not news_compiled:
        news_compiled = "• ไม่สามารถดึงข่าวสารได้ในขณะนี้\n"
        
    return news_compiled

def send_to_cloudflare(message_text):
    print("⏳ กำลังส่งข้อมูลไปยัง Cloudflare...")
    if not CLOUDFLARE_WORKER_URL:
        print("❌ ไม่พบ CLOUDFLARE_WORKER_URL ใน GitHub Secrets")
        return

    headers = {"Content-Type": "application/json"}
    if CLOUDFLARE_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {CLOUDFLARE_AUTH_TOKEN.strip()}"

    payload = {
        "email": "narongsak14@gmail.com",
        "report_type": "CIO_DAILY_REPORT",
        "content": message_text
    }

    try:
        response = requests.post(CLOUDFLARE_WORKER_URL, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            print("✅ ส่งรายงานไปยัง Cloudflare เรียบร้อยแล้ว!")
        else:
            print(f"❌ ส่งเข้า Cloudflare ไม่สำเร็จ (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการส่งไปยัง Cloudflare: {e}")

# ==========================================
# 3. ฟังก์ชันประมวลผล Gemini AI และสั่งรัน
# ==========================================
def run_investment_ai_pipeline():
    print("\n--- 🚀 เริ่มต้นกระบวนการวิเคราะห์การลงทุนระดับมืออาชีพ ---")
    raw_news_data = fetch_rss_news()
    tradingview_signals = fetch_all_tradingview_signals()

    macro_tech_prompt = f"""
คุณคือ 'ประธานคณะกรรมการฝ่ายวิจัยและจัดการกองทุน (Chief Investment Officer - CIO)' 
หน้าที่ของคุณคือวิเคราะห์ความเชื่อมโยงระดับสถาบันระหว่าง 'กระแสข่าวเศรษฐกิจมหภาค' และ 'สัญญาณกราฟเทคนิคอลสถิติเชิงลึก' ของสินทรัพย์และกองทุนเป้าหมาย เพื่อส่งต่อข้อมูลเชิงวิชาการให้วิเคราะห์เป็น Podcast ใน NotebookLM

[ชุดข้อมูลที่ 1: สัญญาณเทคนิคอลล่าสุดจาก TradingView]
----------------------------------------
{tradingview_signals}
----------------------------------------

[ชุดข้อมูลที่ 2: สภาพการณ์ข่าวสารและบริบทเศรษฐกิจโลกล่าสุด]
----------------------------------------
{raw_news_data}
----------------------------------------

จงประมวลผลอย่างเป็นระบบและเขียน 'รายงานสรุปกลยุทธ์ฟิวชันข้ามมิติ' เป็นภาษาไทย โดยแยกประเด็นออกเป็น 4 ส่วนดังนี้:

[PART 1: การตรวจสุขภาพสินทรัพย์และกองทุน (Asset & Fund Health Check)]
- วิเคราะห์สถานะแยกตามกลุ่ม: ทองคำ, หุ้นเทคโนโลยีต่างประเทศ (TSLA, NVDA), กลุ่มหุ้นการเงินและธนาคารไทย (ASP, KGI, TISCO, KTB, SCB, DEMCO), สินทรัพย์ดิจิทัล (BTC)
- **วิเคราะห์เจาะจงกองทุน KTB RMF:**
  1) **KTB RMF4 (หุ้นไทย):** ประเมินจากสัญญาณดัชนี SET ว่าอยู่ในโหมดน่าสะสม/พักการลงทุน
  2) **KTB RMF1 (ตราสารหนี้/พักเงิน):** ประเมินความเสี่ยงและอัตราผลตอบแทนผ่าน Benchmark ทิศทาง Bond Yield ว่าควรใช้เป็นที่หลบภัยหรือไม่

[PART 2: บทวิเคราะห์ความสอดคล้อง (Macro-Technical Linkage)]
- วิเคราะห์เปรียบเทียบว่าข้อมูลข่าวสารเศรษฐกิจโลก สอดคล้องหรือขัดแย้งกับสัญญาณเทคนิคอลจริงในตลาดอย่างไร (เช่น เหตุใดกราฟเทคนิคอลจึงสั่งซื้อ/ขายสวนทางกับข่าวสาร)

[PART 3: คำแนะนำการจัดพอร์ตเชิงกลยุทธ์ (Action Plan & Switching Strategy)]
- ฟันธงแนวทางการปรับน้ำหนักพอร์ตประจำวัน
- ระบุสัดส่วนการ DCA หรือการสับเปลี่ยนกองทุน (Switching) ระหว่าง **KTB RMF4 (หุ้นไทย)** และ **KTB RMF1 (ตราสารหนี้)** อย่างชัดเจนและมีเหตุผลประกอบ

[PART 4: สคริปต์รวบยอดสำหรับสร้าง Podcast ใน NotebookLM]
- แปลงบทวิเคราะห์ให้กลายเป็น 'สคริปต์บทพูดสั้น เร้าใจ และเป็นทางการ' (ความยาว 3-4 ย่อหน้า) ภาษาไทย เพื่อป้อนให้ระบบ NotebookLM สร้างเสียง Podcast ประจำวัน

เขียนรายงานด้วยน้ำเสียงสถาบันการเงิน เฉียบคม ตรงไปตรงมา กระชับ และไม่มีคำเกริ่นนำที่ไม่จำเป็น
"""
    print("\n🧠 กำลังส่งข้อมูลฟิวชันป้อนเข้า Gemini...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # ใช้รุ่นมาตรฐาน gemini-2.0-flash
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=macro_tech_prompt
        )
        report_text = response.text
        print("\n--- ✨ รายงานจาก Gemini ---")
        print(report_text)

        print("\n📤 กำลังส่งรายงานไปยัง Cloudflare...")
        
        repo_name = os.environ.get("GITHUB_REPOSITORY", "narongsak14a/my-investment-bot-v4")
        
        header = (
            f"📦 Repository: {repo_name}\n"
            f"📊 [รายงานสรุปกลยุทธ์การลงทุน CIO Report (วิเคราะห์พอร์ต KTB RMF)]\n"
            f"--------------------------------------------------\n\n"
        )

        send_to_cloudflare(header + report_text)

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในระบบ AI: {e}")

if __name__ == "__main__":
    run_investment_ai_pipeline()
