#!/usr/bin/env python3
"""
Portfolio Scheduler
매일 아침 6시에 포트폴리오 데이터를 자동으로 DB에 저장하는 스케줄러
"""

import schedule
import time
import sys
import os
from datetime import datetime
import logging

# 현재 스크립트의 디렉토리를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 모듈 import
from db_manager import PortfolioDBManager
import data.kis_integration as kis_integration
import data.upbit_integration as upbit_integration
import data.dc_integration as dc_integration
from data import fetcher
import pandas as pd
import json

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('private/portfolio_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 자산 분류 로딩
def load_asset_classification():
    """자산 분류 설정 로딩"""
    asset_classification_file = "private/asset_classification.csv"
    default_asset_types = {
        'IEF': '채권',
        'SGOV': '채권', 
        'SHV': '채권',
        'BIL': '채권',
        'QQQ': 'ETF',
        'QQQM': 'ETF',
        'SCHD': 'ETF',
        '360750': 'ETF',
        '379800': 'ETF',
        '472170': 'ETF',
    }
    
    if os.path.exists(asset_classification_file):
        df = pd.read_csv(asset_classification_file)
        return dict(zip(df['ticker'], df['asset_type']))
    else:
        return default_asset_types.copy()

def process_portfolio_data(balance_data, asset_classification):
    """포트폴리오 데이터 처리 (5_🏦_Real_Portfolio.py와 동일한 로직)"""
    all_data = []
    
    for account_id, account_data in balance_data.items():
        # 주식 데이터 처리 (KIS)
        if 'stock' in account_data:
            for stock in account_data['stock']:
                custom_asset_type = asset_classification.get(stock['ticker'], '주식')
                
                all_data.append({
                    'account_id': account_id,
                    'name': stock['name'],
                    'ticker': stock['ticker'],
                    'quantity': stock['quantity'],
                    'avg_price': stock['avg_price'],
                    'currency': stock['currency'],
                    'asset_type': custom_asset_type,
                    'original_type': '주식',
                    'total_purchase': stock['quantity'] * stock['avg_price']
                })
        
        # 예수금 데이터 처리 (KIS)
        if 'deposit' in account_data:
            for deposit in account_data['deposit']:
                if deposit['currency'] == 'KRW':
                    asset_type = 'KRW'
                elif deposit['currency'] == 'USD':
                    asset_type = 'USD'
                else:
                    asset_type = '현금'
                
                all_data.append({
                    'account_id': account_id,
                    'name': deposit['name'],
                    'ticker': deposit['ticker'],
                    'quantity': deposit['quantity'],
                    'avg_price': deposit['avg_price'],
                    'currency': deposit['currency'],
                    'asset_type': asset_type,
                    'original_type': '현금',
                    'total_purchase': deposit['quantity'] * deposit['avg_price']
                })
        
        # 암호화폐 데이터 처리 (Upbit)
        if 'crypto' in account_data:
            for crypto in account_data['crypto']:
                if crypto['ticker'] == 'KRW':
                    custom_asset_type = 'KRW'
                else:
                    custom_asset_type = asset_classification.get(crypto['ticker'], '암호화폐')
                
                all_data.append({
                    'account_id': account_id,
                    'name': crypto['name'],
                    'ticker': crypto['ticker'],
                    'quantity': crypto['quantity'],
                    'avg_price': crypto['avg_price'],
                    'currency': crypto['currency'],
                    'asset_type': custom_asset_type,
                    'original_type': '암호화폐' if crypto['ticker'] != 'KRW' else '현금',
                    'total_purchase': crypto['quantity'] * crypto['avg_price']
                })
    
    return pd.DataFrame(all_data)

def get_current_prices_for_portfolio(tickers):
    """포트폴리오 종목들의 현재가 조회"""
    kr_tickers = [t for t in tickers if t.endswith('.KS') or len(t) == 6]
    gold_tickers = [t for t in tickers if t == 'M04020000']
    crypto_tickers = [t for t in tickers if t in ['BTC', 'ETH', 'XRP', 'ADA', 'DOT', 'SOL', 'AVAX', 'MATIC', 'ATOM', 'LINK', 'UNI', 'AAVE', 'COMP', 'MKR', 'YFI', 'SNX', 'CRV', 'BAL', 'REN', 'KNC']]
    us_tickers = [t for t in tickers if t not in kr_tickers and t not in ['PENSION_DEPOSIT', 'OVERSEA_DEPOSIT', 'OVERSEA_KRW_DEPOSIT'] and t not in gold_tickers and t not in crypto_tickers]

    prices = {}
    
    try:
        # 한국 주식
        new_kr_tickers = [t+".KS" for t in kr_tickers if len(t) == 6]
        if new_kr_tickers:
            kr_prices = fetcher.get_current_prices(new_kr_tickers)
            kr_prices = kr_prices.to_dict()
            kr_prices = {k[:-3] if k.endswith('.KS') else k: v for k, v in kr_prices.items()}
            prices.update(kr_prices)
        
        # 미국 주식
        if us_tickers:
            us_prices = fetcher.get_current_prices(us_tickers)
            prices.update(us_prices.to_dict())
        
        # 금
        if gold_tickers:
            # gold_prices = fetcher.get_stock_info_from_KIS('M04020000')
            prices['M04020000'] = 150000.0#float(gold_prices['stck_prpr'].iloc[0])
        
        # 암호화폐 (업비트 API 사용)
        if crypto_tickers:
            upbit = upbit_integration.UpbitIntegration()
            for crypto in crypto_tickers:
                if crypto != 'KRW':
                    market = f'KRW-{crypto}'
                    price = upbit.get_ticker_price(market)
                    if price:
                        prices[crypto] = price
                        
    except Exception as e:
        logger.error(f"가격 조회 실패: {e}")
        
    return prices

def save_daily_portfolio():
    """매일 포트폴리오 데이터를 DB에 저장하는 함수"""
    try:
        logger.info("일일 포트폴리오 저장 작업 시작")
        
        # 1. 포트폴리오 데이터 로딩
        kis = kis_integration.KISIntegration()
        upbit = upbit_integration.UpbitIntegration()
        dc = dc_integration.DCIntegration()
        
        # 계좌 데이터 가져오기
        balance = kis.get_balance()
        logger.info(f"KIS 계좌 데이터 로딩 완료: {len(balance)} 계좌")
        
        # 업비트 계좌 데이터
        upbit_balance = upbit.get_balance()
        if upbit_balance:
            balance.update(upbit_balance)
            logger.info("업비트 계좌 데이터 추가 완료")
        
        # 현대차 계좌 데이터
        dc_balance = dc.get_balance()
        if dc_balance:
            balance.update(dc_balance)
            logger.info("현대차 계좌 데이터 추가 완료")
        
        # 백업 저장
        backup_file = f"private/balance_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(balance, f, ensure_ascii=False, indent=2)
        
        # 2. 자산 분류 로딩 및 데이터 처리
        asset_classification = load_asset_classification()
        portfolio_df = process_portfolio_data(balance, asset_classification)
        
        if portfolio_df.empty:
            logger.warning("포트폴리오 데이터가 비어있습니다.")
            return
        
        logger.info(f"포트폴리오 데이터 처리 완료: {len(portfolio_df)} 자산")
        
        # 3. 환율 및 현재가 조회
        usd_krw_rate, _ = fetcher.get_index_data('USDKRW=X')
        usd_krw_rate = usd_krw_rate if usd_krw_rate else 1350.0
        logger.info(f"USD/KRW 환율: {usd_krw_rate}")
        
        stock_and_crypto_tickers = portfolio_df[portfolio_df['original_type'].isin(['주식', '암호화폐'])]['ticker'].unique().tolist()
        current_prices = get_current_prices_for_portfolio(stock_and_crypto_tickers)
        logger.info(f"현재가 조회 완료: {len(current_prices)} 종목")
        
        # 4. 현재가 및 수익률 계산
        portfolio_df['current_price'] = portfolio_df.apply(
            lambda row: current_prices.get(row['ticker'], row['avg_price']) 
            if row['original_type'] in ['주식', '암호화폐'] else row['avg_price'], axis=1
        )
        
        portfolio_df['current_value'] = portfolio_df['quantity'] * portfolio_df['current_price']
        portfolio_df['profit_loss'] = portfolio_df['current_value'] - portfolio_df['total_purchase']
        portfolio_df['return_rate'] = (portfolio_df['profit_loss'] / portfolio_df['total_purchase'] * 100).fillna(0)
        
        # 5. DB에 저장
        db_manager = PortfolioDBManager()
        success = db_manager.save_portfolio_snapshot(portfolio_df, usd_krw_rate)
        
        if success:
            # 요약 정보 로깅
            total_value_krw = 0
            for _, row in portfolio_df.iterrows():
                if row['currency'] == 'USD':
                    value_krw = row['current_value'] * usd_krw_rate
                else:
                    value_krw = row['current_value']
                total_value_krw += value_krw
            
            logger.info(f"포트폴리오 저장 완료 - 총 자산: ₩{total_value_krw:,.0f}, 계좌: {portfolio_df['account_id'].nunique()}개, 자산: {len(portfolio_df)}개")
        else:
            logger.error("포트폴리오 저장 실패")
            
    except Exception as e:
        logger.error(f"일일 포트폴리오 저장 작업 실패: {e}", exc_info=True)

def run_scheduler():
    """스케줄러 실행"""
    logger.info("Portfolio Scheduler 시작")
    logger.info("매분마다 포트폴리오 데이터를 저장합니다.")
    
    # 매분마다 실행
    schedule.every().minute.do(save_daily_portfolio)
    
    # 원래 설정 (주석 처리)
    # schedule.every().day.at("06:00").do(save_daily_portfolio)
    
    # 테스트용: 즉시 실행 (주석 해제하여 사용)
    # save_daily_portfolio()
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
        except KeyboardInterrupt:
            logger.info("스케줄러 종료")
            break
        except Exception as e:
            logger.error(f"스케줄러 오류: {e}", exc_info=True)
            time.sleep(300)  # 5분 후 재시도

if __name__ == "__main__":
    # 명령줄 인수 처리
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        logger.info("테스트 모드: 즉시 포트폴리오 저장 실행")
        save_daily_portfolio()
    else:
        run_scheduler()
