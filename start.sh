#!/bin/bash
echo "╔══════════════════════════════════════╗"
echo "║        СберБанк — Запуск сервера     ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Установка зависимостей..."
pip install flask flask-sqlalchemy flask-login flask-bcrypt --break-system-packages -q

echo "Запуск сервера..."
echo "Откройте браузер: http://localhost:5000"
echo ""
cd "$(dirname "$0")"
python app.py
