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
                        data = [line.strip().split() for line in meta_file.readlines()]
                        self.checksums = {file: checksum for (file, checksum) in data}
                    meta_file.close()
                except FileNotFoundError:
                    pass
                meta_file = open(meta_filepath, 'w+')
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
        filename = filepath.split('/')[-1]
        self.statfile_metadata['_sim_name'] = filename
        self.statfile_metadata['_exp_name'] = filename.split('.')[0]
        self.statfile_metadata['_conf_name'] = filename.split('.')[3]
        self.statfile_metadata['_sim_date'] = datetime.strptime(filename.split('.')[4][:10], "%Y-%m-%d")

        parsed_data = self.reader.load(filepath)
        for key, value in self.statfile_metadata.items():
            parsed_data[key] = value

        self.list_of_all_statfile_data.append(parsed_data)

    @staticmethod
    def hashfile(afile, hasher, blocksize=65536):
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        return hasher.hexdigest()
