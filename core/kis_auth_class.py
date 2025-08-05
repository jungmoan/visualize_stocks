# -*- coding: utf-8 -*-
# ====|  (REST) 접근 토큰 / (Websocket) 웹소켓 접속키 발급 에 필요한 API 호출 샘플 아래 참고하시기 바랍니다.  |=====================
# ====|  API 호출 공통 함수 포함 - 클래스화 버전                                  |=====================

import asyncio
import copy
import json
import logging
import os
import time
from base64 import b64decode
from collections import namedtuple
from collections.abc import Callable
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
import websockets
import yaml
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


class KISAuth:
    """KIS API 인증 및 호출을 관리하는 클래스"""
    
    def __init__(self, config_path):
        """
        KISAuth 클래스 초기화
        
        Args:
            config_path (str): kis_devlp.yaml 파일 경로. None이면 기본 경로 사용
        """
        # 상수 설정
        self.key_bytes = 32
        
        # config_path에서 파일명 추출하여 토큰 파일명 생성
        self.config_root, config_filename = os.path.split(config_path)
        config_filename = os.path.splitext(config_filename)[0]  # 확장자 제거
        print(f"Config root: {self.config_root}, Config filename: {config_filename}")
        self.token_tmp = os.path.join(
            self.config_root, f"{config_filename}_{datetime.today().strftime('%Y%m%d')}"
        )
        
        # 접근토큰 관리하는 파일 존재여부 체크, 없으면 생성
        if not os.path.exists(self.token_tmp):
            with open(self.token_tmp, "w+") as f:
                pass
        
        # 설정 파일 로드
        config_file = config_path or os.path.join(self.config_root, "kis_devlp.yaml")
        with open(config_file, encoding="UTF-8") as f:
            self._cfg = yaml.load(f, Loader=yaml.FullLoader)
        
        # 인스턴스 변수 초기화
        self._TRENV = tuple()
        self._last_auth_time = datetime.now()
        self._autoReAuth = False
        self._DEBUG = False
        self._isPaper = False
        self._smartSleep = 0.1
        
        # 기본 헤더값 정의
        self._base_headers = {
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "charset": "UTF-8",
            "User-Agent": self._cfg["my_agent"],
        }
    
    def clearConsole(self):
        """콘솔 화면 클리어"""
        os.system("cls" if os.name in ("nt", "dos") else "clear")
    
    def save_token(self, my_token, my_expired):
        """토큰 발급 받아 저장"""
        valid_date = datetime.strptime(my_expired, "%Y-%m-%d %H:%M:%S")
        with open(self.token_tmp, "w", encoding="utf-8") as f:
            f.write(f"token: {my_token}\n")
            f.write(f"valid-date: {valid_date}\n")
    
    def read_token(self):
        """토큰 확인"""
        try:
            with open(self.token_tmp, encoding="UTF-8") as f:
                tkg_tmp = yaml.load(f, Loader=yaml.FullLoader)
            
            exp_dt = datetime.strftime(tkg_tmp["valid-date"], "%Y-%m-%d %H:%M:%S")
            now_dt = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            
            if exp_dt > now_dt:
                return tkg_tmp["token"]
            else:
                return None
        except Exception:
            return None
    
    def _getBaseHeader(self):
        """기본 헤더 반환"""
        if self._autoReAuth:
            self.reAuth()
        return copy.deepcopy(self._base_headers)
    
    def _setTRENV(self, cfg):
        """거래 환경 설정"""
        nt1 = namedtuple(
            "KISEnv",
            ["my_app", "my_sec", "my_acct", "my_prod", "my_htsid", "my_token", "my_url", "my_url_ws"],
        )
        d = {
            "my_app": cfg["my_app"],
            "my_sec": cfg["my_sec"],
            "my_acct": cfg["my_acct"],
            "my_prod": cfg["my_prod"],
            "my_htsid": cfg["my_htsid"],
            "my_token": cfg["my_token"],
            "my_url": cfg["my_url"],
            "my_url_ws": cfg["my_url_ws"],
        }
        self._TRENV = nt1(**d)
    
    def isPaperTrading(self):
        """모의투자 여부 확인"""
        return self._isPaper
    
    def changeTREnv(self, token_key, svr="prod", product=None):
        """거래 환경 변경"""
        if product is None:
            product = self._cfg["my_prod"]
            
        cfg = dict()
        
        if svr == "prod":  # 실전투자
            ak1 = "my_app"
            ak2 = "my_sec"
            self._isPaper = False
            self._smartSleep = 0.05
        elif svr == "vps":  # 모의투자
            ak1 = "paper_app"
            ak2 = "paper_sec"
            self._isPaper = True
            self._smartSleep = 0.5
        
        cfg["my_app"] = self._cfg[ak1]
        cfg["my_sec"] = self._cfg[ak2]
        
        # 계좌 설정
        if svr == "prod" and product == "01":
            cfg["my_acct"] = self._cfg["my_acct_stock"]
        elif svr == "prod" and product == "03":
            cfg["my_acct"] = self._cfg["my_acct_future"]
        elif svr == "prod" and product == "08":
            cfg["my_acct"] = self._cfg["my_acct_future"]
        elif svr == "prod" and product == "22":
            cfg["my_acct"] = self._cfg["my_acct_stock"]
        elif svr == "prod" and product == "29":
            cfg["my_acct"] = self._cfg["my_acct_stock"]
        elif svr == "vps" and product == "01":
            cfg["my_acct"] = self._cfg["my_paper_stock"]
        elif svr == "vps" and product == "03":
            cfg["my_acct"] = self._cfg["my_paper_future"]
        
        cfg["my_prod"] = product
        cfg["my_htsid"] = self._cfg["my_htsid"]
        cfg["my_url"] = self._cfg[svr]
        
        try:
            my_token = self._TRENV.my_token
        except AttributeError:
            my_token = ""
        cfg["my_token"] = my_token if token_key else token_key
        cfg["my_url_ws"] = self._cfg["ops" if svr == "prod" else "vops"]
        
        self._setTRENV(cfg)
    
    def _getResultObject(self, json_data):
        """JSON 데이터를 namedtuple 객체로 변환"""
        _tc_ = namedtuple("res", json_data.keys())
        return _tc_(**json_data)
    
    def auth(self, svr="prod", product=None, url=None):
        """토큰 발급"""
        # if product is None:
        product = self._cfg["my_prod"]
        
        print(product)
        p = {
            "grant_type": "client_credentials",
        }
        
        if svr == "prod":
            ak1 = "my_app"
            ak2 = "my_sec"
        elif svr == "vps":
            ak1 = "paper_app"
            ak2 = "paper_sec"
        
        p["appkey"] = self._cfg[ak1]
        p["appsecret"] = self._cfg[ak2]
        
        saved_token = self.read_token()
        if saved_token is None:
            url = f"{self._cfg[svr]}/oauth2/tokenP"
            print(f"Requesting new token from {url}..., {p}")
            res = requests.post(
                url, data=json.dumps(p), headers=self._getBaseHeader()
            )
            rescode = res.status_code
            print(rescode)
            if rescode == 200:
                my_token = self._getResultObject(res.json()).access_token
                my_expired = self._getResultObject(res.json()).access_token_token_expired
                self.save_token(my_token, my_expired)
            else:
                print("Get Authentification token fail!\nYou have to restart your app!!!")
                return
        else:
            my_token = saved_token
        
        self.changeTREnv(my_token, svr, product)
        
        self._base_headers["authorization"] = f"Bearer {my_token}"
        self._base_headers["appkey"] = self._TRENV.my_app
        self._base_headers["appsecret"] = self._TRENV.my_sec
        
        self._last_auth_time = datetime.now()

        self.env_dv = "demo" if self._isPaper else "real"

        if self._DEBUG:
            print(f"[{self._last_auth_time}] => get AUTH Key completed!")
    
    def reAuth(self, svr="prod", product=None):
        """토큰 재발급"""
        if product is None:
            product = self._cfg["my_prod"]
            
        n2 = datetime.now()
        if (n2 - self._last_auth_time).seconds >= 86400:
            self.auth(svr, product)
    
    def getEnv(self):
        """환경 설정 반환"""
        return self._cfg
    
    def smart_sleep(self):
        """API 호출 간격 조절"""
        if self._DEBUG:
            print(f"[RateLimit] Sleeping {self._smartSleep}s ")
        time.sleep(self._smartSleep)
    
    def getTREnv(self):
        """거래 환경 반환"""
        return self._TRENV
    
    def set_order_hash_key(self, h, p):
        """주문 API 해시키 설정"""
        url = f"{self.getTREnv().my_url}/uapi/hashkey"
        res = requests.post(url, data=json.dumps(p), headers=h)
        rescode = res.status_code
        if rescode == 200:
            h["hashkey"] = self._getResultObject(res.json()).HASH
        else:
            print("Error:", rescode)
    
    def _url_fetch(self, api_url, ptr_id, tr_cont, params, appendHeaders=None, postFlag=False, hashFlag=True):
        """API 호출 공통 함수"""
        url = f"{self.getTREnv().my_url}{api_url}"
        
        headers = self._getBaseHeader()
        
        tr_id = ptr_id
        if ptr_id[0] in ("T", "J", "C"):
            if self.isPaperTrading():
                tr_id = "V" + ptr_id[1:]
        
        headers["tr_id"] = tr_id
        headers["custtype"] = "P"
        headers["tr_cont"] = tr_cont
        
        if appendHeaders is not None:
            if len(appendHeaders) > 0:
                for x in appendHeaders.keys():
                    headers[x] = appendHeaders.get(x)
        
        if self._DEBUG:
            print("< Sending Info >")
            print(f"URL: {url}, TR: {tr_id}")
            print(f"<header>\n{headers}")
            print(f"<body>\n{params}")
        
        if postFlag:
            res = requests.post(url, headers=headers, data=json.dumps(params))
        else:
            res = requests.get(url, headers=headers, params=params)
        
        if res.status_code == 200:
            ar = APIResp(res)
            if self._DEBUG:
                ar.printAll()
            return ar
        else:
            print("Error Code : " + str(res.status_code) + " | " + res.text)
            return APIRespError(res.status_code, res.text)


