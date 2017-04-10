#!/bin/bash

sudo docker build -t loxclient-base -f loxclient-base.docker ../..
sudo docker build -t loxclient-dev -f loxclient-dev.docker ../..
