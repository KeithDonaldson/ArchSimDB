4th Year Honours Project: ArchSimDB
=====================

This is the source code for ArchSimDB. ArchSimDB is a tool designed for Computer Architects that allows them to take raw simulator output files -- specfically Flexus at this time -- and compare and visuliase this data easily. The aim of the project is to create a tool that will significantly cut down the amount of time (and potentially errors) currently involved in taking large amounts of raw data and comparing it with other raw data.

**Note**: All following instructions are given for *nix systems only as this software has only been tested on *nix systems. Python 3 is used throughout, and ArchSimDB will not work with Python 2.

## Download and Installing ArchSimDB

### Pre-requisites

MongoDB is used as a database for ArchSimDB. To install MongoDB, it may be as simple as using your operating sytem's default package manager, i.e. `dnf/apt-get/brew install mongodb-org-server`, but if not you can follow the guide on the [MongoDB website](https://docs.mongodb.com/manual/administration/install-on-linux/) for your operating system. You must install `mongodb-org-server`, not `mongodb-org`.

Python 3 is also a requirement, although many *nix systems come pre-packaged with this.

### Launching the web app

1. Clone the repository into a working directory using `git clone https://github.com/KeithDonaldson/ArchSimDB.git`
2. Move to the `ArchSimDB` folder and run the command `python3 run.py {user} --setup True`, replacing `{user}` with a user in the statfiles directory. Out of the box, you can choose from either `user1` or `user2`, i.e. `python3 run.py user1 --setup True`. This command should take care of everything.

