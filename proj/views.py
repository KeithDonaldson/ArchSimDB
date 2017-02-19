from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid.interfaces import IBeforeRender
from pyramid.events import subscriber
from .reader import *
from .dbaccess import *
from .scanner import *
from bson.json_util import dumps
from collections import OrderedDict
import re
import ast

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


@view_config(route_name='delete', renderer='templates/delete.pt')
def delete(request):
    if request.method == 'POST':
        scanner = Scanner()
        db_actions = DatabaseActions()

        dbaccess_logs = db_actions.delete_all(request).get('logs')
        scanner.delete_tracking_file()
        scanner_logs = scanner.logs

        logs = scanner_logs + dbaccess_logs

        return {'logs': logs}
    else:
        return {}


@view_config(route_name='view', renderer='templates/view.pt')
def view(request):
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


@view_config(route_name='get/hierarchy', renderer='json')
def get_hierarchy(request):
    db_actions = DatabaseActions()
    data_hierarchy = db_actions.get_hierarchy(request)

    return data_hierarchy


@view_config(route_name='compare_results_permalink', renderer='templates/compare_results.pt')
def compare_results_permalink(request):
    stats = request.matchdict['stats'].replace(';', '/').split(',')
    apps = request.matchdict['apps'].replace(';', '/').split(',')

    data = {'stats': stats, 'apps': apps}

    return compare_results(request, from_permalink=True, permalink_data=data)


@view_config(route_name='compare_results', renderer='templates/compare_results.pt')
def compare_results(request, from_permalink=False, permalink_data=None):
    if 'fields[]' in request.POST or from_permalink is True:

        # Instantiate the necessary classes
        db_actions = DatabaseActions()
        scanner = Scanner()

        # Get the list of fields (stats) and applications (apps) from the post data OR permalink
        if from_permalink is True and permalink_data:
            fields = permalink_data.get('stats')
            apps = permalink_data.get('apps')
        else:
            fields = request.POST.getall('fields[]')
            apps = request.POST.getall('apps[]')

        # Instantiate some data structures
        warnings = []
        workloads = set()
        configs = set()
        projection_set = [x for x in fields if not x[0] == '$'] + ['_exp_name', '_conf_name']
        composite_stats = scanner.get_composite_stats()
        results = {}

        # For each application, we get the chosen stats
        for app in apps:

            # Gather the required information from the application
            _exp_name, _conf_name, _sim_name = app.split('/')[:3]
            workloads.add(_sim_name)
            configs.add(_exp_name + '/' + _conf_name)
            filters = {'_exp_name': _exp_name, '_conf_name': _conf_name, '_sim_name': _sim_name}

            # DATABASE CALL #
            # Query the database for the requested data
            result = db_actions.get(request, 'applications', selection=filters, projection=projection_set)[0]

            # If a composite stat was chosen, caclulate the value
            for field in fields:
                if field[0] == '$':
                    equation = composite_stats.get('stats').get(field[1:]).strip()
                    variables = re.findall('{.*?}', equation)

                    for var in variables:
                        variables[variables.index(var)] = var.replace('{', '').replace('}', '')

                    composite_result = db_actions.get(request, 'applications', selection=filters, projection=variables)[0]

                    for var in variables:
                        equation = equation.replace('{' + var + '}', str(composite_result.get(var)))

                    try:
                        composite_stat_output = eval(equation, {"__builtins__": None}, {})
                        result[field] = composite_stat_output
                    except TypeError:
                        log.warning("Composite stat failed to evaluate due to unfound variables. Make sure that the "
                                    "simulation data used contains the required fields for " + field + " in the "
                                    "application " + app)
                        warnings.append("Composite stat failed to evaluate due to unfound variables. Make sure that the"
                                        " simulation data used contains the required fields for " + field + " in the "
                                        "application " + app)

            # Add the requested data from this application to the overall data
            results[app] = result

        # Sort the column and row headings. Unnecessary, but makes for easier reading on results page
        workloads = sorted(workloads)
        configs = sorted(configs)
        data = {}

        # For each stat, return a list of lists to represent a table of values
        for field in fields:
            rows = []

            # Set up the list of lists
            for workload in workloads:
                rows.append([workload[:20]])

            # For each cell, find the value in the results if it exists
            for config in configs:
                for i, workload in enumerate(workloads):
                    result = results.get(config + '/' + workload)
                    if result:
                        if field in result:
                            rows[i].append(result.get(field))
                        else:
                            rows[i].append(None)
                    else:
                        rows[i].append(None)

            # Add the array of data for this field to the return dictionary
            data[field] = rows

        # Set up the return dictionary with all information
        results = {'data': data, 'configs': configs, 'stats': fields, 'apps': apps}

        if from_permalink is True:
            results['from_permalink'] = True
        else:
            results['from_permalink'] = False

        return_data = {'results': dumps(results)}

        if len(warnings) != 0:
            return_data['warnings'] = warnings

        return return_data
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


@view_config(route_name='get/experiments', renderer='json')
def get_experiments(request):
    db_actions = DatabaseActions()
    exps = db_actions.get(request, 'experiments')
    exp_dict = [dict(pn) for pn in exps]

    return dumps(exp_dict)


@view_config(route_name='get/fields', renderer='json')
def get_fields(request):
    if 'apps[]' in request.POST:
        fields = set()
        apps = request.POST.getall('apps[]')
        db_actions = DatabaseActions
        scanner = Scanner()

        for app in apps:
            _exp_name, _conf_name, _sim_name = app.split('/')[:3]
            filters = {'_exp_name': _exp_name, '_conf_name': _conf_name, '_sim_name': _sim_name}
            result = db_actions.get(request, 'applications', selection=filters)
            results = [dict(pn) for pn in result]

            for key, val in results[0].items():
                if key[0] != '_':
                    fields.add(key)

        composite_stats = scanner.get_composite_stats()

        for key, value in composite_stats.get('stats').items():
            fields.add('$' + key)

        return {'fields': sorted(list(fields))}

