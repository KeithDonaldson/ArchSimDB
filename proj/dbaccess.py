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

    @staticmethod
    def insert_application(request, document_data):
        return request.db['applications'].insert_one(document_data).inserted_id

    @staticmethod
    def insert_configuration(request, document_data):
        return request.db['configurations'].insert_one(document_data).inserted_id

    @staticmethod
    def find_application_by_id(request, document_id):
        return request.db['applications'].find_one({'_id': document_id})

    @staticmethod
    def get_all_applications(request):
        return request.db['applications'].find({}, projection=['_sim_name', '_sim_owner', '_sim_date',
                                                               '_cpu_arch', '_benchmark'])

    @staticmethod
    def get_all_configurations(request):
        db_info = DatabaseInfo()
        configurations = request.db['configurations'].find({}, projection=['_conf_name', '_conf_owner', '_conf_date'])

        return configurations

    # @staticmethod
    # def get_all_experiments(request):
    #     db_info = DatabaseInfo()
    #     configurations = request.db['configurations'].find({}, projection=['_conf_name', '_conf_owner', '_conf_date'])
    #     for config in configurations:
    #         config['app_count'] = db_info.get_applications_count_by_conf(request, config['_id'])
    #
    #     return configurations
