import aiohttp
import asyncio
import random
from faker import Faker
fake = Faker('en_IN')
muslim_names = {
    'first': ['Mohammed', 'Fatima', 'Yusuf', 'Aisha', 'Ahmed'],
    'last': ['Qureshi', 'Khan', 'Siddiqui', 'Hussain', 'Ali']
}
headers = {
    'Host': 'www.change.org',
    'content-type': 'application/json',
    'x-requested-with': 'corgi-front-end-browser:5.446.0',
    'user-agent': fake.user_agent(),
    'accept': 'application/json',
    'origin': 'https://www.change.org',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-mode': 'cors',
    'sec-fetch-dest': 'empty'
}
async def send_request(session, payload):
    async with session.post(
        'https://www.change.org/api-proxy/graphql/signPetition/490796050?op=SignatureSharedCreateSignature',
        json=payload, headers=headers
    ) as response:
        return await response.json()
async def main():
    async with aiohttp.ClientSession() as session:
        while True:  # Infinite loop for continuous requests
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
