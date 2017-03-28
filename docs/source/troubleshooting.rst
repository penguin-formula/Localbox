***************
Troubleshooting
***************

GPG hangs when generating a key?
================================

Problem: When you are configuring a new LocalBox, after the last step (creation of the passphrase) the application
hangs and in the logs you see the message ``public keys not found. generating...``.

Solution: This happens because of low entropy. One way to fix this is to install ``sudo apt-get install rng-tools``.

.. code:: bash

    sudo apt-get install rng-tools

Just after installing ``rng-tools`` the application will unlock. If it locks again do:

.. code:: bash

    sudo killall rngd
    sudo rngd -r /dev/urandom

Note: This only happened on a Linux Virtual Machine.

References: https://delightlylinux.wordpress.com/2015/07/01/is-gpg-hanging-when-generating-a-key/


No systray icon on Ubuntu
=========================

Problem: You're running LocalBox sync client on Ubuntu (Unity Desktop Environment), it seems to be running fine
but you cannot see it on the system tray.

Solution: Ubuntu does not have a conventional system tray. You can add this functionality by installing
Indicator Systemtray Unity:

.. code:: bash

    sudo apt-add-repository ppa:fixnix/indicator-systemtray-unity -y && sudo apt-get update && sudo apt-get install indicator-systemtray-unity -y

.. image:: ../_static/troubleshooting_ubuntu_systray.jpg