class APIResp:
    """API 응답 처리 클래스"""
    
    def __init__(self, resp):
        self._rescode = resp.status_code
        self._resp = resp
        self._header = self._setHeader()
        self._body = self._setBody()
        self._err_code = self._body.msg_cd
        self._err_message = self._body.msg1

    def getResCode(self):
        return self._rescode

    def _setHeader(self):
        fld = dict()
        for x in self._resp.headers.keys():
            if x.islower():
                fld[x] = self._resp.headers.get(x)
        _th_ = namedtuple("header", fld.keys())
        return _th_(**fld)

    def _setBody(self):
        _tb_ = namedtuple("body", self._resp.json().keys())
        return _tb_(**self._resp.json())

    def getHeader(self):
        return self._header

    def getBody(self):
        return self._body

    def getResponse(self):
        return self._resp

    def isOK(self):
        try:
            if self.getBody().rt_cd == "0":
                return True
            else:
                return False
        except:
            return False

    def getErrorCode(self):
        return self._err_code

    def getErrorMessage(self):
        return self._err_message

    def printAll(self):
        print("<Header>")
        for x in self.getHeader()._fields:
            print(f"\t-{x}: {getattr(self.getHeader(), x)}")
        print("<Body>")
        for x in self.getBody()._fields:
            print(f"\t-{x}: {getattr(self.getBody(), x)}")

    def printError(self, url):
        print(
            "-------------------------------\nError in response: ",
            self.getResCode(),
            " url=",
            url,
        )
        print(
            "rt_cd : ",
            self.getBody().rt_cd,
            "/ msg_cd : ",
            self.getErrorCode(),
            "/ msg1 : ",
            self.getErrorMessage(),
        )
        print("-------------------------------")


