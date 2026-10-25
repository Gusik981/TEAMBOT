@echo off
chcp 65001 > nul
title TeamGrief - Ticket Bot 24/7

:loop
echo ===================================================
echo [%date% %time%] Запуск тикет-бота TeamGrief...
echo ===================================================
python bot.py
echo.
echo [%date% %time%] Процесс завершился или произошел сбой.
echo Перезапуск бота через 5 секунд (нажмите Ctrl+C для отмены)...
timeout /t 5 /nobreak > nul
goto loop
