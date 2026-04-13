@echo off
REM March 仓库自动推送脚本
REM 用于 OpenClaw 版本升级或巴别塔架构升级前备份

cd /d "C:\Users\30959\.openclaw\workspace\March"

REM 1. 更新脱敏配置
echo [1/5] Updating openclaw.json (sanitized)...
powershell -Command "$config = Get-Content 'C:\Users\30959\.openclaw\openclaw.json' -Raw; $config = $config -replace 'sk-sp-[a-zA-Z0-9]+', 'sk-sp-***REDACTED***'; $config = $config -replace 'sk-or-v1-[a-zA-Z0-9]+', 'sk-or-v1-***REDACTED***'; $config = $config -replace 'ghp_[a-zA-Z0-9]+', 'ghp_***REDACTED***'; $config = $config -replace 'NGZYFVXopbCwn12UHJkpNgkOspo7piPl', '***REDACTED***'; $config = $config -replace '399429463459924165', '***REDACTED***'; $config = $config -replace '99a1282cff39ec6008916016302302fe42dd769c6d1cdfc1', '***REDACTED***'; $config | Set-Content 'config\openclaw.json' -Encoding UTF8 -NoNewline"

REM 2. 更新巴别塔索引文件
echo [2/5] Updating babel index files...
copy /Y "C:\Users\30959\.openclaw\workspace\shared-storage\.index\babel-index.json" "babel\babel-index.json"
copy /Y "C:\Users\30959\.openclaw\workspace\shared-storage\.index\unified-index.json" "babel\unified-index.json"

REM 3. 更新核心脚本
echo [3/5] Updating scripts...
copy /Y "C:\Users\30959\.openclaw\workspace\scripts\knowledge-distiller-auto.py" "scripts\"
copy /Y "C:\Users\30959\.openclaw\workspace\scripts\darwin_evolution.py" "scripts\"
copy /Y "C:\Users\30959\.openclaw\workspace\scripts\darwin-auto.py" "scripts\"
copy /Y "C:\Users\30959\.openclaw\workspace\scripts\babel-selfcheck-engine.py" "scripts\"

REM 4. Git 提交
echo [4/5] Committing changes...
git add -A
git -c user.name="FilnForFun" -c user.email="FilnForFun@users.noreply.github.com" commit -m "Auto-update: OpenClaw config & Babel architecture (%date%)"

REM 5. 推送
echo [5/5] Pushing to GitHub...
git push origin main

echo Done! March repository updated successfully.
pause
