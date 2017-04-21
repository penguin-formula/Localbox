#!/bin/bash

# Get path from inside container
host_path=$(pwd)/LoxClientFiles/client_directory
target_path=$1

len=${#host_path}
cont_path=${target_path:len+1}

# Decrypt file
export SUDO_ASKPASS=/usr/bin/gksudo

echo sudo -A docker exec \
    loxclient-dev bash -c \
    \"python -m sync /usr/app/dir/$cont_path\" >> /tmp/AI
sudo -A docker exec \
    loxclient-dev bash -c \
    "python -m sync /usr/app/dir/$cont_path" >> /tmp/AI2 &> /tmp/AI2
