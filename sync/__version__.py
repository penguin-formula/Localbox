from subprocess import check_output

VERSION_STRING = '1.6.51'

try:
    git_version = check_output(['git', 'log']).split('\n')[0].split(' ')[1]
except:
    git_version = 'N/A'