The webapp should now be running locally, with the default address being [http://localhost:6543](http://localhost:6543). If you get an error during setup, consult the Troubleshooting section.

It is thoroughly recommended to run `python3 run.py -h` to look at all of the arguments you can provide to the system. These could help integrate ArchSimDB into your existing workspace.

To stop the web app, stop the process with CTRL+C on the command line or by using `kill {pid}`. The script will take care of ending subprocesses.

## Using ArchSimDB

### Setting up the Raw Data Directory

**Note**: You needn't set up a directory if you are just testing ArchSimDB, as by default it takes data from the example directory at `~/statfiles/`. You can use this example directory as a reference.

The only real setup required for ArchSimDB to work is to have a directory of raw data in the format it expects. The following will explain how to set up a directory correctly. Let's assume you call this directory `data`.

At the top level of your `data` directory is a directory for every user of the system. The most likely scenario is that you only have one directory here for your own raw data. Example: `/data/keithdonaldson/`

At the second level is a directory for every experiment in the system. An Experiment may be something like 'Testing different cache replacement policies on x86 processors'. These are only directories (i.e. used as metadata in the system) and there should be no files at this level. Example: `/data/keithdonaldson/x86-replacement-policies/`

At the third level is a directory for every configuration of a given experiment. A configuration might be 'LRU 64MB Cache' for the example experiment given above. Once again, it is only a directory (i.e. metadata) and there should be no files at this level. Example: `/data/keithdonaldson/x86-replacement-policies/64MB-LRU/`

Finally, the fourth level are all of the raw statfiles for a given configuration. These are called 'applications' in ArchSimDB. Example:  `/data/keithdonaldson/x86-replacement-policies/64MB-LRU/perlbench-40B1.stat`

The expected directory structure is: `{Users}/{Experiments}/{Configurations}/{Applications/Raw statfiles}`

ArchSimDB takes these raw statfiles and parses and stores the data in a database. If you leave all `run.py` settings as default and choose `user1`, the source files used by ArchSimDB will reside at `~/statfiles/user1/`. You can use your own statfile path by providing `run.py` with a `--filespath` argument.

### Syncing

Upon first launching the web app, you should see a page displaying the amount of experiments, configurations, and applications (statfiles) in the database. These should all be zero on first launch. To sync the database with the chosen statfile directory, navigate to the 'Sync' page and click the 'Sync' button. This may take a few seconds or minutes, depending on how large the data set is. The database should now be filled with all sucessfully parsed statfile data. It is worth looking at the logs to check for any files that failed to parse or be recognised.

**Note**: ArchSimDB keeps track of files in your raw data directory with a file called `.archsimdb_tracking_data` at the user root, i.e. `~/statfiles/user1/.archsimdb_tracking_data`. You shouldn't need to touch this, but if you find that your database and raw data aren't synced properly, it may be worth deleting this file and re-syncing _or_ going to the 'Delete' page.

### Viewing Data

You can look at the data in the database from the pages within the 'Search Database' category in the navigation menu. All of the 'List of...' pages just show metadata. Actual parsed statfile data can be viewed by going to the 'View Database' page and selecting an application. The table allows sorting and searching.

### Comparing Data

You can compare data from multiple applications by first going to the 'Compare' page.

You should see a tree-view of the data in the database. Here you can select all of the applications that you wish to compare data from. It is generally expected that you choose the same workloads/benchmarks over multiple configurations, e.g. choosing the 'perlbench-40B1' and 'GemsFTD-40B1' applications from x different configurations*. Any combination of applications here will work, though. Click the 'Submit These Applications' button.

A list of all possible fields/stats from the chosen applications will be displayed, including any [composite stats](#composite-stats) which are signified with a `$` at the beginning. Choose some by clicking the arrows to send across to the 'Chosen Fields' box. You can multiselect and search here. Click the 'Submit Fields and Compare' button and wait. This may take a while depending on the number of fields/applications chosen.
 
*Comparisons are made on applications with the same filename by default, so 'perlbench-40B1.stat' will be compared with any other chosen applications called 'perlbench-40B1.stat'. If this doesn't work with your naming scheme, you can define a separator with the argument `--workloadseparator` at runtime to split the filename. So if your filenames are in the form `workload-cycles-timstamp.stat`, for example, you can define `--workloadseparator` as `-` which would mean comparisons happen on `workload` and not the full filename.

### Deleting

You can delete the data from the database by going to the 'Delete' page and clicking the 'Delete' button. This deletes all data in the database and the tracking file.

### Composite Stats

## Troubleshooting


### Understanding the Database

MongoDB is a No-SQL solution, and as such all of the database contents are stored in a directory (default: `~/db/`). Each user has it's own database and as such you can switch between users freely without losing the data. Moreover, you are free to delete the raw statfiles as by default ArchSimDB will not update it's database to reflect deleted files. Should you wish to delete entries, see the [Deleting](#deleting) section for more information.

### Launching the web app

If the `run.py` script is giving you trouble, it is likely encountering an unexpected issue. In setup mode, the script performs the following tasks in this order, with non-setup mode skipping steps 1-4:

1. Attempts to create the directory at the path given by the --dbpath argument (default: 'db/') by running `mkdir({'db/'})`.
2. Attempts to create the virtual environment at the path given by the --envpath argument (default: 'env/') by running `python3 -m venv {env/}`.
3. Attempts to install `setuptools` by running `pip3 install setuptools`.
4. Attempts to install all Python dependencies by running `pip3 install -e .`.
5. Attempts to start a mongod process with `--dbpath` given by the --dbpath argument (default: 'db/') by running `mongod --dbpath {db/}`. 
6. Attempts to start a pserve process by running `pserve --reload development.ini`.

Steps 3, 4, and 6 are run with respect to the virtual environment created, and as such you should never require super user permissions.

Step 5 is the only process that runs externally from this project, and as such is where the problems are likely to occur. Common errors are that the process is already running (i.e. you have a mongod instance already) or that your --dbpath directory doesn't exist (will only happen if step 1 encountered an error and you skipped). 

As a last resort, you can run the commands listed above (steps 1-6) manually from the command line. Note that steps 3, 4, and 6 will need to start with your virtual environment `bin` path, e.g. `pserve --reload development.ini` becomes `env/bin/pserve --reload development.ini` and `pip3 install setuptools` becomes `env/bin/pip3 install setuptools`.

Other issues? Contact me at contact@keithdonaldson.co.uk.

