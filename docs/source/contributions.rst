Contributions
*************

NOTE: This guide has some instructions that are specific to our current development specs (Ubuntu 16.04).

Setup development environment
=============================

Hard Way
--------

.. code:: bash

    # install virtualenv

    # get the code
    git clone https://github.com/yourlocalbox/LinWin-PySync.git
    # switch to the develop branch
    git checkout develop
    # compile the translations
    make translations


Easy Way
--------

Comming soon!


Start Contributing
==================

There are two kinds of LocalBox contributors: internal and external. The internal contributors are the developers in the
LocalBox team.

External Contributions
----------------------

LocalBox has 4 repositories hosted here: https://github.com/yourlocalbox, fork one of them:

.. image:: ../_static/fork.jpg

Then clone it (``git clone``).

.. image:: ../_static/clone.jpg

Do your git setup:

.. code:: bash

    git config --global user.name "Your Name"
    git config --global user.email your@mail.info

You should do your development based on the ``develop`` branch, so first checkout this branch:

.. code:: bash

    git checkout develop

It's a good idea to keep track of the upstream project, because unless you are doing a very quick fix chances are that
there is new code in the upstream project and your new code has to work with it in order to be merged.

Start by configuring the upstream project:

.. code:: bash

    git remote add --track develop upstream https://github.com/yourlocalbox/LinWin-PySync.git

To update your code use

.. code:: bash

    git fetch upstream
    git merge upstream/develop

When you are done with your development and testing you can create a **Pull request** to merge your changes into the
main repository. Make sure to select the ``develop`` branch.

.. image:: ../_static/pull_request.jpg

Someone from the LocalBox development team will review your code and merge it.

Internal Contributions
----------------------

We develop LocalBox based on the `Vincent Driessen <http://nvie.com/posts/a-successful-git-branching-model/>`_
branching model with the help of
`git flow <http://danielkummer.github.io/git-flow-cheatsheet/>`_.
Start by installing git flow (see :ref:`Git Flow`)

Solving a bug? Create your branch with (replace <ISSUE_NUMBER> with the appropriate number):

.. code:: bash

    git flow bugfix start LOXGUI-<ISSUE_NUMBER>

Creating a new feature ? Create your branch with (replace <ISSUE_NUMBER> with the appropriate number):

.. code:: bash

    git flow feature start LOXGUI-<ISSUE_NUMBER>


Development Dependencies
========================

Git Flow
--------

.. code:: bash

    sudo apt-get install git-flow

WxPython
--------

To install ``wx`` via ``pip`` you need to install:

.. code:: bash

    sudo apt-get install dpkg-dev build-essential python2.7-dev libwebkitgtk-dev libjpeg-dev libtiff-dev libgtk2.0-dev libsdl1.2-dev libgstreamer-plugins-base0.10-dev libnotify-dev freeglut3 freeglut3-dev -y

Translations
------------

To run ``make translations`` you need ``msgfmt.py`` in your path. It can be found in the Debian packages
``python2.7-examples`` or ``python3.5-examples``:

Python 2.7

.. code:: bash

    sudo apt-get install python2.7-examples

Python 3.5

.. code:: bash

    sudo apt-get install python3.5-examples

Then you need to make ``msgfmt.py`` available in your ``$PATH``.

.. code:: bash

    [ ! -d ~/bin ] && mkdir ~/bin
    # Python 2.7
    ln -s /usr/share/doc/python2.7/examples/Tools/i18n/msgfmt.py ~/bin/msgfmt.py
    # Python 3.5
    ln -s /usr/share/doc/python3.5/examples/i18n/msgfmt.py ~/bin/msgfmt.py

Documentation
=============

Want to contribute your knowledge to the cause? Cool.

.. code:: bash

    # install dia (to export the diagrams)
    sudo apt-get install dia -y

    # get the code
    git clone https://github.com/yourlocalbox/LinWin-PySync.git

    mkdir LinWin-PySync-docs
    cd LinWin-PySync-docs

    # clone the repo into a dir called html:
    git clone https://github.com/yourlocalbox/LinWin-PySync.git html
    cd html

    #
    git checkout gh-pages
    git symbolic-ref HEAD refs/heads/gh-pages
    rm .git/index
    git clean -fdx

    # compile the documentation as HTML
    cd ../LinWin-PySync
    make html

Reference: https://daler.github.io/sphinxdoc-test/includeme.html



Translations
============

Creating a new translation
--------------------------

Install Poedit

.. code:: bash

    sudo apt-get install poedit

Create POT file:

.. code:: bash

    make translatefile

Create translation from POT:

.. image:: ../_static/create_translation.*

Open POT:

.. image:: ../_static/open_pot.*

Choose language:

.. image:: ../_static/pot_choose_language.*

Translate the text and save PO in ``./translations``:

.. image:: ../_static/translations_save_po.*

Compile to MO:

.. code:: bash

    make translations


Updating a translation
----------------------

Lets contemplate the scenario where the developers added more strings / messages to the application. Now we need to
make a translation for these new strings.


Create POT file again:

.. code:: bash

    make translatefile

Open your previous PO file (located in ``./translations``) and update it from the new POT.

.. image:: ../_static/translations_update_from_pot.*

The new strings are added to the PO file. Translate them, save and compile:

.. code:: bash

    make translations


Adding translation to the application
-------------------------------------

So your PO file is ready to use, but how?

Add the name of the language in upper case (it should match ``[A-Z_]+``) as the key of ``LANGUAGES`` and use the name of
the PO file (without the extension) as the value:

.. image:: ../_static/translations_language_py.*

After restarting the application the new language is displayed as a choice:

.. image:: ../_static/translations_app.*


Testing on Windows
==================

You can download a free VirtualBox machine from here: https://developer.microsoft.com/en-us/microsoft-edge/tools/vms/


Merge from public repository
============================

.. code:: bash

    cd path/to/private/project/
    git remote add public-project-1 public-project-remote-url
    git fetch public-project-1
    git merge public-project-1/develop  # <--- branch to merge
    git remote remove public-project-1


Example
-------

.. code:: bash

    cd ~/github/LocalBox/LinWin-PySync
    git remote add LinWin https://github.com/yourlocalbox/LinWin-PySync.git
    git merge LinWin/develop
    git remote remove LinWin
    git push