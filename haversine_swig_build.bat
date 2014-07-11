del C:\Python27\ArcGIS10.2\Lib\site-packages\haversine.py
del C:\Python27\ArcGIS10.2\Lib\site-packages\haversine.pyc
del C:\Python27\ArcGIS10.2\Lib\site-packages\_haversine.pyd
del C:\Python27\ArcGIS10.2\Lib\site-packages\haversine-1.0-py2.7.egg-info
cd C:\Users\Cam\Documents\"Airtanker Simulation Model"
swig -python "haversine.i"
python setup_haversine.py install build --compiler=mingw32
rmdir /s /q build
del haversine.py
del "haversine_wrap.c"
del haversine.pyc
pause >nul