import os
import hashlib
import re
from datetime import datetime
from .reader import Reader
from .dbaccess import DatabaseActions
import configparser
import logging


class Scanner:
    """
    Provides functionality to scan through a directory, reading and writing
    files within that directory, and preparing the read data for upload.

    Attributes:
        reader: An instance of the Reader class
        db_actions: An instance of the DatabaseActions class
        statfile_metadata: A dictionary to store metadata from a given statfile
        checksums: A dictionary of checksums (md5 hashes) for the statfiles found
        list_of_all_statfile_data: A list containing the parsed statfile data for all sucessfully parsed files found
        failed_to_parse_statfiles: A list containing the names of any statfiles that failed to parse
        logs: A list containing the logs generated from the scanning process
    """

    def __init__(self):
        self.reader = Reader()
        self.db_actions = DatabaseActions()
        self.statfile_metadata = {}
        self.checksums = {}
        self.list_of_all_statfile_data = []
        self.failed_to_parse_statfiles = []
        self.logs = []

        config = configparser.ConfigParser()
        config.read_file(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'development.ini')))

        self.working_path = config.get('app:config', 'filespath')

        if self.working_path[-1] == '/':
            self.working_path = self.working_path[:-1]

    def scanner(self):
        """
        Walks through a directory and finds all statfiles and ArchSimDB files. Checks against the
        `.archsimdb_tracking_data` file to determine whether found files are new, changed, or
        unchanged and takes the necessary action.

        :return: A dictionary containing all of the parsed statfile data and logs
        :rtype: dict
        """

        initiated = False
    
        for dirpath, dirnames, filenames in os.walk(self.working_path):

            # On the first pass, read all of the known statfiles and their respective checksums from the
            # `.archsimdb_tracking_data` file, and write a new tracking file.

            if not initiated:
                self.statfile_metadata['_sim_owner'] = dirpath.split('/')[-1]
                meta_filepath = dirpath + '/.archsimdb_tracking_data'
                try:
                    meta_file = open(meta_filepath, 'r')
                    if os.stat(meta_filepath).st_size != 0:
                        data = [line.strip().split() for line in meta_file.readlines()[6:]]
                        self.checksums = {file: checksum for (file, checksum) in data}
                    meta_file.close()
                except FileNotFoundError:
                    pass
                meta_file = open(meta_filepath, 'w+')

                meta_file.write("# DO NOT TOUCH THIS FILE!\n"
                                "# This file contains the statfiles known to ArchSimDB and\n"
                                "# should not be edited. Statfiles are hashed and any changes\n"
                                "# will be automatically tracked.\n"
                                "# Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")

                initiated = True

            # For every statfile found, determine whether it is new, changed, or unchanged. This is done by md5 hasing
            # the statfile and comparing it against the `checksums` dictionary. If it is new or changed, the file is
            # handed over to the `prepare_input` method.
    
            for file in filenames:
                if not file.startswith(".archsimdb"):
                    filepath = os.path.join(dirpath, file)
                    relative_filepath = os.path.relpath(filepath, self.working_path)
                    statfile = open(filepath, 'rb')

                    if self.working_path.split('/') != filepath.split('/')[:-3]:
                        self.logs.append("Found a file not in the correct directory path "
                                         "(i.e. not in user/experiment/configuration/) at " + filepath)
                        continue  # The file is not of the form working_path/experiment/configuration, abort

                    if relative_filepath not in self.checksums:  # New file
                        self.logs.append("Found new file at " + filepath)
                        self.prepare_input(filepath)
                        if filepath not in self.failed_to_parse_statfiles:
                            meta_file.write(relative_filepath + " " + self.hashfile(statfile, hashlib.md5()) + "\n")
                    elif self.checksums.get(relative_filepath) != self.hashfile(statfile, hashlib.md5()):  # Changed
                        self.logs.append("Found changed file at " + filepath)
                        self.prepare_input(filepath)
                        if filepath not in self.failed_to_parse_statfiles:
                            meta_file.write(relative_filepath + " " + self.hashfile(statfile, hashlib.md5()) + "\n")
                    else:                        # Unchanged file
                        meta_file.write(relative_filepath + " " + self.checksums.get(relative_filepath) + "\n")
                        self.logs.append("Found unchanged file at " + filepath)

        meta_file.close()
        statfile_data = self.list_of_all_statfile_data

        return {'statfile_data': statfile_data, 'logs': self.logs}

    def get_composite_stats(self):
        """
        Returns the composite stats found in `.archsimdb_composite_stats`

        :return: A dictionary containing the semi-parsed composite stats
        :rtype dict
        """

        composite_stats = {}
        line_number = 0

        # If the composite stats file exists, attempt to parse each line.

        try:
            composite_stats_filepath = self.working_path + '/.archsimdb_composite_stats'
            composite_stats_file = open(composite_stats_filepath, 'r')

            for line in composite_stats_file.readlines():
                line_number += 1
                try:
                    composite_stat_name = line.split('=')[0].strip()  # The left of the equals sign is the stat name
                    composite_stat_equation = line.split('=')[1]  # Everything to the right is the equation
                except IndexError:
                    self.logs.append("Failed to parse composite stat on line " + str(line_number))
                    continue

                if self.test_equation(composite_stat_equation, line_number):
                    composite_stats[composite_stat_name] = composite_stat_equation
                    self.logs.append("Added composite stat called " + composite_stat_name)
                else:
                    continue
        except FileNotFoundError:
            self.logs.append("No composite stats file found")

        return {'stats': composite_stats}

    def test_equation(self, composite_stat_equation, line_number):
        """
        Tests that the given equation will parse in Python. Rudimentary test only and just catches
        the basic syntax errors.

        :param composite_stat_equation: The equation of the composite stat
        :type composite_stat_equation: str

        :param line_number: The line number of the current composite stat
        :type line_number: int

        :return: Whether the equation parsed or not with dummy variables
        :rtype: bool
        """

        variables = re.sub('{.*?}', '1', composite_stat_equation).strip()  # Replace all variables with 1

        try:
            compile(variables, '<string>', 'eval')
            return True
        except SyntaxError:
            self.logs.append("Composite stat on line " + str(line_number) + " failed to compile. Please "
                                                                            "check that it is valid Python.")

        return False

    def delete_tracking_file(self):
        """
        Deletes the `.archsimdb_tracking_data` file

        :return None
        """

        meta_filepath = self.working_path + '/.archsimdb_tracking_data'

        try:
            os.remove(meta_filepath)
            self.logs.append("Tracking file detelted successfully.")
        except FileNotFoundError:
            self.logs.append("Couldn't find tracking file, aborting.")

    def prepare_input(self, filepath):
        """
        Parse and add releveant metadata to a new or changed statfile

        :param filepath: the path to the statfile
        :type filepath: str

        :return: None
        """

        filename = filepath.split('/')[-1]
        self.statfile_metadata['_sim_name'] = filename
        self.statfile_metadata['_conf_name'] = filepath.split('/')[-2]
        self.statfile_metadata['_exp_name'] = filepath.split('/')[-3]
        self.statfile_metadata['_sim_date'] = datetime.fromtimestamp(os.path.getmtime(filepath))

        parsed_data = self.reader.load(filepath)

        if parsed_data is not None:
            for key, value in self.statfile_metadata.items():
                    parsed_data[key] = value

            self.list_of_all_statfile_data.append(parsed_data)
        else:
            self.logs.append("Failed to parse file at " + filepath)
            self.failed_to_parse_statfiles.append(filepath)

    @staticmethod
    def hashfile(afile, hasher, blocksize=65536):
        """
        Return the md5 hash of a file

        :param afile: the file to be hashes
        :type afile: file

        :param hasher: the type of hasher to be used
        :type hasher: hashlib

        :param blocksize: the size of blocks in memory
        :type blocksize: int

        :return: A string representing the hash
        :rtype: str
        """

        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        return hasher.hexdigest()
