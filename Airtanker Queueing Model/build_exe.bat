rmdir /s /q "Airtanker Queueing Model"
python setup2.py py2exe
rmdir /s /q build
rename dist "Airtanker Queueing Model"
cd "Airtanker Queueing Model"
rmdir /s /q Microsoft.VC90.CRT
pause >nul