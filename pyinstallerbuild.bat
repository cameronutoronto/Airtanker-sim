del C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\"Airtanker Simulation Model.py"
del C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\dist\"Airtanker Simulation Model.exe"
del "Airtanker Simulation Model.exe"
echo f | xcopy /s "Airtanker_GUI.py" C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\"Airtanker Simulation Model.py"
cd C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller
python main.py --onefile --noconsole "Airtanker Simulation Model.py"
cd dist
echo f | xcopy /s "Airtanker Simulation Model.exe" C:\Users\Cam\Documents\"Airtanker Simulation Model"\"Airtanker Simulation Model.exe"
pause>nul