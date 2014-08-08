del C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\"Erlang Airtanker Queueing Model.py"
del C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\dist\"Erlang Airtanker Queueing Model.exe"
del "Erlang Airtanker Queueing Model.exe"
echo f | xcopy /s "queueing_gui_b.py" C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller\"Erlang Airtanker Queueing Model.py"
cd C:\Users\Cam\Downloads\PyInstaller-2.1\PyInstaller-2.1\Pyinstaller
python main.py --onefile "Erlang Airtanker Queueing Model.py"
cd dist
echo f | xcopy /s "Erlang Airtanker Queueing Model.exe" C:\Users\Cam\Documents\"Airtanker Simulation Model"\"Airtanker Queueing Model - B"\"Erlang Airtanker Queueing Model.exe"
pause>nul