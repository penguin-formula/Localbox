#!/bin/bash

loxclient_default_per=~/LoxClientFiles

function runLoxClient {
    exec_mode=$1

    if [ $exec_mode = "dev" ]
    then
        # Is it persistent?
        getArg arg_value "-v" "${@:2}"
        has_volume=$?

        if [ $has_volume -eq 1 ]
        then
            # Is there an alternative directory for files
            getArg alt_per_dir "--dir" "${@:2}"
            is_alt_per_dir=$?

            if [ -z $arg_value ]
            then
                arg_value=$loxclient_default_per
            fi

            if [ ! -d "$arg_value" ]
            then
                mkdir -p $arg_value
                mkdir $arg_value/client_config
                mkdir $arg_value/client_gpg
                mkdir $arg_value/client_directory
            fi

            loxclient_args="\
                -v $arg_value/client_config:/root/.config/localbox \
                -v $arg_value/client_gpg:/root/.gnupg \
                -v $arg_value/client_directory:/usr/app/dir"
        else
            loxclient_args=""
        fi
    else
        echo todo
    fi

    # Setup command
    getArg cmd_arg "--cmd" "${@:2}"
    is_cmd_arg=$?

    # Grand access to X server to everyone
    xhost +

    if [ $is_cmd_arg -eq 0 ]
    then
        sudo docker run \
            -it \
            --rm \
            --name loxclient-$exec_mode \
            --net=host \
            $loxclient_args \
            -v /tmp/.X11-unix:/tmp/.X11-unix \
            -e DISPLAY=$DISPLAY \
            loxclient-$exec_mode
    elif [ $is_cmd_arg -eq 1 ]
    then
        sudo docker exec \
            -it \
            loxclient-$exec_mode \
            $cmd_arg
    fi
}

function getArg {
    local ret_value=$1
    arg_name=$2
    shift
    shift

    while [[ $# -gt 0 ]]
    do
        arg="$1"

        if [ $arg = $arg_name ]
        then
            echo $2
            eval $ret_value="'$2'"
            return 1
        fi

        shift # past argument or value
    done

    ret_value=""
    return 0
}

exec_mode=$1
runLoxClient $exec_mode "${@:2}"
