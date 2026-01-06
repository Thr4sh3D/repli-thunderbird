@echo off
title Repli Server 🧠
echo Startar upp din AI-assistent...

:: Gå till exakt den här mappen
cd /d "C:\Users\tobia\OneDrive\Dokument\Privat\Kodning\Repli-Thunderbird\repli-thunderbird\backend"

:: Starta servern
uvicorn server:app --reload

:: Om något går fel stannar rutan kvar
pause