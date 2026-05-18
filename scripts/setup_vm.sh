#!/bin/bash
# Setup script for Oracle Cloud Ubuntu VM
# Run: bash <(curl -s https://raw.githubusercontent.com/placucci22/spotify-remote/main/scripts/setup_vm.sh)
set -e

echo "=== [1/4] Atualizando sistema ==="
sudo apt-get update -q
sudo apt-get install -y python3 python3-pip curl

echo "=== [2/4] Instalando dependencias Python ==="
pip3 install --quiet requests beautifulsoup4 playwright

echo "=== [3/4] Instalando Playwright + Chromium ==="
python3 -m playwright install chromium --with-deps

echo "=== [4/4] Baixando scraper ==="
mkdir -p ~/liga-scraper
curl -s https://raw.githubusercontent.com/placucci22/spotify-remote/main/scripts/scrape_liga.py \
     -o ~/liga-scraper/scrape_liga.py

echo ""
echo "==================================================="
echo " Setup concluido!"
echo "==================================================="
echo ""
echo "Agora adicione o cron job com:  crontab -e"
echo ""
echo "Cole esta linha (substitua pelos seus valores):" 
echo "0 9 * * * KV_REST_API_URL='COLE_AQUI' KV_REST_API_TOKEN='COLE_AQUI' python3 ~/liga-scraper/scrape_liga.py >> ~/scrape.log 2>&1"
echo ""
