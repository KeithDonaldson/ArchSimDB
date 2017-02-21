4th Year Honours Project: ArchSimDB
=====================

This is the source code for my 4th Year Honours Project. 

## Quick Start

### Preface

These instructions are given for Linux systems only, and this software has only been tested on Linux systems. Python 3 is used throughout, and ArchSimDB will not work with Python 2.

### Pre-requisites

MongoDB is used as a database for ArchSimDB. To download MongoDB, follow the guide on the [MongoDB website](https://docs.mongodb.com/manual/administration/install-on-linux/) for your operating system. You will need to install `mongodb-org-server`. You must install `mongodb-org-server` instead of `mongodb-org` as ArchSimDB requires the mongo daemon included in the server version.

Some Linux distributions will come with Python `setuptools` pre-installed, however some do not. If your distro does not, gather it using `pip3 install setuptools` (you may need to `sudo`).

### Launching the web app

1. Clone the repository into a working directory using `git clone https://github.com/KeithDonaldson/ArchSimDB.git`
2. Move to the `ArchSimDB` folder and run the command `sudo python3 setup.py install`.
 
    Note: If you plan to edit the ArchSimDB source code often, it may be better to run `sudo python3 setup.py develop`. Otherwise, you will need to perform the setup after each source code change to guarantee updates.
    
    Note: If you don't have `sudo` access, add the `--user` argument to the end of the above commands.
3. Create a directory 
4. Run the command `python3 run.py` to start up the webapp.

The webapp should now be running locally, with the default address being [http://localhost:6543](http://localhost:6543).

## Tutorial

More in-depth explanation of the system will follow.
