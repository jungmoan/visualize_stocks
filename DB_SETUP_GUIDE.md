# 📊 포트폴리오 DB 저장 시스템

매분마다 자동으로 포트폴리오 데이터를 SQLite DB에 저장하는 시스템입니다.

## 🏗️ 시스템 구성

### 1. `db_manager.py`
- SQLite 데이터베이스 관리 클래스
- 포트폴리오 히스토리 및 자산별 상세 데이터 저장
- 테이블: `portfolio_history`, `asset_history`

### 2. `portfolio_scheduler.py`
- 매분마다 자동 실행되는 스케줄러
- 포트폴리오 데이터 수집 및 DB 저장
- 로그 파일: `private/portfolio_scheduler.log`

### 3. `pages/6_📊_Portfolio_History.py`
- Streamlit 히스토리 조회 페이지
- 차트 및 분석 기능 제공

## 🚀 설치 및 설정

### 1. 자동 설치 (추천)
```bash
cd /home/jungmo/apps/visualize_stocks
./setup_scheduler.sh
```

### 2. 수동 설치
```bash
# 서비스 파일 복사
sudo cp portfolio-scheduler.service /etc/systemd/system/

# systemd 재로드
sudo systemctl daemon-reload

# 서비스 활성화 및 시작
sudo systemctl enable portfolio-scheduler
sudo systemctl start portfolio-scheduler
```

## 📋 주요 명령어

### 서비스 관리
```bash
# 상태 확인
sudo systemctl status portfolio-scheduler

# 로그 확인 (실시간)
sudo journalctl -u portfolio-scheduler -f

# 서비스 재시작
sudo systemctl restart portfolio-scheduler

# 서비스 중지
sudo systemctl stop portfolio-scheduler

# 서비스 비활성화
sudo systemctl disable portfolio-scheduler
```

### 수동 실행 (테스트용)
```bash
cd /home/jungmo/apps/visualize_stocks
source .venv/bin/activate
python3 portfolio_scheduler.py test
```

## 📊 데이터베이스 구조

### `portfolio_history` 테이블
- `record_datetime`: 기록 날짜시간 (분 단위)
- `total_purchase_krw`: 총 매입금액 (KRW)
- `total_value_krw`: 총 평가금액 (KRW)  
- `total_profit_krw`: 총 손익 (KRW)
- `total_return_rate`: 총 수익률 (%)
- `total_purchase_usd`: 총 매입금액 (USD)
- `total_value_usd`: 총 평가금액 (USD)
- `total_profit_usd`: 총 손익 (USD)
- `account_count`: 계좌 수
- `asset_count`: 자산 수

### `asset_history` 테이블
- 각 자산별 상세 정보 저장 (분 단위)
- 계좌별, 종목별 구분
- 수량, 가격, 수익률 등 포함

## 💡 사용법

### 1. Streamlit에서 히스토리 조회
- **포트폴리오 히스토리** 페이지 접속
- 기간 선택 및 통화 설정
- 차트 및 상세 데이터 확인

### 2. 수동 저장
- **실제 포트폴리오** 페이지에서 **💾 DB에 저장** 버튼 클릭
- 또는 **포트폴리오 히스토리** 페이지에서 **🔄 현재 포트폴리오 수동 저장** 버튼 클릭

### 3. 스케줄링
- 매분마다 자동 실행하여 실시간 모니터링
- 분 단위 포트폴리오 변화 추적 가능
- 실행 결과는 로그 파일에서 확인
- 시스템 재부팅 후에도 자동 시작

## 🔧 문제 해결

### 스케줄러가 실행되지 않는 경우
```bash
# 서비스 상태 확인
sudo systemctl status portfolio-scheduler

# 로그 확인
sudo journalctl -u portfolio-scheduler --no-pager

# 권한 확인
ls -la /home/jungmo/apps/visualize_stocks/portfolio_scheduler.py
```

### 데이터베이스 직접 접근
```bash
cd /home/jungmo/apps/visualize_stocks
sqlite3 private/portfolio_history.db

# 테이블 목록 확인
.tables

# 최근 데이터 확인
SELECT * FROM portfolio_history ORDER BY record_datetime DESC LIMIT 5;

# 종료
.exit
```

## 📁 파일 위치

- 데이터베이스: `/home/jungmo/apps/visualize_stocks/private/portfolio_history.db`
- 로그 파일: `/home/jungmo/apps/visualize_stocks/private/portfolio_scheduler.log`
- 백업 파일: `/home/jungmo/apps/visualize_stocks/private/balance_backup_*.json`
- 서비스 파일: `/etc/systemd/system/portfolio-scheduler.service`

## ⚡ 성능 최적화

- 캐시 TTL 5분으로 설정
- 백업 파일 자동 생성
- 에러 시 자동 재시작
- 로깅을 통한 모니터링

---

```
source .venv/bin/activate && python3 portfolio_scheduler.py &
```

**마지막 업데이트**: 2025-08-07
