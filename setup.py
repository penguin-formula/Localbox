import sys
import glob
import os
from platform import system
from setuptools import setup, find_packages
from setuptools.command.install import install as InstallCommand
import pip

try:
    from _winreg import *
except ImportError:
    print("this is not windows")

# tweak as necessary
version = sys.version[:3]
installpath = sys.prefix

regpath = "SOFTWARE\\Python\\Pythoncore\\%s\\" % (version)
installkey = "InstallPath"
pythonkey = "PythonPath"
pythonpath = "%s;%s\\Lib\\;%s\\DLLs\\" % (
    installpath, installpath, installpath
)


def RegisterPy():
    try:
        reg = OpenKey(HKEY_LOCAL_MACHINE, regpath)
    except EnvironmentError:
        try:
            reg = CreateKey(HKEY_LOCAL_MACHINE, regpath)
            SetValue(reg, installkey, REG_SZ, installpath)
            SetValue(reg, pythonkey, REG_SZ, pythonpath)
            CloseKey(reg)
        except:
            print("*** Unable to register!")
            return
        print("--- Python " + str(version) + " is now registered!")
        return
    if (QueryValue(reg, installkey) == installpath and
                QueryValue(reg, pythonkey) == pythonpath):
        CloseKey(reg)
        print("=== Python " + str(version) + " is already registered!")
        return
    CloseKey(reg)
    print("*** Unable to register!")
    print("*** You probably have another Python installation!")


try:
    RegisterPy()
except NameError:
    print("this is not windows")

data_files = [
    ('localbox', ['data/icon/localbox.ico',
                  'data/icon/localbox.png',
                  'data/x-localbox.xml']),
    ('localbox/images', glob.glob('data/images/*.*'))
]

if system() == 'Linux':
    data_files += [('/usr/share/applications/', ['data/localbox.desktop'])]

if system() == 'Windows' or system().startswith('CYGWIN'):
    data_files += [('gpg', ['libs/iconv.dll', 'libs/gpg.exe'])]

from sync.__version__ import VERSION_STRING

with open('requirements.txt') as f:
    required = f.read().splitlines()

class Install(InstallCommand):
    """ Customized setuptools install command which uses pip. """

    def run(self, *args, **kwargs):
        pip.main(['install', '-U', '-f', 'https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-18.04', 'wxPython'])
        InstallCommand.run(self, *args, **kwargs)


setup(
    name="LocalBoxSync",
    version=VERSION_STRING,
    description='Desktop Client for the LocalBox',
    packages=find_packages(),
    install_requires=required,
    data_files=data_files,
    # cmdclass={'install': Install},
    include_package_data=True,
    author="De Staat der Nederlanden",
    author_email="info@yourlocalbox.org",
    url="https://yourlocalbox.org",
)
