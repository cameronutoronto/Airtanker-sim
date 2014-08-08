del C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\"Airtanker Queueing Model.py"
del C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\dist\"Airtanker Queueing Model.exe"
del "Airtanker Queueing Model.exe"
echo f | xcopy /s "queueing_gui.py" C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\"Airtanker Queueing Model.py"
cd C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller
python main.py --onefile --noconsole "Airtanker Queueing Model.py"
cd dist
echo f | xcopy /s "Airtanker Queueing Model.exe" C:\Users\Cam\Documents\"Airtanker Simulation Model"\"Airtanker Queueing Model"\"Airtanker Queueing Model.exe"
pause>nul