from bson.objectid import ObjectId
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

    def handle_sync(self, request, list_of_statfiles):
        experiment_names = self.get_all_experiment_names(request)
        configurations = self.get_all_configurations(request)

        conf_pairs = []
        for config in configurations:
            conf_pairs.append([config.get('_conf_name'), config.get('_exp_name')])

        for parsed_statfile in list_of_statfiles:
            if parsed_statfile.get('_exp_name') not in experiment_names:
                exp_metadata = {'_exp_name': parsed_statfile.get('_exp_name'),
                                '_exp_owner': parsed_statfile.get('_sim_owner'),
                                '_exp_date': parsed_statfile.get('_sim_date')}
                self.insert_experiment(request, exp_metadata)
            conf_identity = [parsed_statfile.get('_conf_name'), parsed_statfile.get('_exp_name')]
            if conf_identity not in conf_pairs:
                conf_metadata = {'_conf_name': parsed_statfile.get('_conf_name'),
                                 '_conf_owner': parsed_statfile.get('_sim_owner'),
                                 '_conf_date': parsed_statfile.get('_sim_date'),
                                 '_exp_name': parsed_statfile.get('_exp_name')}
                self.insert_configuration(request, conf_metadata)
            self.insert_application(request, parsed_statfile)

    @staticmethod
    def insert_application(request, document_data):
        return request.db['applications'].insert_one(document_data).inserted_id

    @staticmethod
    def insert_configuration(request, document_data):
        return request.db['configurations'].insert_one(document_data).inserted_id

    @staticmethod
    def insert_experiment(request, document_data):
        return request.db['experiments'].insert_one(document_data).inserted_id

    @staticmethod
    def find_application_by_id(request, document_id):
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

    @staticmethod
    def get_all_applications(request):
        return request.db['applications'].find({}, projection=['_sim_name', '_sim_owner', '_sim_date',
                                                               '_exp_name', '_conf_name'])

    @staticmethod
    def get_all_configurations(request):
        return request.db['configurations'].find({}, projection=['_conf_name', '_conf_owner', '_conf_date',
                                                                 '_exp_name'])

    @staticmethod
    def get_all_experiments(request):
        return request.db['experiments'].find({}, projection=['_exp_name', '_exp_owner', '_exp_date'])


