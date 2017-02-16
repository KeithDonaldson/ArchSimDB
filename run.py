import argparse
import configparser
import subprocess
import atexit
import time


if __name__ == '__main__':
    """
    Provides a single interface to launch ArchSimDB.
    """
    config = configparser.ConfigParser()
    parser = argparse.ArgumentParser(description='Run ArchSimDB',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('dbpath', type=str, nargs=1,
                        help='The absolute path to be used as the mongodb directory. If this is a first time '
                             'setup, you will need to create an empty directory first for the mongo database.')
    parser.add_argument('dbname', type=str, nargs=1,
                        help='The name of your mongodb database to connect to. If one does not exist, it will be'
                             'created with this name.')
    parser.add_argument('filespath', type=str, nargs=1,
                        help='The absolute path to a directory containing experiment directories. That is, the '
                             'directory in which there is a structure of `experiments/configurations/statfiles*` '
                             'within.')
    parser.add_argument('--mongouri', dest='mongo_uri', type=str, nargs=1, default=['mongodb://localhost:27017/'],
                        help='The uri that your mongo daemon is to run on.')
    parser.add_argument('--port', dest='port', type=int, nargs=1, default=[6543], required=False,
                        help='The port on localhost which ArchSimDB will run on.')

    args = parser.parse_args()

    config.read_file(open('development.ini'))
    config.set('app:config', 'filespath', args.filespath[0])

    if args.mongo_uri[0][-1] != '/':
        config.set('app:main', 'mongo_uri', args.mongo_uri[0] + '/' + args.dbname[0])
    else:
        config.set('app:main', 'mongo_uri', args.mongo_uri[0] + args.dbname[0])

    config.set('server:main', 'port', str(args.port[0]))

    with open('development.ini', 'w') as config_file:
        config.write(config_file)

    processes = []

    try:
        print("> Attempting to start mongod on dbpath " + args.dbpath[0])
        p_mongo = subprocess.Popen(['mongod', '--dbpath', args.dbpath[0]])
    except subprocess.CalledProcessError as e:
        print(e.output)
        print("-"*30)
        print("! ERROR: Could not start mongod process, please see above error trace.")

    print(p_mongo.poll())

    # time.sleep(1)
    # processes.append(p_mongo)
    # print("> Mongod started successfully")
    #
    # try:
    #     print("> Attempting to start web app")
    #     p_pserve = subprocess.Popen(['pserve', '--reload', 'development.ini'])
    # except subprocess.CalledProcessError as e:
    #     print("We fucked")
    #
    # processes.append(p_pserve)
    # time.sleep(1)

