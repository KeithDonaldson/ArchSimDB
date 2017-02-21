import argparse
import configparser
import subprocess
import atexit
import time
import os.path


def set_config(args):
    """
    Validate the program arguments and set them in the .ini file

    :param args: The arguments given to the program
    :type args: Namespace

    :return: None
    """

    print(">> Checking and setting arguments provided")
    config.read_file(open('development.ini'))

    # - Validate and set Statfile Filepath
    if os.path.exists(args.filespath[0]):
        config.set('app:config', 'filespath', os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                                           args.filespath[0]))
    else:
        print(">! ERROR: Given filepath " + args.filespath[0] + " does not exist.")
        print(">> Exiting, failed to run.")
        exit()

    # - Set Mongouri
    if args.mongo_uri[0][-1] != '/':
        config.set('app:main', 'mongo_uri', args.mongo_uri[0] + '/' + args.dbname[0])
    else:
        config.set('app:main', 'mongo_uri', args.mongo_uri[0] + args.dbname[0])

    # - Set Port
    config.set('server:main', 'port', str(args.port[0]))

    # - Write the ini file
    with open('development.ini', 'w') as config_file:
        config.write(config_file)

    print(">> Arguments valid and successfully set")


def start_processes(args):
    """
    Create and start all processes required for ArchSimDB to run

    :param args: The arguments given to the program
    :type args: Namespace

    :return: None
    """

    processes = []
    atexit.register(end_processes, processes)
    skip = None

    # - Create mongod process
    print("-" * 30)
    print(">> Attempting to start mongod on dbpath " + args.dbpath[0])
    p_mongod = subprocess.Popen(['mongod', '--dbpath', args.dbpath[0]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(2)

    if p_mongod.returncode is None:              # Program hasn't returned
        pass
    else:                                        # Program has failed to run
        p_mongod_stdout, p_mongod_stderr = p_mongod.communicate()[:2]
        print_error('mongod', p_mongod_stdout, p_mongod_stderr)
        skip = input(">> If this error was because mongo if already running, press [y] to skip. Otherwise, "
                     "press [n] to exit.\n")

        while skip not in ('y', 'n'):
            skip = input(">> If this error was because mongo if already running, press [y] to skip. Otherwise, "
                         "press [n] to exit.\n")
        if skip == 'n':
            print(">> Exiting, failed to run.")
            exit()

    processes.append(['mongod', p_mongod])
    print(">> mongod started successfully (pid: " + str(p_mongod.pid) + ")")

    # - Create pserve process
    print("-" * 30)
    print(">> Attempting to start pserve")
    p_pserve = subprocess.Popen(['pserve', '--reload', 'development.ini'])
    time.sleep(2)

    if p_pserve.returncode is None:              # Program hasn't returned
        pass
    else:                                        # Program has failed to run
        p_pserve_stdout, p_pserve_stderr = p_pserve.communicate()[:2]
        print_error('pserve', p_pserve_stdout, p_pserve_stderr)

    processes.append(['pserve', p_pserve])
    print(">> NOTE: pserve reloads automatically whenever it encounters an error (unless fatal) or a file change. If "
          "you see an error above, the web app may not have launched successfully but pserve still is still running.")
    print(">> pserve started successfully (pid: " + str(p_pserve.pid) + ")")

    # - At this point, all processes should be running
    print("-" * 30)
    print(">> Processes started successfully, ArchSimDB is now be available at http://localhost:" + str(args.port[0]))
    if skip:
        print(">> If the website doesn't load due to a timeout, it is likely because you skipped the mongod setup. The "
              "website will not load without the correctly setup mongod process running.")

    p_pserve.communicate()                       # Wait for pserve completion


def end_processes(processes):
    """
    Terminates active processes on program exit

    :param processes: A list of all processes created in this program
    :type processes: list

    :return: None
    """

    print(">> Closing alive processes")
    for name, p in processes:
        p.communicate()

        try:
            p.kill()
            print(">> Killed " + name + " (pid: " + str(p.pid) + ")")
        except OSError:
            print(">> Could not kill " + name + ". It may have already been terminated.")
            pass

    print(">> Exiting")


def print_error(process_name, stdout, stderr):
    """
    Prints an error message on a process failing to run

    :param process_name: The name of the failed process
    :type process_name: str

    :param stdout: The stdout buffer of the failed process
    :type stdout: BufferedReader

    :param stdout: The stderr buffer of the failed process
    :type stdout: BufferedReader

    :return: None
    """

    print(">! ERROR")
    print("- STDOUT START -")
    print(stdout)
    print(" - STDOUT END -")
    print(">! ERROR: Could not start " + process_name + " process, please see above trace.")


if __name__ == '__main__':

    config = configparser.ConfigParser()
    parser = argparse.ArgumentParser(description='Run ArchSimDB')

    parser.add_argument('--dbpath', dest='dbpath', type=str, nargs=1, default=['db/'],
                        help='The absolute path to be used as the mongodb directory. If this is a first time '
                             'setup, you will need to create an empty directory first for the mongo database. '
                             '(Default: %(default)s. Type: %(type)s)')
    parser.add_argument('--dbname', dest='dbname', type=str, nargs=1, default=['archsimdb'],
                        help='The name of your mongodb database to connect to. If one does not exist, it will be'
                             'created with this name. (Default: %(default)s. Type: %(type)s)')
    parser.add_argument('--filespath', dest='filespath', type=str, nargs=1, default=['statfiles/'],
                        help='The absolute path to a directory containing experiment directories. That is, the '
                             'directory in which there is a structure of `experiments/configurations/statfiles*` '
                             'within. (Default: %(default)s. Type: %(type)s)')
    parser.add_argument('--mongouri', dest='mongo_uri', type=str, nargs=1, default=['mongodb://localhost:27017/'],
                        help='The uri that your mongo daemon is to run on. (Default: %(default)s. Type: %(type)s)')
    parser.add_argument('--port', dest='port', type=int, nargs=1, default=[6543], required=False,
                        help='The port on localhost which ArchSimDB will run on. '
                             '(Default: %(default)s. Type: %(type)s)')

    arguments = parser.parse_args()

    set_config(arguments)
    start_processes(arguments)
