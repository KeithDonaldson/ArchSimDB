import logging


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
            
            # For each insert, we need to check for duplicate entries in the database
            
            experiment_names = self.get_all_experiment_names(request)
            configurations = self.get(request, 'configurations')

            conf_pairs = []
            conf_identity = [statfile.get('_conf_name'), statfile.get('_exp_name')]
            
            for config in configurations:
                conf_pairs.append([config.get('_conf_name'), config.get('_exp_name')])
            
            # If this statfile is from a new experiment, create the experiment in the database

            if statfile.get('_exp_name') not in experiment_names:
                exp_metadata = {'_exp_name': statfile.get('_exp_name'),
                                '_exp_owner': statfile.get('_sim_owner'),
                                '_exp_date': statfile.get('_sim_date')}
                self.insert_experiment(request, exp_metadata)
                
            # If this statfile is from a new configuration, create the configuration in the database           

            if conf_identity not in conf_pairs:
                conf_metadata = {'_conf_name': statfile.get('_conf_name'),
                                 '_conf_owner': statfile.get('_sim_owner'),
                                 '_conf_date': statfile.get('_sim_date'),
                                 '_exp_name': statfile.get('_exp_name')}
                self.insert_configuration(request, conf_metadata)
            
            # Finally, insert the parsed statfile into the database
            
            self.insert_application(request, statfile)

        if self.logs is None:
            return []
        else:
            return self.logs

    @staticmethod
    def get(request, collection, selection={}, projection=None):
        return request.db[collection].find(selection, projection=projection)

    def insert_application(self, request, document_data):
        self.logs.append("Inserting application with name " + document_data.get('_sim_name'))
        return request.db['applications'].insert_one(document_data).inserted_id

    def insert_configuration(self, request, document_data):
        self.logs.append("Inserting configuration with name " + document_data.get('_conf_name'))
        return request.db['configurations'].insert_one(document_data).inserted_id

    def insert_experiment(self, request, document_data):
        self.logs.append("Inserting experiment with name " + document_data.get('_exp_name'))
        return request.db['experiments'].insert_one(document_data).inserted_id

    @staticmethod
    def get_application_by_id(request, document_id):
        return request.db['applications'].find_one({'_id': document_id})

    @staticmethod
    def get_all_experiment_names(request):
        names = []
        all_experiments = request.db['applications'].find({}, projection=['_exp_name'])
        for exp in all_experiments:
            names.append(exp.get('_exp_name'))

        return names

    @staticmethod
    def get_all_configuration_names(request):
        names = []
        all_configurations = request.db['configurations'].find({}, projection=['_conf_name'])
        for conf in all_configurations:
            names.append(conf.get('_conf_name'))

        return names

    def get_hierarchy(self, request):
        apps = self.get(request, 'applications', projection=['_sim_name', '_conf_name', '_exp_name'])
        app_dict = [dict(pn) for pn in apps]

        hierarchy = {}

        for app in app_dict:
            _exp_name = app.get('_exp_name')
            _conf_name = app.get('_conf_name')
            _sim_name = app.get('_sim_name')

            if _exp_name in hierarchy:
                if _conf_name in hierarchy[_exp_name]:
                    hierarchy[_exp_name][_conf_name][_sim_name] = _sim_name
                else:
                    hierarchy[_exp_name][_conf_name] = {}
                    hierarchy[_exp_name][_conf_name][_sim_name] = _sim_name
            else:
                hierarchy[_exp_name] = {}
                hierarchy[_exp_name][_conf_name] = {}
                hierarchy[_exp_name][_conf_name][_sim_name] = _sim_name

        return hierarchy

