import logging
import json


class Reader:
    """
    Provides functionality to read from uploaded files.
    """

    @staticmethod
    def load(input_filepath, logging_level="logging.ERROR"):
        """
        Load, read, and parse a file.

        :param input_filepath: The absolute path to the uploaded file
        :type: str

        :param logging_level: The level of logging for the parser based on logging package.
        :type: str

        :return: A dictionary with the parsed file data
        :rtype: dict
        """

        # - Initialise logging and the Parser object
        logging.basicConfig(filemode='w', level=logging_level)
        parser = Parser()

        # - Open the given file in read mode, split the lines, and feed that to the parser.
        input_file = open(input_filepath, 'r')
        file = input_file.read()
        parsed_data = parser.parse(file, input_filepath)

        return parsed_data


class Parser:
    """
    Provides functionality to parse uploaded files.

    Attributes:
        input_data: A list storing the lines from a Flexus input
        output_data: A dictionary that stores parsed key-values.
        line_number: An integer that keeps track of the line the parser is at.
    """

    def __init__(self):
        self.input_data = []
        self.output_data = {}
        self.line_number = 0

    def parse(self, input_file, filepath):
        """
        Parses a statfile

        :param input_file: The read input statfile
        :type input_file: str

        :param filepath: The input statfile's filepath
        :type filepath: str

        :return: A dictionary with parsed file data
        :rtype: dict
        """

        lines = input_file.splitlines()
        file_type = self.determine_filetype(lines)

        if file_type == "Flexus":
            try:
                return self.parse_flexus_statfile(lines)
            except ParserException as e:
                logging.error("ERROR: Cannot parse statfile (believed to be Flexus) at " + filepath + ", see below:")
                logging.error(e.msg)
                return None
        elif file_type == "JSON":
            try:
                return self.parse_json(input_file)
            except ValueError as e:
                logging.error("ERROR: Cannot parse statfile (believed to be JSON) at " + filepath + ", see below:")
                logging.error(e)
                return None
        else:
            logging.error("Unknown filetype")
            return None

    def parse_flexus_statfile(self, lines):
        """
        Parse a statfile from Flexus Simulator.

        :param lines: The lines of the read file
        :type: list

        :return: A dictionary with the parsed file data
        :type: dict
        """

        self.input_data = lines

        # - Deal with the first line, always 'sum' or 'all' and set _sim_type

        if self.input_data[0] != "sum" and self.input_data[0] != "all":
            logging.error("No 'sum' or 'all' found")
            raise ParserException("Sum or all not included on line 1, found '" + self.input_data[0] + "'")

        self.output_data['_sim_type'] = "Flexus"
        line_type = self.flexus_next_type()
        self.line_number += 1

        # The main loop of the parser. The class variable 'line_number' gets updated by the
        # various methods. The variable 'line_type' keeps track of the current type of the line,
        # as defined in the 'next_type' method. The variable 'next_line_type' keeps track of the
        # expected/next type of the line, as defined in the 'next_type' method. These two
        # variables give us all the information we need to know how to parse the line. With this
        # information, we call a sub-method to parse either the current line or the impending
        # table. Sub-methods update the class variable 'line_number' internally should it be
        # parsing more than just the one line.

        while self.line_number != len(lines):

            next_line_type = self.flexus_next_type()

            if line_type == "empty":
                pass
            elif line_type == "eof":
                break
            elif line_type == "ko":
                if next_line_type == "bs":
                    self.flexus_parse_table_bs()
                elif next_line_type == "cpv":
                    self.flexus_parse_table_cpv()
                else:
                    self.flexus_parse_novalue()
            elif line_type == "kv":
                if next_line_type == "bs":
                    self.flexus_parse_table_bs()
                elif next_line_type == "cpv":
                    self.flexus_parse_table_cpv()
                else:
                    self.flexus_parse_keyval()
            else:
                logging.error("Unexpected token found")
                raise ParserException("Unexpected token type on line " + str(self.line_number))

            line_type = self.flexus_next_type()
            self.line_number += 1

        return self.output_data

    def flexus_next_type(self):
        """
        Flexus helper: Finds the type of the next line.

        :return: The type of the next line
        :type: str
        """

        # Catch the end-of-file case before attempting anything else, and if we are
        # safe then set 'line' to the next line in the input data.

        try:
            line = self.input_data[self.line_number+1].split()
        except IndexError:
            return "eof"                         # End of File

        # There are five types of lines we can expect from Flexus data:
        #   'empty': An empty line,
        #   'ko': Key only; Just a single token on a line with no discernible value,
        #   'bs': Bucket Size Table; A table with two columns: "Bucket" and "Size",
        #   'cpv': Count Pct Value Table; A table with two columns: "Count", "Pct", and "Value",
        #   'kv': Key Value; A simple key-value pair.
        # Small inspections of the line deduce the type. The 'kv' option is a catch-all-else,
        # with the value parsed as the last item on the line and the key as everything prior.

        if len(line) == 0:
            return "empty"                       # Empty
        if len(line) == 1:
            return "ko"                          # Key only
        elif line[0] == "Bucket" and line[1] == "Size":
            return "bs"                          # Bucket size
        elif line[0] == "Count" and line[1] == "Pct" and line[2] == "Value":
            return "cpv"                         # Count Pct Value
        else:
            return "kv"                          # Key value

    def flexus_parse_keyval(self):
        """
        Flexus helper: Parses a key-value pair from the Flexus statfile.

        :return: None
        """

        line = self.input_data[self.line_number].split()

        key = " ".join(line[:-1])
        val = line[-1]

        logging.debug("Line #: {0}\t| Type: KV | Key: {1} | Value: {2}".format(self.line_number + 1, key, val))

        if val.isdigit():
            self.output_data[key] = int(val)
        else:
            self.output_data[key] = val

    def flexus_parse_novalue(self):
        """
        Flexus helper: Parses a key with no value from the Flexus statfile.

        :return: None
        """

        key = self.input_data[self.line_number].strip()

        logging.debug("Line #: {0}\t| Type: KO | Key: {1}".format(self.line_number + 1, key))

        self.output_data[key] = -1

    def flexus_parse_table_cpv(self):
        """
        Flexus helper: Parses a Count/Pct/Value table.

        :return: None
        """

        # - The key for the whole table is on the current line and is stored in 'key'

        key = self.input_data[self.line_number].strip()

        self.line_number += 2
        table_data = {}

        # For each line hereon in until we hit a line of dashes, we expect three values:
        # "Count", "Pct", and "Value". The "Value" column is parsed as 'inside_key' and the
        # "Count" column is parsed as 'inside_value'.

        for cpv_line in self.input_data[self.line_number:]:
            try:
                inside_key = cpv_line.split()[2]  # The "Value" column
            except IndexError:
                logging.debug("100.00% issue caught")
                inside_key = cpv_line.split()[1]  # The "Value" column

            # First if statement: If we have hit the dashes, the data we need has ended.
            # Second if statement: If the value has been grouped into "in X undisplayed elements".
            # Third if statement: If the Pct is 100.00% and doesn't put a space between "Count" and "Pct".

            if "-" in inside_key:
                break

            if inside_key == "in":
                inside_key = "In Undisplayed"

            if len(cpv_line.split()) == 2:
                inside_val = cpv_line.split()[0][:-7]  # Remove the '100.00%' from the tail
            else:
                inside_val = cpv_line.split()[0]  # The "Count" column

            self.output_data[key + ':' + inside_key] = int(inside_val)

            logging.debug("Line #: {0}\t| Type: CPV | Key: {1} | Inside Key: {2} | Inside Value: {3}".format(
                self.line_number + 1, key, inside_key, inside_val))

            self.line_number += 1

        self.line_number += 3                    # Skip the summation lines

    def flexus_parse_table_bs(self):
        """
        Flexus helper: Parses a Bucket/Size table.

        :return: None
        """

        # - The key for the whole table is on the current line and is stored in 'key'

        key = self.input_data[self.line_number].strip()

        self.line_number += 2
        table_data = {}

        # For each line hereon in until we hit a blank line, we expect two values:
        # "Bucket" and "Size". The "Bucket" column is parsed as 'inside_key' and the
        # "Size" column is parsed as 'inside_value'.

        for bs_line in self.input_data[self.line_number:]:
            bs_line = bs_line.split(":\t")

            # If the line is no longer a key-value, the table has ended
            if len(bs_line) != 2:
                break

            inside_key = bs_line[0].strip()      # The "Bucket" column
            inside_val = bs_line[1]              # The "Size" column

            self.output_data[key + ':' + inside_key] = int(inside_val)

            logging.debug("Line #: {0}\t| Type: BS | Key: {1} | Inside Key: {2} | Inside Value: {3}".format(
                self.line_number + 1, key, inside_key, inside_val))

            self.line_number += 1

    def parse_json(self, file):
        """
        Parses a statfile in JSON format

        :return: A dictionary with the parsed data
        :rtype: dict
        """

        keys_to_delete = []
        keys_to_add = []

        self.output_data = json.loads(file)
        self.output_data['_sim_type'] = "JSON"

        # - Take any nested dictionaries and transform into keys
        for (key, val) in self.output_data.items():
            if type(val) is dict:
                print(self.output_data[key])
                for (inside_key, inside_val) in self.output_data[key].items():
                    keys_to_add.append({key + ':' + inside_key: inside_val})
                keys_to_delete.append(key)

        print(keys_to_delete)
        print(keys_to_add)

        for key in keys_to_delete:
            del self.output_data[key]

        for new_keys in keys_to_add:
            for (key, val) in new_keys.items():
                self.output_data[key] = val

        return self.output_data

    @staticmethod
    def determine_filetype(lines):
        """
        Provides logic to determine the filetype for the statfile

        :param lines: The lines of the read file
        :type lines: list

        :return: The filetype
        :rtype: str
        """

        if lines[0] == "sum" or lines[0] == "all":  # Flexus
            return "Flexus"
        else:
            return "JSON"


class ParserException(Exception):
    pass
