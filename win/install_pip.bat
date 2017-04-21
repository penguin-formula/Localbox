SET install_dir=%1

echo Installing dependencies...
CD %install_dir% 
python.exe get-pip.py
python.exe -m pip install psutil python-gnupg==0.3.8 pycrypto watchdog==0.8.3
python -m pip install -U --pre -f https://wxpython.org/Phoenix/snapshot-builds/ wxPython_Phoenix