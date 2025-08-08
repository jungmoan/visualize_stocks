import sqlite3
import pandas as pd
from datetime import datetime, date
import os

class PortfolioDBManager:
    def __init__(self, db_path="private/portfolio_history.db"):
        """
        포트폴리오 히스토리 DB 관리자
        """
        self.db_path = db_path
        # 디렉토리가 없으면 생성
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """데이터베이스 및 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 포트폴리오 히스토리 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_datetime DATETIME NOT NULL,
                    total_purchase_krw REAL NOT NULL,
                    total_value_krw REAL NOT NULL,
                    total_profit_krw REAL NOT NULL,
                    total_return_rate REAL NOT NULL,
                    total_purchase_usd REAL NOT NULL,
                    total_value_usd REAL NOT NULL,
                    total_profit_usd REAL NOT NULL,
                    account_count INTEGER NOT NULL,
                    asset_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 자산별 히스토리 테이블 생성
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS asset_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_datetime DATETIME NOT NULL,
                    account_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    name TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    avg_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    currency TEXT NOT NULL,
                    value_krw REAL NOT NULL,
                    value_usd REAL NOT NULL,
                    profit_loss_krw REAL NOT NULL,
                    return_rate REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (record_datetime) REFERENCES portfolio_history(record_datetime)
                )
            ''')
            
            conn.commit()
    
    def save_portfolio_snapshot(self, portfolio_df, usd_krw_rate):
        """
        포트폴리오 스냅샷을 데이터베이스에 저장
        
        Args:
            portfolio_df: 처리된 포트폴리오 DataFrame
            usd_krw_rate: USD/KRW 환율
        """
        today_datetime = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                # 총 자산 계산 (KRW 기준)
                total_purchase_krw = 0
                total_value_krw = 0
                
                for _, row in portfolio_df.iterrows():
                    if row['currency'] == 'USD':
                        purchase_krw = row['total_purchase'] * usd_krw_rate
                        value_krw = row['current_value'] * usd_krw_rate
                    else:
                        purchase_krw = row['total_purchase']
                        value_krw = row['current_value']
                    
                    total_purchase_krw += purchase_krw
                    total_value_krw += value_krw
                
                total_profit_krw = total_value_krw - total_purchase_krw
                total_return_rate = (total_profit_krw / total_purchase_krw * 100) if total_purchase_krw > 0 else 0
                
                # USD 기준 계산
                total_purchase_usd = total_purchase_krw / usd_krw_rate
                total_value_usd = total_value_krw / usd_krw_rate
                total_profit_usd = total_profit_krw / usd_krw_rate
                
                account_count = portfolio_df['account_id'].nunique()
                asset_count = len(portfolio_df)
                
                # 포트폴리오 히스토리 저장 (매번 새로운 레코드 생성)
                cursor.execute('''
                    INSERT INTO portfolio_history 
                    (record_datetime, total_purchase_krw, total_value_krw, total_profit_krw, 
                     total_return_rate, total_purchase_usd, total_value_usd, total_profit_usd,
                     account_count, asset_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    today_datetime, total_purchase_krw, total_value_krw, total_profit_krw,
                    total_return_rate, total_purchase_usd, total_value_usd, total_profit_usd,
                    account_count, asset_count
                ))
                
                # 자산별 히스토리 저장 (매번 새로운 레코드들 생성)
                
                # 자산별 히스토리 저장
                for _, row in portfolio_df.iterrows():
                    # KRW 기준 값 계산
                    if row['currency'] == 'USD':
                        value_krw = row['current_value'] * usd_krw_rate
                        profit_loss_krw = (row['current_value'] - row['total_purchase']) * usd_krw_rate
                        value_usd = row['current_value']
                    else:
                        value_krw = row['current_value']
                        profit_loss_krw = row['current_value'] - row['total_purchase']
                        value_usd = row['current_value'] / usd_krw_rate
                    
                    cursor.execute('''
                        INSERT INTO asset_history 
                        (record_datetime, account_id, ticker, name, asset_type, quantity, 
                         avg_price, current_price, currency, value_krw, value_usd, 
                         profit_loss_krw, return_rate)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        today_datetime, row['account_id'], row['ticker'], row['name'], 
                        row['asset_type'], row['quantity'], row['avg_price'], 
                        row['current_price'], row['currency'], value_krw, value_usd,
                        profit_loss_krw, row['return_rate']
                    ))
                
                conn.commit()
                print(f"포트폴리오 스냅샷 저장 완료: {today_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
                return True
                
            except Exception as e:
                print(f"포트폴리오 스냅샷 저장 실패: {e}")
                conn.rollback()
                return False
    
    def get_portfolio_history(self, start_date=None, end_date=None):
        """
        포트폴리오 히스토리 조회
        
        Args:
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
        
        Returns:
            DataFrame: 포트폴리오 히스토리
        """
        query = "SELECT * FROM portfolio_history"
        params = []
        
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append("DATE(record_datetime) >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("DATE(record_datetime) <= ?")
                params.append(end_date)
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY record_datetime"
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)
    
    def get_asset_history(self, record_datetime):
        """
        특정 날짜시간의 자산별 히스토리 조회
        
        Args:
            record_datetime: 조회할 날짜시간 (YYYY-MM-DD HH:MM:SS)
        
        Returns:
            DataFrame: 자산별 히스토리
        """
        query = "SELECT * FROM asset_history WHERE record_datetime = ? ORDER BY value_krw DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(query, conn, params=[record_datetime])
    
    def get_latest_record(self):
        """최근 기록 조회"""
        query = "SELECT * FROM portfolio_history ORDER BY record_datetime DESC LIMIT 1"
        
        with sqlite3.connect(self.db_path) as conn:
            result = pd.read_sql_query(query, conn)
            return result.iloc[0] if not result.empty else None
    
    def delete_record(self, record_datetime):
        """특정 날짜시간의 기록 삭제"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM asset_history WHERE record_datetime = ?', (record_datetime,))
            cursor.execute('DELETE FROM portfolio_history WHERE record_datetime = ?', (record_datetime,))
            
            conn.commit()
            print(f"기록 삭제 완료: {record_datetime}")

if __name__ == "__main__":
    # 테스트 코드
    db_manager = PortfolioDBManager()
    print("데이터베이스 초기화 완료")
