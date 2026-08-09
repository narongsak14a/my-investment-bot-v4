import os
import requests
import feedparser
from google import genai
from tradingview_ta import TA_Handler, Interval

# ==========================================
# 1. ตั้งค่า API Key & Cloudflare Endpoint
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ดึง URL ของ Cloudflare Worker / Webhook จาก Environment Variables
CLOUDFLARE_WORKER_URL = os.environ.get("CLOUDFLARE_WORKER_URL")
# (Optional) หาก Cloudflare Worker มีการตั้งค่า Bearer Token ไว้เพื่อความปลอดภัย
CLOUDFLARE_AUTH_TOKEN = os.environ.get("CLOUDFLARE_AUTH_TOKEN")

# รายชื่อสินทรัพย์เป้าหมาย
ASSETS = [
    {"name": "ทองคำ (Gold)", "symbol": "XAUUSD", "exchange": "OANDA", "screener": "cfd"},
    {"name": "ทองคำไทย (Gold TH)", "symbol": "GOLD", "exchange": "TVC", "screener": "cfd"},
    {"name": "Tesla (TSLA)", "symbol": "TSLA", "exchange": "NASDAQ", "screener": "america"},
    {"name": "Nvidia (NVDA)", "symbol": "NVDA", "exchange": "NASDAQ", "screener": "america"},
    {"name": "ดัชนีหุ้นไทย (SET Index)", "symbol": "SET", "exchange": "SET", "screener": "thailand"},
    {"name": "หุ้น DEMCO (DEMCO)", "symbol": "DEMCO", "exchange": "SET", "screener": "thailand"},
    {"name": "Bitcoin (BTC/USD)", "symbol": "BTCUSD", "exchange": "BINANCE", "screener": "crypto"}
]

# ==========================================
# 2. ฟังก์ชันดึงข้อมูล TradingView, RSS & ส่ง Cloudflare
# ==========================================
def fetch_all_tradingview_signals():
    print("⏳ กำลังดึงสัญญาณเทคนิคคอลจาก TradingView...")
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
            tv_summary_report += f"- {asset['name']}: แนะนำ [{rec}] (ซื้อ: {buy}, ขาย: {sell})\n"
        except Exception as e:
            tv_summary_report += f"- {asset['name']}: ดึงข้อมูลไม่สำเร็จ ({e})\n"
    return tv_summary_report

def fetch_rss_news():
    print("⏳ กำลังเชื่อมต่อดึงข้อมูลข่าวสารการเงินโลก...")
    feed_url = "https://finance.yahoo.com/news/rssindex"
    feed = feedparser.parse(feed_url)
    news_compiled = ""
    if feed.entries:
        for entry in feed.entries[:5]:
            news_compiled += f"• ข่าวด่วน: {entry.title}\n"
    else:
        news_compiled = "• ไม่สามารถดึงข่าวสารได้ในขณะนี้\n"
    return news_compiled

