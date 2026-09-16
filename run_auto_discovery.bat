@echo off
cd /d C:\Users\GREEN-LEAF\Desktop\dana
.venv\Scripts\python.exe manage.py auto_discover_all --limit 12 -v 1 >> logs\auto_discovery.log 2>&1
