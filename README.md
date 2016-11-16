4th Year Honours Project: ArchSimDB
=====================

This is the source code for my 4th Year Honours Project. 

## Quick Start

### Pre-requisites and Preface

Before getting started, make sure that you have **MongoDB** running as this will be the database for the web app. You can do this by typing `mongod` on the terminal after installing MongoDB. These instructions are given for Linux systems only, and this software has only been tested on Linux systems.

### Launching the web app

1. Clone the repository into a working directory.
2. In the `src` folder, run the command `sudo python3 setup.py develop`. This will prepare the files for Pyramid.
3. Download all of the python dependencies which weren't collected from step 2. These can all be collected through `pip`.

  ```
  $ sudo pip3 install pymongo
  $ sudo pip3 install pyramid_jinja2
  ```

4. Run the command `pserve development.ini --reload` to start up the webapp. If you get any `ImportError`s, attempt to install the package with `pip`.

The webapp should now be running locally, with the default port being http://localhost:6543. Assuming you have a working copy of the database, you should see something like this:

![Website Screenshot](http://puu.sh/rVDbU/a69b553947.png "Website Screenshot")

If you have an empty database, or one with a different schema to ArchSimDB, you'll likely get empty data here.

## Uploading a statfile

Currently the only accepted statfiles are ones generated from the Flexus simulator. To upload a file:

1. Go to http://localhost:6543/upload
2. Click on the 'Browse...' button and choose a Flexus statfile.
3. Click 'submit'
4. You should receive a confirmation page with a snippet of the inserted data in JSON format and the ObjectID.

## Tutorial

More in-depth explanation of the system will follow.
