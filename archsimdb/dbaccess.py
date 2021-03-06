import operator


class DatabaseInfo:
    """
    Provides methods for accessing single pieces of metadata from the database.
    These methods will not return any of the actual data from within the database.
    """

    @staticmethod
    def get_all_collection_names(request):
        return request.db.collection_names()

    @staticmethod
    def get_collection_count(request, collection_name):
        return request.db[collection_name].count()

    @staticmethod
    def get_experiment_count(request):
        return request.db['experiments'].count()

    @staticmethod
    def get_configuration_count(request):
        return request.db['configurations'].count()

    @staticmethod
    def get_applications_count(request):
        return request.db['applications'].count()

    @staticmethod
    def get_applications_count_by_conf(request, conf_id):
        return request.db['applications'].find({'_conf_id': conf_id}, projection=['_sim_name']).count()


class DatabaseActions:
    """
    Provides methods for interacting with the data inside the database.
    """

    def __init__(self):
        self.logs = []

    def handle_sync(self, request, list_of_statfiles):
        """
        Inserts the required data into the database upon user syncing.
        
        :param request: The Pyramid request object
        :type request: Request
        
        :param list_of_statfiles: A list containing dictionaries to insert into database
        :type list_of_statfiles: list
        
        :return: A log of what happened
        :type: list
        """

        for statfile in list_of_statfiles:
            
            # - For each insert, we need to check for duplicate entries in the database
            experiment_names = self.get_all_experiment_names(request)
            configurations = self.get(request, 'configurations')

            conf_pairs = []
            conf_identity = [statfile.get('_conf_name'), statfile.get('_exp_name')]
            
            for config in configurations:
                conf_pairs.append([config.get('_conf_name'), config.get('_exp_name')])

            sim_dates = self.get(request, 'applications',
                                 selection={'_exp_name': statfile.get('_exp_name'),
                                            '_conf_name': statfile.get('_conf_name')},
                                 projection=['_sim_date'])
            sim_dates_dict = [dict(pn) for pn in sim_dates]
            latest_date = statfile.get('_sim_date')

            for date in sim_dates_dict:
                if date.get('_sim_date').strftime("%Y-%m-%d") >= statfile.get('_sim_date').strftime("%Y-%m-%d"):
                    latest_date = date.get('_sim_date')
            
            # - If this statfile is from a new experiment, create the experiment in the database
            if statfile.get('_exp_name') not in experiment_names:
                exp_metadata = {'_exp_name': statfile.get('_exp_name'),
                                '_exp_owner': statfile.get('_sim_owner'),
                                '_exp_date': latest_date}
                self.insert_experiment(request, exp_metadata)
            else:
                self.update(request, 'experiments', {'_exp_date': latest_date},
                            selection={'_exp_name': statfile.get('_exp_name')})
                
            # - If this statfile is from a new configuration, create the configuration in the database
            if conf_identity not in conf_pairs:
                conf_metadata = {'_conf_name': statfile.get('_conf_name'),
                                 '_conf_owner': statfile.get('_sim_owner'),
                                 '_conf_date': latest_date,
                                 '_exp_name': statfile.get('_exp_name')}
                self.insert_configuration(request, conf_metadata)
            else:
                self.update(request, 'configurations', {'_conf_date': latest_date},
                            selection={'_exp_name': statfile.get('_exp_name'),
                                       '_conf_name': statfile.get('_conf_name')})

            # - Check for duplicate in the database and delete if it exists
            duplicate = self.get(request, 'applications',
                                 selection={'_exp_name': statfile.get('_exp_name'),
                                            '_conf_name': statfile.get('_conf_name'),
                                            '_sim_name': statfile.get('_sim_name')},
                                 projection=['_sim_name'])

            if duplicate.count() != 0:
                self.logs.append("Deleting previous version of " + statfile.get('_sim_name'))
                self.delete(request, 'applications', selection={'_exp_name': statfile.get('_exp_name'),
                                                                '_conf_name': statfile.get('_conf_name'),
                                                                '_sim_name': statfile.get('_sim_name')})

            # - Finally, insert the parsed statfile into the database
            self.insert_application(request, statfile)

        if self.logs is None:
            return []
        else:
            return self.logs

    def insert_application(self, request, document_data):
        """
        Inserts a new application into the database

        :param request: The request object
        :type request: pyramid.request

        :param document_data: A dictionary with the data to be added
        :type document_data: dict

        :return: An insert confirmation object
        :rtype pymongo.results.InsertOneResult
        """

        self.logs.append("Inserting application with name " + document_data.get('_sim_name'))
        return request.db['applications'].insert_one(document_data).inserted_id

    def insert_configuration(self, request, document_data):
        """
        Inserts a new configuration into the database

        :param request: The request object
        :type request: pyramid.request

        :param document_data: A dictionary with the data to be added
        :type document_data: dict

        :return: An insert confirmation object
        :rtype pymongo.results.InsertOneResult
        """

        self.logs.append("Inserting configuration with name " + document_data.get('_conf_name'))
        return request.db['configurations'].insert_one(document_data).inserted_id

    def insert_experiment(self, request, document_data):
        """
        Inserts a new experiment into the database

        :param request: The request object
        :type request: pyramid.request

        :param document_data: A dictionary with the data to be added
        :type document_data: dict

        :return: An insert confirmation object
        :rtype pymongo.results.InsertOneResult
        """

        self.logs.append("Inserting experiment with name " + document_data.get('_exp_name'))
        return request.db['experiments'].insert_one(document_data).inserted_id

    def delete_all(self, request):
        """
        Deletes all content in the database

        :param request: The reqest object
        :type request: pyramid.request

        :return: A dictionary containing the logs
        :rtype dict
        """

        request.db['applications'].delete_many({})
        self.logs.append("Deleted all applications")

        request.db['configurations'].delete_many({})
        self.logs.append("Deleted all configurations")

        request.db['experiments'].delete_many({})
        self.logs.append("Deleted all experiments")

        return {'logs': self.logs}

    def get_hierarchy(self, request):
        """
        Returns the database in a hierarchical form and formatted for jstree usage

        :param request: The request object
        :type request: pyramid.request

        :return: The hierarchy as a dictionary
        :rtype dict
        """

        exps = self.get(request, 'experiments', projection=['_exp_name', '_exp_date'])
        exp_dict = [dict(pn) for pn in exps]
        exp_dict = sorted(exp_dict, key=lambda k: k['_exp_date'], reverse=True)

        confs = self.get(request, 'configurations', projection=['_conf_name', '_conf_date', '_exp_name'])
        conf_dict = [dict(pn) for pn in confs]
        conf_dict = sorted(conf_dict, key=lambda k: k['_conf_date'],reverse=True)

        apps = self.get(request, 'applications', projection=['_sim_name', '_sim_date', '_conf_name', '_exp_name'])
        app_dict = [dict(pn) for pn in apps]
        app_dict = sorted(app_dict, key=lambda k: k['_sim_date'], reverse=True)

        hierarchy = []

        for exp in exp_dict:
            hierarchy.append({
                'id': exp.get('_exp_name'),
                'text': exp.get('_exp_name'),
                'parent': '#',
                'icon': 'fa fa-folder-o'
            })

        for conf in conf_dict:
            hierarchy.append({
                'id': conf.get('_exp_name') + '/' + conf.get('_conf_name'),
                'text': conf.get('_conf_name'),
                'parent': conf.get('_exp_name'),
                'icon': 'fa fa-folder-o'
            })

        for app in app_dict:
            hierarchy.append({
                'id': '*' + app.get('_exp_name') + '/' + app.get('_conf_name') + '/' + app.get('_sim_name'),
                'text': app.get('_sim_name'),
                'parent': app.get('_exp_name') + '/' + app.get('_conf_name'),
                'icon': 'fa fa-file-text-o'
            })

        return hierarchy

    @staticmethod
    def get(request, collection, selection={}, projection=None):
        """
        The base method for returning data from the database

        :param request: The request object
        :type request: pyramid.request

        :param collection: The collection to access data from
        :type collection: str

        :param selection: The selection criteria for items in the database
        :type selection: dict

        :param projection: The fields in the database to return
        :type projection: list

        :return: A cursor containing the returned data from the database
        :rtype pymongo.cursor.Cursor
        """

        return request.db[collection].find(selection, projection=projection)

    @staticmethod
    def update(request, collection, pairs, selection={}):
        """
        The base method for updating existing data in the database

        :param request: The request object
        :type request: pyramid.request

        :param collection: The collection to access data from
        :type collection: str

        :param pairs: The keys and values to update
        :type pairs: dict

        :param selection: The selection criteria for items in the database
        :type selection: dict

        :return: An update confirmation
        :rtype: pymongo.results.UpdateResult
        """

        return request.db[collection].update_many(selection, {'$set': pairs}, upsert=False)

    @staticmethod
    def delete(request, collection, selection={}):
        """
        The base method for deleting existing data in the database

        :param request: The request object
        :type request: pyramid.request

        :param collection: The collection to access data from
        :type collection: str

        :param selection: The selection criteria for items in the database
        :type selection: dict

        :return: A deletion confirmation
        :rtype: pymongo.results.DeleteResult
        """

        return request.db[collection].delete_many(selection)

    @staticmethod
    def get_application_by_id(request, document_id):
        """
        Returns an application matching the ObjectID

        :param request: The request object
        :type request: pyramid.request

        :param document_id: An ObjectID of the item in the database
        :type document_id: bson.ObjectID

        :return: A cursor containing the returned data from the database
        :rtype pymongo.cursor.Cursor
        """

        return request.db['applications'].find_one({'_id': document_id})

    @staticmethod
    def get_all_experiment_names(request):
        """
        Returns the names of all experiments in the database as a list

        :param request: The request object
        :type request: pyramid.request

        :return: A list containing experiments names
        :rtype: list
        """

        names = []
        all_experiments = request.db['applications'].find({}, projection=['_exp_name'])
        for exp in all_experiments:
            names.append(exp.get('_exp_name'))

        return names

    @staticmethod
    def get_all_configuration_names(request):
        """
        Returns the names of all configurations in the database as a list

        :param request: The request object
        :type request: pyramid.request

        :return: A list containing configuration names
        :rtype: list
        """

        names = []
        all_configurations = request.db['configurations'].find({}, projection=['_conf_name'])
        for conf in all_configurations:
            names.append(conf.get('_conf_name'))

        return names
