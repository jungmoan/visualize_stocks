import pandas as pd



class DCIntegration:
    def __init__(self):
        asset_path = "private/dc_balance.csv"
        self.asset_df = pd.read_csv(asset_path)

        print(self.asset_df )

    def get_balance(self):
        stock = self.get_stock_info()
        deposit = self.get_deposit()
        merged = {'DC': {'stock': stock['DC'].get('stock', []), 'deposit': deposit['DC'].get('deposit', [])}}
        return merged
    
    def get_stock_info(self):
        """DC 계좌 잔고 조회"""
        ret = {
            "DC": {
                "stock": [],
                "deposit": []
            }
        }
        
        # DC 계좌 잔고 정보
        for index, row in self.asset_df.iterrows():
            if row['ticker'] == 'DC_DEPOSIT':
                continue
            ret["DC"]["stock"].append({
                'name': row['name'],
                'ticker': row['ticker'],
                'quantity': float(row['quantity']),
                'avg_price': float(row['avg_price']),
                'currency': row['currency']
            })
        
        return ret

    def get_deposit(self):
        ret =  {
                    "deposit": [
                        {
                            'name': 'DC 예수금',
                            'ticker': 'DC_DEPOSIT',
                            'quantity': float(self.asset_df.loc[self.asset_df['ticker'] == 'DC_DEPOSIT', 'quantity'].values[0]),
                            'avg_price': 0.0,  # KRW는 평균 매입가가 없으므로 0으로 설정
                            'currency': 'KRW'
                        }
                    ]
                }
        return {'DC': ret}

    def get_orderbook(self, ticker):
        # Implement the logic to fetch order book for a specific ticker
        pass

if __name__ == "__main__":
    hyundai = DCIntegration()
    balance = hyundai.get_balance()
    print(balance)