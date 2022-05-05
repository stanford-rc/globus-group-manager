Installation
============

This program can be installed and run in multiple ways. 

Virtualenv
----------

To install from a Python virtual environment, download a repository export to a
local directory, create a venv, and install the code into that venv.

.. code-block:: shell

   python3.9 -m venv .
   . bin/activate
   pip install --upgrade pip
   pip install .

As long as the venv is active in your shell, the ``sggm`` command will be
available.

In this situation, we suggest using a dotenv file to store configuration.

.. warning:: Use caution when working from a Git worktree (that is, the result of a ``git clone``.  Running in a Git worktree introduces the possibility of running unexpected code, or committing secrets.
