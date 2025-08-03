import jwt
import hashlib
import os
import requests
import uuid
from urllib.parse import urlencode, unquote
import pandas as pd
from typing import Dict, List, Optional
import json


class UpbitIntegration:
    """업비트 API 통합 클래스"""
    
    def __init__(self):
        """환경변수에서 API 키 및 서버 URL 로드"""
        self.access_key = os.environ.get('UPBIT_OPEN_API_ACCESS_KEY')
        self.secret_key = os.environ.get('UPBIT_OPEN_API_SECRET_KEY')
        self.server_url = os.environ.get('UPBIT_OPEN_API_SERVER_URL')
        
        if not self.access_key or not self.secret_key:
            raise ValueError("업비트 API 키가 설정되지 않았습니다. 환경변수를 확인해주세요.")
    
    def _generate_headers(self, query_string: str = None) -> Dict[str, str]:
        """API 요청을 위한 인증 헤더 생성"""
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        
        if query_string:
            query_hash = hashlib.sha512(query_string.encode()).hexdigest()
            payload['query_hash'] = query_hash
            payload['query_hash_alg'] = 'SHA512'
        
        jwt_token = jwt.encode(payload, self.secret_key)
        authorization = f'Bearer {jwt_token}'
        
        return {
            'Authorization': authorization,
            'Content-Type': 'application/json'
        }
    
    def get_accounts(self) -> List[Dict]:
        """계좌 정보 조회"""
        try:
            headers = self._generate_headers()
            response = requests.get(f'{self.server_url}/v1/accounts', headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"계좌 정보 조회 실패: {e}")
            return []
    
    def get_deposit(self):
        accounts = self.get_accounts()
        
        for account in accounts:
            if account.get('currency') == 'KRW':
                ret =  {
                    "deposit": [
                        {
                            'name': '업비트 예수금',
                            'ticker': 'UPBIT_DEPOSIT',
                            'quantity': float(account.get('balance', 0)),
                            'avg_price': 0.0,  # KRW는 평균 매입가가 없으므로 0으로 설정
                            'currency': 'KRW'
                        }
                    ]
                }
        return {'UPBIT': ret}
    def _get_balance(self) -> Dict:
        """잔고 정보를 가공하여 반환"""
        accounts = self.get_accounts()
        if not accounts:
            return {}
        
        balance_data = {
            'crypto': []
        }
        
        for account in accounts:
            currency = account.get('currency', '')
            balance = float(account.get('balance', 0))
            locked = float(account.get('locked', 0))
            avg_buy_price = float(account.get('avg_buy_price', 0))
            if avg_buy_price == 0:
                continue
            if balance > 0 or locked > 0:  # 잔고가 있는 것만
                total_balance = balance + locked
                
                balance_data['crypto'].append({
                    'name': currency,
                    'ticker': currency,
                    'quantity': total_balance,
                    'avg_price': avg_buy_price,
                    'currency': 'KRW'
                })
        
        return {'UPBIT': balance_data}
    
    def get_ticker_price(self, market: str) -> Optional[float]:
        """특정 마켓의 현재가 조회"""
        try:
            url = f'{self.server_url}/v1/ticker'
            params = {'markets': market}
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data:
                return float(data[0].get('trade_price', 0))
            return None
        except requests.exceptions.RequestException as e:
            print(f"티커 가격 조회 실패 ({market}): {e}")
            return None
    
    def get_markets(self) -> List[Dict]:
        """마켓 코드 목록 조회"""
        try:
            response = requests.get(f'{self.server_url}/v1/market/all')
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"마켓 목록 조회 실패: {e}")
            return []
    
    def get_orderbook(self, markets: List[str]) -> List[Dict]:
        """호가 정보 조회"""
        try:
            markets_str = ','.join(markets)
            params = {'markets': markets_str}
            response = requests.get(f'{self.server_url}/v1/orderbook', params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"호가 정보 조회 실패: {e}")
            return []

    def get_balance(self):
        deposit = self.get_deposit()
        balance = self._get_balance()
        merged = {'UPBIT': {'crypto': balance['UPBIT'].get('crypto', []), 'deposit': deposit['UPBIT'].get('deposit', [])}}
        return merged

# 테스트 실행 (필요시)
if __name__ == "__main__":
    try:
        upbit = UpbitIntegration()
        deposit = upbit.get_deposit()
        balance = upbit.get_balance()
        merged = {'UPBIT': {'crypto': balance['UPBIT'].get('crypto', []), 'deposit': deposit['UPBIT'].get('deposit', [])}}
        print(merged)
        with open('private/upbit.json', 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"오류: {e}")