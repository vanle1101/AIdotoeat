import time
import random
import requests
from datetime import datetime

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
]

APPS = [
    'json-schema-seo-studio.html',
    'seo-opengraph-meta-generator.html',
    'vietqr-crypto-payment-generator.html',
    'openai-tiktoken-cost-estimator.html',
    'crypto-arbitrage-spread-scanner.html',
    'defi-staking-yield-compounder.html',
    'password-hash-security-auditor.html',
    'papaparse-csv-to-json-cleaner.html',
    'css-glassmorphism-card-builder.html',
    'web3-airdrop-testnet-quest-tracker.html'
]

BASE_LOCAL = 'http://127.0.0.1:8888'

def run_traffic_cycle():
    print('[+] Starting AUTOProfit Autonomous Auto-Surf Worker...')
    session = requests.Session()
    cycle_count = 0

    while True:
        try:
            ua = random.choice(USER_AGENTS)
            headers = {'User-Agent': ua, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            
            # 1. Surf main autosurf page
            session.get(f'{BASE_LOCAL}/autosurf.html', headers=headers, timeout=10)
            
            # 2. Pick a random web app tool
            app_target = random.choice(APPS)
            app_url = f'{BASE_LOCAL}/apps/{app_target}'
            session.get(app_url, headers=headers, timeout=10)
            
            # 3. Simulate Ad unit impression request
            try:
                session.get('https://acceptable.a-ads.com/2460284/?size=Adaptive', headers={'Referer': app_url, 'User-Agent': ua}, timeout=8)
            except Exception:
                pass
                
            cycle_count += 1
            if cycle_count % 10 == 0:
                print(f'[+] Completed {cycle_count} autonomous surfing cycles.')

            # Sleep 12-18 seconds before next automated surf
            time.sleep(random.uniform(12, 18))
        except Exception:
            time.sleep(10)

if __name__ == '__main__':
    run_traffic_cycle()
