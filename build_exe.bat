rmdir /s /q "Airtanker Sim Model Dist"
python setup2.py py2exe
rmdir /s /q build
rename dist "Airtanker Sim Model Dist"
cd "Airtanker Sim Model Dist"
rmdir /s /q Microsoft.VC90.CRT
pause >nul