import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.kis_auth_class import KISAuth

from typing import Optional, Tuple
import pandas as pd
import json

indexMapping = {
    "cblc_dvsn_name": "잔고구분명",
    "prdt_name": "상품명",
    "pdno": "상품번호",
    "item_dvsn_name": "종목구분명",
    "thdt_buyqty": "당일매수수량",
    "thdt_sll_qty": "당일매도수량",
    "hldg_qty": "보유수량",
    "ord_psbl_qty": "주문가능수량",
    "pchs_avg_pric": "매입평균가격",
    "pchs_amt": "매입금액",
    "prpr": "현재가",
    "evlu_amt": "평가금액",
    "evlu_pfls_amt": "평가손익금액",
    "evlu_erng_rt": "평가수익률",
    "dnca_tot_amt": "예수금총액",
    "nxdy_excc_amt": "익일정산금액",
    "prvs_rcdl_excc_amt": "전일정산금액",
    "thdt_buy_amt": "당일매수금액",
    "thdt_sll_amt": "당일매도금액",
    "thdt_tlex_amt": "당일거래세금액",
    "scts_evlu_amt": "유가증권평가금액",
    "tot_evlu_amt": "총평가금액",
    "prdt_name": "상품명",
    "cblc_qty13": "보유수량",
    "thdt_buy_ccld_qty1": "당일매수체결수량",
    "thdt_sll_ccld_qty1": "당일매도체결수량",
    "ccld_qty_smtl1": "체결수량합계",
    "ord_psbl_qty1": "주문가능수량",
    "frcr_pchs_amt": "외화매입금액",
    "frcr_evlu_amt2": "외화평가금액",
    "evlu_pfls_amt2": "평가손익금액",
    "evlu_pfls_rt1": "평가손익률",
    "pdno": "상품번호",
    "bass_exrt": "기준환율",
    "buy_crcy_cd": "매수통화코드",
    "ovrs_now_pric1": "해외현재가",
    "avg_unpr3": "평균단가",
    "tr_mket_name": "시장명",
    "natn_kor_name": "국가명",
    "pchs_rmnd_wcrc_amt": "매입잔여원화금액",
    "thdt_buy_ccld_frcr_amt": "당일매수체결외화금액",
    "thdt_sll_ccld_frcr_amt": "당일매도체결외화금액",
    "unit_amt": "단위금액",
    "std_pdno": "표준상품번호",
    "prdt_type_cd": "상품유형코드",
    "scts_dvsn_name": "증권구분명",
    "loan_rmnd": "대출잔액",
    "loan_dt": "대출일자",
    "loan_expd_dt": "대출만기일자",
    "ovrs_excg_cd": "해외거래소코드",
    "item_lnkg_excg_cd": "종목연계거래소코드",
    "prdt_dvsn": "상품구분",
    "crcy_cd": "통화코드",
    "crcy_cd_name": "통화명",
    "frcr_buy_amt_smtl": "외화매수금액합계",
    "frcr_sll_amt_smtl": "외화매도금액합계",
    "frcr_dncl_amt_2": "외화정산금액",
    "frst_bltn_exrt": "최초고시환율",
    "frcr_buy_mgn_amt": "외화매수증거금금액",
    "frcr_etc_mgna": "외화기타증거금",
    "frcr_drwg_psbl_amt_1": "외화인출가능금액",
    "frcr_evlu_amt2": "외화평가금액",
    "acpl_cstd_crcy_yn": "실현환산통화여부",
    "nxdy_frcr_drwg_psbl_amt": "익일외화인출가능금액",
    "pchs_amt_smtl": "매입금액합계",
    "evlu_amt_smtl": "평가금액합계",
    "evlu_pfls_amt_smtl": "평가손익금액합계",
    "dncl_amt": "정산금액",
    "cma_evlu_amt": "CMA평가금액",
    "tot_dncl_amt": "총정산금액",
    "etc_mgna": "기타증거금",
    "wdrw_psbl_tot_amt": "출금가능총금액",
    "frcr_evlu_tota": "외화평가총액",
    "evlu_erng_rt1": "평가수익률",
    "pchs_amt_smtl_amt": "매입금액합계금액",
    "evlu_amt_smtl_amt": "평가금액합계금액",
    "tot_evlu_pfls_amt": "총평가손익금액",
    "tot_asst_amt": "총자산금액",
    "buy_mgn_amt": "매수증거금금액",
    "mgna_tota": "증거금총액",
    "frcr_use_psbl_amt": "외화사용가능금액",
    "ustl_sll_amt_smtl": "미결제매도금액합계",
    "ustl_buy_amt_smtl": "미결제매수금액합계",
    "tot_frcr_cblc_smtl": "총외화잔고합계",
    "tot_loan_amt": "총대출금액"
}

