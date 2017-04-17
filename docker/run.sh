#!/bin/bash

loxclient_default_per=~/LoxClientFiles

function runLoxClient {
    exec_mode=$1

    cd ..

    if [ $exec_mode = "dev" ]; then
        sudo docker run \
            -it \
            --rm \
            --name loxclient-dev \
            --net=host \
            -u $(awk "BEGIN { printf \"%d:%d\", $(id -u), $(id -g) }") \
            -v $(pwd)/../LoxClient:/usr/app/LoxClient \
            -v /tmp/.X11-unix:/tmp/.X11-unix \
            -e DISPLAY=$DISPLAY \
            loxclient-dev
    elif [ $exec_mode = "pre" ]; then
        # Assure these directories exist
        mkdir -p /home/pedro/LoxClientFiles/client_home/.config/localbox
        mkdir -p /home/pedro/LoxClientFiles/client_directory

        sudo docker run \
            -it \
            --rm \
            --name loxclient-pre \
            --net=host \
            -u $(awk "BEGIN { printf \"%d:%d\", $(id -u), $(id -g) }") \
            -v $(pwd)/../LoxClient:/usr/app/LoxClient \
            -v $loxclient_default_per/client_home:/home/containeruser \
            -v $loxclient_default_per/client_directory:/usr/app/dir \
            -v /tmp/.X11-unix:/tmp/.X11-unix \
            -e DISPLAY=$DISPLAY \
            loxclient-pre
    elif [ $exec_mode = "manage"  ]; then
        sudo docker run \
            -it \
            --rm \
            --name loxclient-manage \
            --net=host \
            -u $(awk "BEGIN { printf \"%d:%d\", $(id -u), $(id -g) }") \
            -v $(pwd)/../LoxClient:/usr/app/LoxClient \
            -v /tmp/.X11-unix:/tmp/.X11-unix \
            -e DISPLAY=$DISPLAY \
            loxclient-manage "${@:2}"
    fi

    cd docker
}

exec_mode=$1
runLoxClient $exec_mode "${@:2}"
