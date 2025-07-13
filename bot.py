from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import requests
from bs4 import BeautifulSoup
import datetime
import matplotlib.pyplot as plt
import io
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB
mongo_client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = mongo_client["price_tracker"]
collection = db["price_history"]

# Flipkart
def get_flipkart_price(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    try:
        print(f"Fetching Flipkart URL: {url}")  # Debug log
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Response status code: {r.status_code}")  # Debug log
        
        if r.status_code != 200:
            print(f"Error: Received status code {r.status_code}")
            return None, None

        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Save HTML for debugging
        with open('flipkart_debug.html', 'w', encoding='utf-8') as f:
            f.write(r.text)
        
        # Debug print
        print("Searching for title and price elements...")
        
        # Try multiple possible class names for title with debug
        title_element = None
        title_classes = ["B_NuCI", "yhB1nd", "G6XhRU"]
        for class_name in title_classes:
            title_element = soup.find(["span", "h1"], class_=class_name)
            if title_element:
                print(f"Found title with class: {class_name}")
                break
                
        # Try multiple possible class names for price with debug
        price_element = None
        price_classes = ["_30jeq3 _16Jk6d", "_30jeq3", "dyC4hf"]
        for class_name in price_classes.split():
            price_element = soup.find(["div", "span"], class_=class_name)
            if price_element:
                print(f"Found price with class: {class_name}")
                break
        
        if title_element and price_element:
            title = title_element.text.strip()
            price = price_element.text.strip()
            print(f"Successfully fetched: Title='{title}', Price='{price}'")  # Debug log
            return title, price
        else:
            if not title_element:
                print("Title element not found")
            if not price_element:
                print("Price element not found")
            return None, None
            
    except requests.Timeout:
        print("Request timed out")
        return None, None
    except requests.RequestException as e:
        print(f"Request error: {e}")
        return None, None
    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {str(e)}")
        return None, None

# Amazon (Scraper-based)
def get_amazon_price(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Try multiple possible ways to find title
        title = None
        title_element = soup.find(id="productTitle")
        if title_element:
            title = title_element.get_text(strip=True)

        # Try multiple possible price elements
        price = None
        price_elements = [
            soup.find(id="priceblock_dealprice"),
            soup.find(id="priceblock_ourprice"),
            soup.find(id="priceblock_saleprice"),
            soup.find("span", class_="a-price-whole"),
            soup.find("span", class_="a-offscreen"),
            soup.select_one(".a-price .a-offscreen"),
            soup.select_one("#tp_price_block_total_price_ww .a-offscreen")
        ]
        
        for element in price_elements:
            if element:
                price = element.get_text(strip=True)
                if price:
                    # Ensure price starts with ₹
                    if not price.startswith('₹'):
                        price = '₹' + price.replace('₹', '')
                    print(f"Successfully fetched Amazon product: {title} - {price}")  # Debug log
                    return title, price
                    
        print(f"Could not find price for Amazon URL: {url}")  # Debug log
        return None, None
    except Exception as e:
        print(f"Error scraping Amazon: {e}")  # Debug log
        return None, None

# Myntra
def get_myntra_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        title = soup.find("h1", class_="pdp-title").text.strip()
        price = soup.find("strong", class_="pdp-price").text.strip()
        return title, price
    except:
        return None, None

# Ajio
def get_ajio_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        title = soup.find("h1", class_="prod-name").text.strip()
        price = soup.find("div", class_="price  ").find("span").text.strip()
        return title, price
    except:
        return None, None

# Croma
def get_croma_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        title = soup.find("h1", class_="pdp-title").text.strip()
        price = soup.find("span", class_="amount").text.strip()
        return title, f"₹{price}"
    except:
        return None, None

# Tata CLiQ
def get_tatacliq_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        title = soup.find("h1", class_="pdp-e-i-head").text.strip()
        price = soup.find("span", class_="pdp-price").text.strip()
        return title, price
    except:
        return None, None

# Nykaa
def get_nykaa_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    try:
        title = soup.find("h1", class_="css-1gc4x7i").text.strip()
        price = soup.find("span", class_="css-1jczs19").text.strip()
        return title, price
    except:
        return None, None

# Save to DB
def save_price(url, price):
    date = datetime.date.today().isoformat()
    collection.insert_one({"url": url, "price": price, "date": date})

# Fetch History
def get_price_history(url):
    records = collection.find({"url": url}).sort("date", pymongo.ASCENDING).limit(30)
    return [(rec["date"], rec["price"]) for rec in records]

# Compute Price Stats
def compute_stats(history):
    prices = [int(p.replace("₹", "").replace(",", "")) for _, p in history if p]
    if not prices:
        return None, None, None, None
    return min(prices), max(prices), round(sum(prices)/len(prices), 2), prices[-1]

# Plot Graph
def plot_graph(history):
    dates = [datetime.datetime.strptime(d, "%Y-%m-%d") for d, _ in history]
    prices = [int(p.replace("₹", "").replace(",", "")) for _, p in history]
    plt.figure(figsize=(8, 4))
    plt.plot(dates, prices, marker='o')
    plt.title("Price History (30 Days)")
    plt.xlabel("Date")
    plt.ylabel("Price (INR)")
    plt.grid(True)
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    return buf

# Telegram Handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text("👋 Send me a product link from Flipkart, Amazon, Myntra, Ajio, TataCliq, Nykaa or Croma.")

def handle_link(update: Update, context: CallbackContext):
    try:
        url = update.message.text.strip()
        
        # Basic URL validation
        if not url.startswith('http'):
            update.message.reply_text("❌ Please provide a valid URL starting with http:// or https://")
            return
            
        # Send a waiting message
        processing_msg = update.message.reply_text("🔍 Processing your request...")
        
        # Debug log
        print(f"\nProcessing URL: {url}")
        
        name, price = None, None
        
        try:
            if "flipkart.com" in url:
                print("Detected Flipkart URL")
                name, price = get_flipkart_price(url)
            elif "amazon.in" in url:
                print("Detected Amazon URL")
                name, price = get_amazon_price(url)
            elif "myntra.com" in url:
                print("Detected Myntra URL")
                name, price = get_myntra_price(url)
            elif "ajio.com" in url:
                print("Detected Ajio URL")
                name, price = get_ajio_price(url)
            elif "tatacliq.com" in url:
                print("Detected TataCliq URL")
                name, price = get_tatacliq_price(url)
            elif "nykaa.com" in url:
                print("Detected Nykaa URL")
                name, price = get_nykaa_price(url)
            elif "croma.com" in url:
                print("Detected Croma URL")
                name, price = get_croma_price(url)
            else:
                processing_msg.edit_text("❌ Only Flipkart, Amazon, Myntra, Ajio, TataCLiQ, Nykaa and Croma supported.")
                return

            print(f"Scraping result - Name: {name}, Price: {price}")  # Debug log

            if name and price:
                try:
                    # Store in database
                    print("Saving to database...")  # Debug log
                    save_price(url, price)
                    
                    # Get history
                    print("Fetching price history...")  # Debug log
                    history = get_price_history(url)
                    
                    # Calculate stats
                    print("Computing statistics...")  # Debug log
                    min_p, max_p, avg_p, current_p = compute_stats(history)
                    
                    # Format message
                    product_info = f"📦 *{name}*\n"
                    product_info += f"💰 Current Price: {price}\n"
                    
                    if min_p is not None and max_p is not None and avg_p is not None:
                        stats = f"\n📊 *Price Statistics:*\n"
                        stats += f"📉 Lowest: ₹{min_p:,}\n"
                        stats += f"📈 Highest: ₹{max_p:,}\n"
                        stats += f"📊 Average: ₹{avg_p:,}\n"
                        product_info += stats
                    
                    # Update message
                    processing_msg.edit_text(product_info, parse_mode='Markdown')
                    
                    # Generate and send graph
                    if len(history) > 1:
                        print("Generating price history graph...")  # Debug log
                        graph = plot_graph(history)
                        update.message.reply_photo(photo=graph)
                        
                        # Send detailed history
                        history_text = "*📅 Price History:*\n"
                        for date, p in history:
                            history_text += f"{date}: {p}\n"
                        update.message.reply_text(history_text, parse_mode='Markdown')
                except Exception as e:
                    print(f"Error in data processing: {e}")  # Debug log
                    processing_msg.edit_text("❌ Error processing product data. Please try again.")
            else:
                error_msg = ("❌ Couldn't fetch product info. This might be due to:\n"
                           "1. Invalid product URL\n"
                           "2. Product not available\n"
                           "3. Website layout changed\n\n"
                           "Please verify the URL and try again.")
                processing_msg.edit_text(error_msg)
                print("Failed to fetch product info")  # Debug log
        except Exception as e:
            print(f"Error in URL processing: {e}")  # Debug log
            processing_msg.edit_text(f"❌ Error processing URL: {str(e)}")
            
    except Exception as e:
        print(f"Critical error in handle_link: {e}")  # Debug log
        update.message.reply_text("❌ An unexpected error occurred. Please try again later.")

# Main
def main():
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_link))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()