class KISIntegration:
    def __init__(self):
        self.pension_auth = KISAuth("/home/jungmo/apps/visualize_stocks/private/pension_devlp.yaml")
        self.pension_auth.auth()
        self.normal_auth = KISAuth("/home/jungmo/apps/visualize_stocks/private/kis_devlp.yaml")
        self.normal_auth.auth()  # 인증 수행
        self.personal_pension_auth = KISAuth("/home/jungmo/apps/visualize_stocks/private/personal_pension_devlp.yaml")
        self.personal_pension_auth.auth()  # 인증 수행

        pension_trenv = self.pension_auth.getTREnv()
        self.pension_acct = pension_trenv.my_acct
        self.pension_prod = pension_trenv.my_prod
        


    def _pension_inquire_balance(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        API_URL = "/uapi/domestic-stock/v1/trading/pension/inquire-balance"

        cano = self.pension_acct
        acnt_prdt_cd = self.pension_prod
        acca_dvsn_cd = "00"
        inqr_dvsn = "00"
        FK100 = ""
        NK100 = ""
        tr_cont = ""
        tr_id = "TTTC2208R"  # 퇴직연금 잔고조회

        params = {
            "CANO": cano,                       # 종합계좌번호
            "ACNT_PRDT_CD": acnt_prdt_cd,      # 계좌상품코드
            "ACCA_DVSN_CD": acca_dvsn_cd,      # 적립금구분코드
            "INQR_DVSN": inqr_dvsn,            # 조회구분
            "CTX_AREA_FK100": FK100,           # 연속조회검색조건100
            "CTX_AREA_NK100": NK100            # 연속조회키100
        }
        
        res = self.pension_auth._url_fetch(API_URL, tr_id, tr_cont, params)
        current_data1 = pd.DataFrame(res.getBody().output1)
        current_data2 = pd.DataFrame(res.getBody().output2, index=[0])

        current_data1 = current_data1[["prdt_name", "pdno", "hldg_qty", "pchs_avg_pric"]]
        current_data2 = current_data2[["dnca_tot_amt"]]
        
        current_data1["CANO"] = cano
        current_data2["CANO"] = cano

        return current_data1, current_data2
    
    def _normal_inquire_balance_oversea(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        API_URL = "/uapi/overseas-stock/v1/trading/inquire-present-balance"

        cano = self.normal_auth.getTREnv().my_acct
        acnt_prdt_cd = self.normal_auth.getTREnv().my_prod
        wcrc_frcr_dvsn_cd = "02"
        natn_cd = "000"
        tr_mket_cd = "00"
        inqr_dvsn_cd = "00"
        env_dv = self.normal_auth.env_dv
        # TR ID 설정 (모의투자 지원 로직)
        if env_dv == "real":
            tr_id = "CTRP6504R"  # 실전투자용 TR ID
        elif env_dv == "demo":
            tr_id = "VTRP6504R"  # 모의투자용 TR ID
        else:
            raise ValueError("env_dv can only be 'real' or 'demo'")

        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": acnt_prdt_cd,
            "WCRC_FRCR_DVSN_CD": wcrc_frcr_dvsn_cd,
            "NATN_CD": natn_cd,
            "TR_MKET_CD": tr_mket_cd,
            "INQR_DVSN_CD": inqr_dvsn_cd,
        }

        res = self.normal_auth._url_fetch(api_url=API_URL, ptr_id=tr_id, tr_cont="", params=params)

        if res.isOK():
            output_data = res.getBody().output1
            current_data1 = pd.DataFrame(output_data)
            output_data = res.getBody().output2
            current_data2 = pd.DataFrame(output_data)
            output_data = res.getBody().output3
            current_data3 = pd.DataFrame(output_data, index=[0])
        else:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        # 필요한 컬럼만 추출
        current_data1 = current_data1[["prdt_name","pdno", "cblc_qty13", "avg_unpr3"]]
        current_data2 = current_data2[["frcr_dncl_amt_2"]]
        current_data3 = current_data3[["ustl_sll_amt_smtl","tot_dncl_amt"]]

        current_data1["CANO"] = cano
        current_data2["CANO"] = cano
        current_data3["CANO"] = cano

        return current_data1, current_data2, current_data3

    def _gold_inquire_balance(self) -> pd.DataFrame:

        df1 = pd.DataFrame()
        df1["prdt_name"] = ["KRX 금현물"]
        df1["pdno"] = ["M04020000"]
        df1["hldg_qty"] = [22]
        df1["pchs_avg_pric"] = [int(3257430/22)]
        df1["CANO"] = ["GOLD"]

        df2 = pd.DataFrame()
        df2["dnca_tot_amt"] = [1341218]
        df2["CANO"] = ["GOLD"]
        return df1, df2
    
    def _ISA_inquire_balance(self) -> Tuple[pd.DataFrame, pd.DataFrame]:

        df1 = pd.DataFrame()
        df1["prdt_name"] = ["TIGER 미국나스닥100"]
        df1["pdno"] = ["133690"]
        df1["hldg_qty"] = [101]
        df1["pchs_avg_pric"] = [118144]
        df1["CANO"] = ["ISA"]

        df2 = pd.DataFrame()
        df2["dnca_tot_amt"] = [86297]
        df2["CANO"] = ["ISA"]

        return df1, df2

    def get_balance(self, jsondump = False) -> dict:

        pension_stock, pension_deposit = self._pension_inquire_balance()
        normal_stock, normal_usd_deposit, normal_krw_deposit = self._normal_inquire_balance_oversea()
        ISA_stock, ISA_deposit = self._ISA_inquire_balance()

        ret = {}

        # 퇴직연금 잔고 정보 처리
        pension_stock_list = []
        for _, row in pension_stock.iterrows():
            stock_info = {
                "name": row["prdt_name"],
                "ticker": row["pdno"],
                "quantity": float(row["hldg_qty"]),
                "avg_price": float(row["pchs_avg_pric"]),
                "currency": "KRW"  # 퇴직연금은 원화로 가정
            }
            pension_stock_list.append(stock_info)

        pension_deposit_list = []
        p = {
            "name": "퇴직연금 예수금",
            "ticker": "PENSION_DEPOSIT",
            "quantity": 1,  # 예수금은 수량 개념이 없으므로 1로 설정
            "avg_price": float(pension_deposit["dnca_tot_amt"].values[0]),
            "currency": "KRW"  # 예수금은 원화로 가정
        }
        pension_deposit_list.append(p)
        ret[f'{self.pension_auth.getTREnv().my_acct}'] = {
            "stock": pension_stock_list,
            "deposit": pension_deposit_list
        }

        # ISA 잔고 정보 처리
        isa_stock_list = []
        for _, row in ISA_stock.iterrows():
            stock_info = {
                "name": row["prdt_name"],
                "ticker": row["pdno"],
                "quantity": float(row["hldg_qty"]),
                "avg_price": float(row["pchs_avg_pric"]),
                "currency": "KRW"  # ISA는 원화로 가정
            }
            isa_stock_list.append(stock_info)
        isa_deposit_list = []
        i = {
            "name": "ISA 예수금",
            "ticker": "ISA_DEPOSIT",
            "quantity": 1,  # 예수금은 수량 개념이 없으므로 1로 설정
            "avg_price": float(ISA_deposit["dnca_tot_amt"].values[0]),
            "currency": "KRW"  # 예수금은 원화로 가정
        }
        isa_deposit_list.append(i)

        ret['ISA'] = {
            "stock": isa_stock_list,
            "deposit": isa_deposit_list
        }

        # 금 잔고 정보 처리
        gold_stock, gold_deposit = self._gold_inquire_balance()
        gold_stock_list = []
        for _, row in gold_stock.iterrows():
            stock_info = {
                "name": row["prdt_name"],
                "ticker": row["pdno"],
                "quantity": float(row["hldg_qty"]),
                "avg_price": float(row["pchs_avg_pric"]),
                "currency": "KRW"  # 금은 원화로 가정
            }
            gold_stock_list.append(stock_info)
        gold_deposit_list = []
        g = {
            "name": "금 예수금",
            "ticker": "GOLD_DEPOSIT",
            "quantity": 1,  # 예수금은 수량 개념이 없으므로 1로 설정
            "avg_price": float(gold_deposit["dnca_tot_amt"].values[0]),
            "currency": "KRW"  # 예수금은 원화로 가정
        }
        gold_deposit_list.append(g)
        ret['GOLD'] = {
            "stock": gold_stock_list,
            "deposit": gold_deposit_list
        }

        # 해외주식 잔고 정보 처리
        normal_stock_list = []
        normal_deposit_list = []
        for _, row in normal_stock.iterrows():
            stock_info = {
                "name": row["prdt_name"],
                "ticker": row["pdno"],
                "quantity": float(row["cblc_qty13"]),
                "avg_price": float(row["avg_unpr3"]),
                "currency": "USD"  # 해외 주식은 달러로 가정
            }
            normal_stock_list.append(stock_info)

        n1 = {
            "name": "해외주식 예수금",
            "ticker": "OVERSEA_DEPOSIT",
            "quantity": 1,  # 예수금은 수량 개념이 없으므로 1로 설정
            "avg_price": float(normal_usd_deposit["frcr_dncl_amt_2"].values[0]),
            "currency": "USD"  # 예수금은 달러로 가정
        }
        normal_deposit_list.append(n1)
        n2 = {
            "name": "해외주식 원화 예수금",
            "ticker": "OVERSEA_KRW_DEPOSIT",
            "quantity": 1,  # 예수금은 수량 개념이 없으므로 1로 설정
            "avg_price": float(normal_krw_deposit["tot_dncl_amt"].values[0]) + float(normal_krw_deposit["ustl_sll_amt_smtl"].values[0]),
            "currency": "KRW"  # 예수금은 원화로 가정
        }
        normal_deposit_list.append(n2)

        ret[f'{self.normal_auth.getTREnv().my_acct}'] = {
            "stock": normal_stock_list,
            "deposit": normal_deposit_list
        }

        with open("private/balance.json", "w", encoding="utf-8") as f:
            json.dump(ret, f, ensure_ascii=False, indent=2)

        return ret
    
    def get_market_data(self, market_type):
        # 여기에 KIS API를 호출하여 시장 데이터를 가져오는 로직을 추가합니다.
        # 예시로는 주식, ETF, 암호화폐 등의 데이터를 가져올 수 있습니다.
        pass

    def get_stock_info_domestic(self,
        fid_input_iscd: str  # [필수] 입력 종목코드 (ex. 종목코드 (ex 005930 삼성전자), ETN은 종목코드 6자리 앞에 Q 입력 필수)
    ) -> pd.DataFrame:
        
        env_dv = self.normal_auth.env_dv
        API_URL = "/uapi/domestic-stock/v1/quotations/inquire-price"
        fid_cond_mrkt_div_code = "UN"  # 통합 시장 코드

        # 필수 파라미터 검증
        if env_dv == "" or env_dv is None:
            raise ValueError("env_dv is required (e.g. 'real:실전, demo:모의')")
        
        if fid_cond_mrkt_div_code == "" or fid_cond_mrkt_div_code is None:
            raise ValueError("fid_cond_mrkt_div_code is required (e.g. 'J:KRX, NX:NXT, UN:통합')")
        
        if fid_input_iscd == "" or fid_input_iscd is None:
            raise ValueError("fid_input_iscd is required (e.g. '종목코드 (ex 005930 삼성전자), ETN은 종목코드 6자리 앞에 Q 입력 필수')")

        # tr_id 설정
        if env_dv == "real":
            tr_id = "FHKST01010100"
        elif env_dv == "demo":
            tr_id = "FHKST01010100"
        else:
            raise ValueError("env_dv can only be 'real' or 'demo'")

        params = {
            "FID_COND_MRKT_DIV_CODE": fid_cond_mrkt_div_code,
            "FID_INPUT_ISCD": fid_input_iscd
        }
        
        res = self.normal_auth._url_fetch(API_URL, tr_id, "", params)
        
        if res.isOK():
            current_data = pd.DataFrame(res.getBody().output, index=[0])
            return current_data
        else:
            res.printError(url=API_URL)
            return pd.DataFrame() 
        
    
    def get_stock_info_oversea(self, ticker):
        # 해외 주식 티커에 대한 정보를 가져오는 메서드
        return self.normal_auth.get_stock_info(ticker)

if __name__ == "__main__":
    
    inte = KISIntegration()
    
    balance = inte.get_balance()
    print(balance)