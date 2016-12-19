import os
import logging
import hashlib
from datetime import datetime
from .reader import Reader
from .dbaccess import DatabaseActions


class Scanner:

    def __init__(self):
        self.reader = Reader()
        self.db_actions = DatabaseActions()
        self.statfile_metadata = {}
        self.checksums = {}
        self.list_of_all_statfile_data = []
        self.logs = []

    def scanner(self):
        working_path = "/home/keith/Documents/statfiles/s1319624/"
        initiated = False
    
        logger = logging.getLogger("sync")
    
        if working_path[-1] == '/':
            working_path = working_path[:-1]
    
        for dirpath, dirnames, filenames in os.walk(working_path):
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
    
            for file in filenames:
                if file != ".archsimdb_tracking_data":
                    filepath = dirpath + '/' + file
                    statfile = open(filepath, 'rb')
                    if filepath not in self.checksums:
                        meta_file.write(filepath + " " + self.hashfile(statfile, hashlib.md5()) + "\n")
                        self.prepare_input(filepath)
                        logger.info("Found new file at " + filepath)
                        self.logs.append("Found new file at " + filepath)
                    elif self.checksums.get(filepath) != self.hashfile(statfile, hashlib.md5()):
                        meta_file.write(filepath + " " + self.hashfile(statfile, hashlib.md5()) + "\n")
                        self.prepare_input(filepath)
                        logger.info("Found changed file at " + filepath)
                        self.logs.append("Found changed file at " + filepath)
                    else:
                        meta_file.write(filepath + " " + self.checksums.get(filepath) + "\n")
                        logger.info("Found unchanged file at " + filepath)
                        self.logs.append("Found unchanged file at " + filepath)
    
        meta_file.close()

        return {'statfile_data': self.list_of_all_statfile_data, 'logs': self.logs}
        
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
        self.statfile_metadata['_sim_date'] = datetime.strptime(filename.split('.')[4][:10], "%Y-%m-%d")

        parsed_data = self.reader.load(filepath)
        for key, value in self.statfile_metadata.items():
            parsed_data[key] = value

        self.list_of_all_statfile_data.append(parsed_data)

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
        :type: str
        """
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        return hasher.hexdigest()
