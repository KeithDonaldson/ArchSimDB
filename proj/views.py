from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid.interfaces import IBeforeRender
from pyramid.events import subscriber
from pyramid.events import NewRequest
from pyramid.httpexceptions import HTTPFound
from .reader import *
from .dbaccess import *
from .scanner import *
import os
import uuid
import logging
log = logging.getLogger(__name__)
import shutil
from bson.json_util import dumps
from datetime import datetime

# --------------------------- #
# --- Human-visible pages --- #
# --------------------------- #


@subscriber(IBeforeRender)
def globals_factory(event):
    master = get_renderer('templates/master.pt').implementation()
    event['master'] = master


@view_config(route_name='home', renderer='templates/index.pt')
def home(request):
    info = DatabaseInfo()
    exp_cnt = info.get_experiment_count(request)
    conf_cnt = info.get_configuration_count(request)
    app_cnt = info.get_applications_count(request)

    return {'exp_cnt': exp_cnt, 'conf_cnt': conf_cnt, 'app_cnt': app_cnt}


@view_config(route_name='upload', renderer='templates/upload.pt')
def upload(request):
    if request.method == 'POST':
        metadata = {}
        for key, val in request.POST.items():
            if key != 'statfile':
                if key == '_sim_date':
                    metadata[key] = datetime.strptime(val, "%Y-%m-%d")
                else:
                    metadata[key] = val

        input_file = request.POST['statfile'].file
        file_path = os.path.join('/tmp', '%s.txt' % uuid.uuid4())
        temp_file_path = file_path + '~'
        input_file.seek(0)
        with open(temp_file_path, 'wb') as output_file:
            shutil.copyfileobj(input_file, output_file)
        os.rename(temp_file_path, file_path)

        file_reader = Reader
        db_actions = DatabaseActions()

        parsed_data = file_reader.load(file_path)

        for key, val in metadata.items():
            parsed_data[key] = val

        inserted_id = db_actions.insert_application(request, parsed_data)

        return {'inserted_id': inserted_id}
    else:
        return {}


@view_config(route_name='add/configuration', renderer='templates/insert_conf.pt')
def add_conf(request):
    """
    :param request:
    :return:
    """

    if request.method == 'POST':
        conf_data = {}
        for key, val in request.POST.items():
            if key == '_conf_date':
                conf_data[key] = datetime.strptime(val, "%Y-%m-%d")
            else:
                conf_data[key] = val

        db_actions = DatabaseActions()
        inserted_id = db_actions.insert_configuration(request, conf_data)

        return {'inserted_id': inserted_id}
    else:
        return {}


@view_config(route_name='applications', renderer='templates/applications.pt')
def applications(request):
    db_actions = DatabaseActions()
    all_applications = db_actions.get(request, 'applications', projection=['_sim_name', '_sim_owner', '_sim_date',
                                                                           '_exp_name', '_conf_name'])
    app_dict = [dict(pn) for pn in all_applications]

    for app in app_dict:
        for key, val in app.items():
            if key == '_sim_date':
                app[key] = val.strftime("%Y-%m-%d")

    return {'applications': dumps(app_dict)}


@view_config(route_name='configurations', renderer='templates/configurations.pt')
def configurations(request):
    db_actions = DatabaseActions()
    all_configurations = db_actions.get(request, 'configurations')
    conf_dict = [dict(pn) for pn in all_configurations]

    for conf in conf_dict:
        for key, val in conf.items():
            if key == '_conf_date':
                conf[key] = val.strftime("%Y-%m-%d")

    return {'configurations': dumps(conf_dict)}


@view_config(route_name='experiments', renderer='templates/experiments.pt')
def experiments(request):
    db_actions = DatabaseActions()
    all_experiments = db_actions.get(request, 'experiments')
    exp_dict = [dict(pn) for pn in all_experiments]

    for exp in exp_dict:
        for key, val in exp.items():
            if key == '_exp_date':
                exp[key] = val.strftime("%Y-%m-%d")

    return {'experiments': dumps(exp_dict)}


@view_config(route_name='flot', renderer='templates/flot.pt')
def flot(request):
    return {}


@view_config(route_name='sync', renderer='templates/sync.pt')
def sync(request):
    if request.method == 'POST':
        scanner = Scanner()
        db_actions = DatabaseActions()
        scanning_results = scanner.scanner()

        list_of_inserts = scanning_results.get('statfile_data')
        scanner_logs = scanning_results.get('logs')
        dbaccess_logs = db_actions.handle_sync(request, list_of_inserts)

        logs = scanner_logs + dbaccess_logs

        return {'inserted_no': len(list_of_inserts), 'logs': logs}
    else:
        return {}


@view_config(route_name='query', renderer='templates/query.pt')
def query(request):
    db_actions = DatabaseActions()
    all_experiments = db_actions.get(request, 'experiments')
    exp_dict = [dict(pn) for pn in all_experiments]

    for exp in exp_dict:
        for key, val in exp.items():
            if key == '_exp_date':
                exp[key] = val.strftime("%Y-%m-%d")

    return {'experiments': dumps(exp_dict)}


# --------------------- #
# POST AND GET REQUESTS #
# --------------------- #

@view_config(route_name='get/configurations', renderer='json')
def get_configurations(request):
    if '_exp_name' in request.POST:
        filters = {'_exp_name': request.POST.get('_exp_name')}
        db_actions = DatabaseActions

        confs = db_actions.get(request, 'configurations', selection=filters)
        conf_dict = [dict(pn) for pn in confs]

        for conf in conf_dict:
            for key, val in conf.items():
                if key == '_conf_date':
                    conf[key] = val.strftime("%Y-%m-%d")

        return dumps(conf_dict)


@view_config(route_name='get/applications', renderer='json')
def get_applications(request):
    if '_conf_name' in request.POST:
        filters = {'_conf_name': request.POST.get('_conf_name'), '_exp_name': request.POST.get('_exp_name')}
        db_actions = DatabaseActions

        apps = db_actions.get(request, 'applications', selection=filters,
                              projection=['_sim_name', '_sim_owner', '_sim_date', '_exp_name', '_conf_name'])
        app_dict = [dict(pn) for pn in apps]

        for app in app_dict:
            for key, val in app.items():
                if key == '_sim_date':
                    app[key] = val.strftime("%Y-%m-%d")

        return dumps(app_dict)
