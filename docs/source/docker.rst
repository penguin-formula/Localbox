*****************
Docker Containers
*****************

Images
======

There are four images for the client. They are:

- ``loxclient-base``
- ``loxclient-dev``
- ``loxclient-pre``
- ``loxclient-manage``

The first image, ``loxclient-base`` contains the basic setup to execute the
client in a container. The three other images are built from this one.

The development images, ``loxclient-dev`` should be used to test the
development of the Client in a non persistent way. This is necessary because
every time the client gets executed it's starts from scratch, so there are no
previous files or sessions and everything needs to be configured from the
ground up. When this container stops, every file and configuration is lost.

For a persistent execution, the ``loxclient-pre`` image should be used. This
image uses the directory ``~/LoxClientFiles`` to keep any necessary files for
the client's execution and configuration, including the synchronized directory.

The management image may be used to execute anything process that needs the
Client's code. Currently, this image is only used to execute the ``make
translations script``.

Running Containers
==================

The base image, ``loxclient-base``, is never executed directly. To execute the
other three images, check the following sections.

The script ``LoxClient/docker/run.sh`` is used as a way to execute the images.

Development Image
-----------------

The development image only uses one external volume, which is
``/tmp/.X11-unix`` so it can use the X server.

The created container will have the same name as the image, ``loxclient-dev``.

Do execute the container do:

    ./run.sh dev

When adding a new repository, the user will be asked for a directory in which
the files will be synchronized. The file system displayed is the file system of
the container. Any directory may be picked, but it is recommended that the user
creates the repository in:

    ``/usr/app/dir``

Persistent Image
----------------

The persistent image uses same volume for the X server as the development image
and it also uses the directory on the user's home ``~/LoxClientFiles``. The
files in this directory contain the necessary configuration files for the
Client and the synchronized directory.

The configuration files are in ``~/LoxClientFiles/client_home``. The
synchronized directory is in ``~/LoxClientFiles/client_directory``. Note that
you may create files in the later directory and they will be synchronized by
the Client.

Decrypting files is a bit tricky for now and it is explained in section
decrypting_files_.

Do execute the container do:

    ./run.sh per

With this image, when adding a repository, the user will also be asked for a directory. The file system is also the container's file system, but the following directory:

    ``/usr/app/dir``

is mapped to the host directory:

``~/LoxClientFiles/client_directory``

This directory should be picked if you want the repository to b persistent.

Management Image
----------------

The management image for now is only used to make the translations. To do so
use the following:

    ./run.sh manage make translations

The translations will be in:

    LoxClient/sync/locale/

.. _decrypting_files:

Decrypting Files
================

To decrypt inside the docker start a bash section in them:

    sudo docker exec -it CONTAINER_NAME bash

The ``CONTAINER_NAME`` should be ``loxclient-dev`` or ``loxclient-pre``.

The command will start a bash section in container. The default directory will
be:

    /usr/app/LoxClient

To decrypt a file, for example, if that file is ``SubDir/file.txt.lox``, do:

    python -m sync /usr/app/dir/SubDir/file.txt.lox
