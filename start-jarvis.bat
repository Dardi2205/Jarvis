@echo off
title JARVIS Auto-Start
echo Starting JARVIS...

:: Wait for network
timeout /t 10 /nobreak >nul

:: Start JARVIS server
cd /d "C:\Users\dardi\Documents\New OpenCode Project\jarvis"
start /min python backend/main.py
timeout /t 5 /nobreak >nul

:: Start Cloudflare tunnel
start /min "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel run --token "eyJ6b25lSUQiOiJhZWVlNWVmNzRkYzNiMmE0MjY2MTc3NTAyYWUzOWI4NiIsImFjY291bnRJRCI6ImY5MGZmYWU5NTAzNzQzYjQ4Y2FlMjg0MjkzZDM1MTM1Iiwic2VydmVySWQiOiJhYWRkMjhmYS0xYjBkLTRlOWQtYmFiNi0yYmFhNjZhNjBhNjcifQ=="

echo JARVIS is online!
