from pyramid.view import view_config
from .reader import *
import os
import uuid
import shutil
from bson.json_util import dumps


@view_config(route_name='home', renderer='templates/index.pt')
def home(request):
    info = DatabaseInfo()
    collections = info.get_all_collection_names(request)
    exp_cnt = info.get_experiment_count(request)
    conf_cnt = info.get_configuration_count(request)
    app_cnt = info.get_applications_count(request)

    return {'collections': collections, 'exp_cnt': exp_cnt, 'conf_cnt': conf_cnt, 'app_cnt': app_cnt}


@view_config(route_name='upload', renderer='templates/upload.pt')
def upload(request):
    return {}


@view_config(route_name='upload_processor', renderer='templates/index.pt')
def upload_processor(request):
    """
    :param request:
    :return:
    """

    input_file = request.POST['txt'].file
    file_path = os.path.join('/tmp', '%s.txt' % uuid.uuid4())
    temp_file_path = file_path + '~'
    input_file.seek(0)
    with open(temp_file_path, 'wb') as output_file:
        shutil.copyfileobj(input_file, output_file)
    os.rename(temp_file_path, file_path)

    file_reader = Reader
    db_info = DatabaseInfo
    db_actions = DatabaseActions

    parsed_data = file_reader.load(file_path)
    inserted_id = db_actions.insert_application(request, parsed_data)
    parsed_data = db_actions.find_application_by_id(request, inserted_id)

    db_data = home(request)
    db_data['inserted_id'] = inserted_id
    db_data['inserted_data'] = dumps(parsed_data, sort_keys=True, indent=4)[:1000]

    request.response.status = 200
    return db_data


def insert_document(parsed_data, request):
    """
    Just inserts arbitrary static data into the database for now until I have a parser.

    :param file_path: The path to the newly uploaded txt file
    :return: Response
    """

    actions = DatabaseActions()
    inserted_id = actions.insert_application(request, parsed_data)

    return inserted_id


class DatabaseInfo:

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


class DatabaseActions:

    @staticmethod
    def insert_application(request, document_data):
        return request.db['applications'].insert_one(document_data).inserted_id

    @staticmethod
    def find_application_by_id(request, document_id):
        return request.db['applications'].find_one({'_id': document_id})
