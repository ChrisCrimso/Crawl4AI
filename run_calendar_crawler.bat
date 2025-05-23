@echo off
echo Running FIU Calendar Crawler at %date% %time%
cd /d "C:\Users\ChrisG\Desktop\Crawl4AI"
python calendar_crawler.py >> crawler_logs\calendar_crawler_%date:~-4,4%%date:~-7,2%%date:~-10,2%.log 2>&1
echo Calendar crawler completed at %date% %time% with exit code %ERRORLEVEL% 