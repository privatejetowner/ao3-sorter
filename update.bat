@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ============================================================
REM  AO3 Sorter - 一键更新脚本
REM  双击运行：抓取 → 生成 tags.json → 推送 GitHub
REM ============================================================

REM --- 配置区 ---

REM GitHub Pages 仓库的本地路径
set "REPO_DIR=C:\Users\33715\Desktop\sidework\ao3\ao3-sorter"

REM 脚本所在目录（ao3_sorter.py 和 gen_tags.py）
set "SCRIPT_DIR=C:\Users\33715\Desktop\sidework\ao3"

REM 要抓取的 tag 列表（用空格分隔）
set TAGS="桂瑞"
REM 添加更多: set TAGS="桂瑞" "另一个tag" "第三个tag"

REM --- 配置区结束 ---

echo ====================================================
echo   AO3 Sorter - 一键更新
echo ====================================================
echo.

REM 抓取每个 tag，输出到仓库目录
for %%T in (%TAGS%) do (
    echo ----------------------------------------
    echo 正在抓取: %%~T
    echo ----------------------------------------
    python "%SCRIPT_DIR%\ao3_sorter.py" "%%~T" "%REPO_DIR%"
    echo.
)

REM 扫描 ao3_sorted_*.html，自动生成 tags.json
echo ----------------------------------------
echo 正在生成 tags.json ...
echo ----------------------------------------
python "%SCRIPT_DIR%\gen_tags.py" "%REPO_DIR%"
echo.

REM 推送到 GitHub
echo ----------------------------------------
echo 正在推送到 GitHub...
echo ----------------------------------------
cd /d "%REPO_DIR%"
git add -A
git commit -m "更新数据 %date% %time:~0,8%"
git push

echo.
echo ====================================================
echo   完成！GitHub Pages 几分钟后更新
echo ====================================================
pause