def send_to_cloudflare(message_text):
    print("⏳ กำลังส่งข้อมูลไปยัง Cloudflare...")
    
    if not CLOUDFLARE_WORKER_URL:
        print("❌ ไม่พบ CLOUDFLARE_WORKER_URL ใน GitHub Secrets")
        return

    headers = {
        "Content-Type": "application/json"
    }
    
    if CLOUDFLARE_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {CLOUDFLARE_AUTH_TOKEN.strip()}"

    # Payload JSON สำหรับส่งต่อไปยัง Cloudflare
    payload = {
        "email": "narongsak14@gmail.com",
        "report_type": "CIO_DAILY_REPORT",
        "content": message_text
    }

    try:
        response = requests.post(CLOUDFLARE_WORKER_URL, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            print("✅ ส่งรายงานไปยัง Cloudflare เรียบร้อยแล้ว! สวัสดี สิงห์สะอาด")
            
            
        else:
            print(f"❌ ส่งเข้า Cloudflare ไม่สำเร็จ (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการส่งไปยัง Cloudflare: {e}")

# ==========================================
# 3. ฟังก์ชันประมวลผล Gemini และสั่งรัน
# ==========================================
def run_investment_ai_pipeline():
    print("\n--- 🚀 เริ่มต้นกระบวนการวิเคราะห์การลงทุน ---")
    raw_news_data = fetch_rss_news()
    tradingview_signals = fetch_all_tradingview_signals()

    macro_tech_prompt = f"""
คุณคือ 'ประธานคณะกรรมการฝ่ายวิจัยและจัดการกองทุน (Chief Investment Officer)'
หน้าที่ของคุณคือการวิเคราะห์และถกเถียงเชิงลึกระหว่าง 'กระแสข่าวเศรษฐกิจ' และ 'สัญญาณกราฟเทคนิคอลจาก TradingView' ของสินทรัพย์เป้าหมาย เพื่อจัดทำเอกสารส่งต่อให้ NotebookLM เจนเสียง Podcast

[ชุดข้อมูลที่ 1: สัญญาณเทคนิคอลล่าสุดจาก TradingView]
----------------------------------------
{tradingview_signals}
----------------------------------------

[ชุดข้อมูลที่ 2: สภาพการณ์ข่าวสารเศรษฐกิจล่าสุด]
----------------------------------------
{raw_news_data}
----------------------------------------

จงทำการประมวลผลและเขียน 'รายงานสรุปกลยุทธ์ฟิวชันข้ามมิติ' เป็นภาษาไทย โดยแยกประเด็นออกเป็น 4 ส่วนดังนี้:

[PART 1: การตรวจสุขภาพ 4 สินทรัพย์ (Asset Health Check)]
- สรุปภาพรวมและอารมณ์ตลาดของ ทองคำ, Tesla, Nvidia และหุ้นไทย ว่าตัวไหนอยู่ในโหมด 'แข็งแกร่ง/น่าสะสม' และตัวไหนกำลังเจอ 'สัญญาณอันตราย/เทขาย' ตามข้อมูลจาก TradingView

[PART 2: บทวิเคราะห์ความสอดคล้อง (Macro-Technical Linkage)]
- ตัวเลขและสัญญาณจาก TradingView มันมีความสอดคล้องหรือขัดแย้งกับกระแสข่าวเศรษฐกิจโลกอย่างไร? เช่น ข่าวร้ายแต่ทำไมสัญญาณทางเทคนิคอลของหุ้นบางตัวยังสั่งให้ซื้ออยู่?

[PART 3: คำแนะนำในการปรับหน้าตัก (Action Plan)]
- บอกแนวทางแบบฟันธงว่าประธานบริษัทควร 'เพิ่มน้ำหนักการลงทุน' หรือ 'ลดความเสี่ยงกระจายความเสี่ยง' ในสินทรัพย์กลุ่มใดมากที่สุดในวันนี้ เพราะอะไร

[PART 4: บทพูดสคริปต์แบบสั้นเร้าใจสำหรับส่งเข้า NotebookLM]
- แปลงเนื้อหาทั้งหมดให้กลายเป็น 'บทพูดคุยรวบยอด สั้นๆ กระชับ และน่าตื่นเต้น' เป็นภาษาไทย (ความยาว 3-4 ย่อหน้า) เพื่อใช้ส่งต่อเป็นไฟล์ข้อมูลต้นฉบับให้ระบบ NotebookLM แปลงเป็นเสียง Podcast ประจำวันของคุณ

เขียนรายงานด้วยน้ำเสียงเฉียบคม เป็นทางการ ตรงไปตรงมา กระชับ และไม่มีคำเกริ่นนำไร้สาระ
"""

    print("\n🧠 กำลังส่งข้อมูลฟิวชันป้อนเข้า Gemini...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=macro_tech_prompt
        )
        report_text = response.text
        print("\n--- ✨ รายงานจาก Gemini ---")
        print(report_text)

        print("\n📤 กำลังส่งรายงานไปยัง Cloudflare...")
        
        #--------------------------------------------------------------        
        repo_name = os.environ.get("GITHUB_REPOSITORY", "narongsak14a/my-investment-bot-v4")
        print(repo_name)
       
        #---------------------------------------------------------------  

        header = "📊 [รายงานสรุปกลยุทธ์การลงทุนประจำวัน CIO Report(ณรงค์ศักดิ์)]\n\n"
        send_to_cloudflare(header + report_text + repo_name)

    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในระบบ AI: {e}")

# เรียกใช้งานโปรแกรม
run_investment_ai_pipeline()
