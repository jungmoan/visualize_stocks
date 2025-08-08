#!/bin/bash

# Portfolio Scheduler 설치 스크립트

echo "🚀 Portfolio Scheduler 설정을 시작합니다..."

# 현재 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="portfolio-scheduler"
SERVICE_FILE="${SERVICE_NAME}.service"

# 서비스 파일을 시스템에 복사
echo "📁 서비스 파일을 /etc/systemd/system/에 복사..."
sudo cp "$SCRIPT_DIR/$SERVICE_FILE" "/etc/systemd/system/"

# systemd 데몬 리로드
echo "🔄 systemd 데몬 리로드..."
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
echo "⚙️  서비스 활성화..."
sudo systemctl enable "$SERVICE_NAME"

# 서비스 시작
echo "▶️  서비스 시작..."
sudo systemctl start "$SERVICE_NAME"

# 서비스 상태 확인
echo "📊 서비스 상태 확인..."
sudo systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "✅ Portfolio Scheduler 설정이 완료되었습니다!"
echo ""
echo "🔍 유용한 명령어들:"
echo "   서비스 상태 확인:   sudo systemctl status $SERVICE_NAME"
echo "   서비스 로그 확인:   sudo journalctl -u $SERVICE_NAME -f"
echo "   서비스 중지:       sudo systemctl stop $SERVICE_NAME"
echo "   서비스 재시작:     sudo systemctl restart $SERVICE_NAME"
echo "   서비스 비활성화:   sudo systemctl disable $SERVICE_NAME"
echo ""
echo "📅 매분마다 포트폴리오 데이터가 자동으로 저장됩니다."
echo "📊 Streamlit의 '포트폴리오 히스토리' 페이지에서 확인할 수 있습니다."