class APIRespError(APIResp):
    """API 오류 응답 클래스"""
    
    def __init__(self, status_code, error_text):
        self.status_code = status_code
        self.error_text = error_text
        self._error_code = str(status_code)
        self._error_message = error_text

    def isOK(self):
        return False

    def getErrorCode(self):
        return self._error_code

    def getErrorMessage(self):
        return self._error_message

    def getBody(self):
        class EmptyBody:
            def __getattr__(self, name):
                return None
        return EmptyBody()

    def getHeader(self):
        class EmptyHeader:
            tr_cont = ""
            def __getattr__(self, name):
                return ""
        return EmptyHeader()

    def printAll(self):
        print(f"=== ERROR RESPONSE ===")
        print(f"Status Code: {self.status_code}")
        print(f"Error Message: {self.error_text}")
        print(f"======================")

    def printError(self, url=""):
        print(f"Error Code : {self.status_code} | {self.error_text}")
        if url:
            print(f"URL: {url}")


# # 하위 호환성을 위한 전역 인스턴스 및 함수들
# _kis_auth_instance = None

# def get_kis_auth_instance():
#     """전역 KISAuth 인스턴스 반환"""
#     global _kis_auth_instance
#     if _kis_auth_instance is None:
#         _kis_auth_instance = KISAuth()
#     return _kis_auth_instance

# # 기존 함수들의 래퍼 (하위 호환성)
# def auth(svr="prod", product=None):
#     return get_kis_auth_instance().auth(svr, product)

# def getTREnv():
#     return get_kis_auth_instance().getTREnv()

# def isPaperTrading():
#     return get_kis_auth_instance().isPaperTrading()

# def smart_sleep():
#     return get_kis_auth_instance().smart_sleep()

# def _url_fetch(api_url, ptr_id, tr_cont, params, appendHeaders=None, postFlag=False, hashFlag=True):
#     return get_kis_auth_instance()._url_fetch(api_url, ptr_id, tr_cont, params, appendHeaders, postFlag, hashFlag)
