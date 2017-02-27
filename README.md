4th Year Honours Project: ArchSimDB
=====================

This is the source code for my 4th Year Honours Project. 

## Quick Start

### Preface

These instructions are given for Linux systems only, and this software has only been tested on Linux systems. Python 3 is used throughout, and ArchSimDB will not work with Python 2.

### Pre-requisites

MongoDB is used as a database for ArchSimDB. To download MongoDB, follow the guide on the [MongoDB website](https://docs.mongodb.com/manual/administration/install-on-linux/) for your operating system. It may be as simple as `dnf install mongodb-org-server`. You must install `mongodb-org-server` instead of `mongodb-org` as ArchSimDB requires the mongo daemon included in the server version.

### Launching the web app

1. Clone the repository into a working directory using `git clone https://github.com/KeithDonaldson/ArchSimDB.git`
2. Move to the `ArchSimDB` folder and run the command `python3 run.py --setup True`. This should take care of everything.

The webapp should now be running locally, with the default address being [http://localhost:6543](http://localhost:6543).

## Troubleshooting

### Launching the web app

If the `run.py` script is giving you trouble, it is likely encountering an unexpected issue. In setup mode, the script performs the following tasks in this order, with non-setup mode skipping steps 1-4:

1. Attempts to create the directory at the path given by the --dbpath argument (default: 'db/') by running `os.mkdir({'db/'})`.
2. Attempts to create the virtual environment at the path given by the --envpath argument (default: 'env/') by running `python3 -m venv {env/}`.
3. Attempts to install `setuptools` by running `pip3 install setuptools`.
4. Attempts to install all Python dependencies by running `pip3 install -e .`.
5. Attempts to start a mongod process with `--dbpath` given by the --dbpath argument (default: 'db/') by running `mongod --dbpath {db/}`. 
6. Attempts to start a pserve process by running `pserve --reload development.ini`.

Steps 3, 4, and 6 are run with respect to the virtual environment created, and as such you should never require super user permissions.

Step 5 is the only process that runs externally from this project, and as such is where the problems are likely to occur. Common errors are that the process is already running (i.e. you have a mongod instance already) or that your --dbpath directory doesn't exist (will only happen if step 1 encountered an error and you skipped). 

As a last resort, you can run the commands listed above (steps 1-6) manually from the command line. Note that steps 3, 4, and 6 will need to start with your virtual environment `bin` path, e.g. `pserve --reload development.ini` becomes `env/bin/pserve --reload development.ini` and `pip3 install setuptools` becomes `env/bin/pip3 install setuptools`.

Other issues? Contact me at contact@keithdonaldson.co.uk.

