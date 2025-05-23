@echo off
echo FIU Web Crawler - Recrawl and Migration Tool
echo ===========================================
echo.

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

echo Step 1: Running Playwright crawler on all problematic directories
echo This may take some time depending on the number of files...
python recrawl_all_issues.py --timeout 60000 --wait 8
echo.

echo Step 2: Migrating successfully recrawled content to FIU_content
python migrate_successful_crawls.py
echo.

echo Process complete!
echo Check the comparison_results directory for reports and migration logs.
pause 