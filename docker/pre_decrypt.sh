#!/bin/bash

# Get path from inside container
host_path=$(pwd)/LoxClientFile/client_directory
target_path=$(pwd)/LoxClientFile/client_directory/SomeDir/file.txt.lox

len=${#host_path}
cont_path=${target_path:len:105}

# Decrypt file
sudo docker exec \
    loxclient-dev bash -c \
    "python -m sync /usr/app/dir/$cont_path"
