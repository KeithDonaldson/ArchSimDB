from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid.interfaces import IBeforeRender
from pyramid.events import subscriber
from .reader import *
from .dbaccess import *
from .scanner import *
from bson.json_util import dumps
from collections import OrderedDict

import logging
log = logging.getLogger(__name__)

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


@view_config(route_name='app_info', renderer='templates/data.pt')
def app_info(request):
    db_actions = DatabaseActions()
    _exp_name = request.matchdict['_exp_name']
    _conf_name = request.matchdict['_conf_name']
    _sim_name = request.matchdict['_sim_name']

    raw_data = db_actions.get(request, 'applications', {'_exp_name': _exp_name, '_conf_name': _conf_name,
                                                        '_sim_name': _sim_name})

    data = [dict(pn) for pn in raw_data]

    return {'data': dumps(data), '_sim_name': data[0].get('_sim_name')[:20]}


@view_config(route_name='compare', renderer='templates/compare.pt')
def compare(request):
    db_actions = DatabaseActions()
    data_hierarchy = db_actions.get_hierarchy(request)

    return {'hierarchy': json.dumps(data_hierarchy, sort_keys=True)}


@view_config(route_name='compare_results', renderer='templates/compare_results.pt')
def compare_results(request):
    if 'fields[]' in request.POST:
        fields = request.POST.getall('fields[]')
        apps = request.POST.getall('apps[]')

        db_actions = DatabaseActions()
        results = {}
        app_names = []

        for app in apps:
            _exp_name, _conf_name, _sim_name = app.split('/')[:3]
            app_names.append(_sim_name[:15])
            filters = {'_exp_name': _exp_name, '_conf_name': _conf_name, '_sim_name': _sim_name}
            result = db_actions.get(request, 'applications', selection=filters, projection=fields)
            results[_sim_name] = ([dict(pn) for pn in result][0])

        data = []

        for field in fields:
            field_data = OrderedDict({'field': field})
            for key, val in results.items():
                if val.get(field) is None:
                    field_data[key[:15]] = "-"
                else:
                    field_data[key[:15]] = val.get(field)
            data.append(field_data)

        results = {'data': data, 'apps': app_names}

        return {'results': dumps(results)}
    else:
        return {'results': None}


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


@view_config(route_name='get/fields', renderer='json')
def get_fields(request):
    for key in request.POST.keys():
        print(key)
    if 'apps[]' in request.POST:
        fields = set()
        apps = request.POST.getall('apps[]')
        db_actions = DatabaseActions

        for app in apps:
            _exp_name, _conf_name, _sim_name = app.split('/')[:3]
            filters = {'_exp_name': _exp_name, '_conf_name': _conf_name, '_sim_name': _sim_name}
            result = db_actions.get(request, 'applications', selection=filters)
            results = [dict(pn) for pn in result]

            for key, val in results[0].items():
                if key[0] != '_':
                    fields.add(key)

        return {'fields': sorted(list(fields))}

