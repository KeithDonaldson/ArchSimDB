from pyramid.view import view_config
from pyramid.renderers import get_renderer
from pyramid.interfaces import IBeforeRender
from pyramid.events import subscriber
from .dbaccess import *
from .scanner import *
from bson.json_util import dumps
import re

import logging
log = logging.getLogger(__name__)


# PAGE STRUCTURE IS AS FOLLOWS:
# |- Home
#  \  Search Database*
#   |- View
#    \
#     |- Data**
#   |- List of Experiments
#   |- List of Configurations
#   |- List of Applications
# |- Compare
#  \
#   |- Compare Results**
# |- Sync
# |- Delete
#
# * Not a page, just a menu item
# ** Not in the navigation menu


# --------------------------- #
# --- Human-visible pages --- #
# --------------------------- #

# - MASTER TEMPALTE
@subscriber(IBeforeRender)
def globals_factory(event):
    master = get_renderer('templates/master.pt').implementation()
    event['master'] = master

    config = configparser.ConfigParser()
    config.read_file(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'development.ini')))

    event['user'] = config.get('app:config', 'user')


# - INDEX PAGE
@view_config(route_name='home', renderer='templates/index.pt')
def home(request):
    """
    Returns the counts in the three collections for the `Home` page

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with the counts in the database
    :rtype: dict
    """

    info = DatabaseInfo()
    exp_cnt = info.get_experiment_count(request)
    conf_cnt = info.get_configuration_count(request)
    app_cnt = info.get_applications_count(request)

    return {'exp_cnt': exp_cnt, 'conf_cnt': conf_cnt, 'app_cnt': app_cnt}


# - VIEW PAGE
@view_config(route_name='view', renderer='templates/view.pt')
def view(request):
    """
    Returns the experiments in the database for the `View` page

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with the experiments in the database
    :rtype: dict
    """

    db_actions = DatabaseActions()
    all_experiments = db_actions.get(request, 'experiments')
    exp_dict = [dict(pn) for pn in all_experiments]

    for exp in exp_dict:
        for key, val in exp.items():
            if key == '_exp_date':
                exp[key] = val.strftime("%Y-%m-%d")

    return {'experiments': dumps(exp_dict)}


# - DATA PAGE
@view_config(route_name='data', renderer='templates/data.pt')
def data(request):
    """
    Returns the data for a single application in the database for the 'Data' page

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with the data from a single application
    :rtype: dict
    """

    db_actions = DatabaseActions()
    _exp_name = request.matchdict['_exp_name']
    _conf_name = request.matchdict['_conf_name']
    _sim_name = request.matchdict['_sim_name']

    raw_data = db_actions.get(request, 'applications', {'_exp_name': _exp_name, '_conf_name': _conf_name,
                                                        '_sim_name': _sim_name})

    try:
        dict_data = [dict(pn) for pn in raw_data][0]
        sim_name = dict_data.get('_sim_name')[:20]

        list_data = []

        for (key, val) in dict_data.items():
            if key[0] != '_':
                list_data.append({'key': key, 'value': val})

        return {'data': list_data, '_sim_name': sim_name}
    except IndexError:
        return {'data': {}, '_sim_name': 'Not Found'}


# - LIST OF EXPERIMENTS PAGE
@view_config(route_name='experiments', renderer='templates/experiments.pt')
def experiments(request):
    """
    Returns all of the experiments in the database for the 'List of Experiments' page

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with all of the experiments in the database
    :rtype: dict
    """

    db_actions = DatabaseActions()
    all_experiments = db_actions.get(request, 'experiments')
    exp_dict = [dict(pn) for pn in all_experiments]

    for exp in exp_dict:
        for key, val in exp.items():
            if key == '_exp_date':
                exp[key] = val.strftime("%Y-%m-%d")  # Convert the Python datetime to a string for display

    return {'experiments': dumps(exp_dict)}


# - LIST OF CONFIGURATIONS PAGE
@view_config(route_name='configurations', renderer='templates/configurations.pt')
def configurations(request):
    """
    Returns all of the configurations in the database for the 'List of Configurations' page

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with all of the configurations in the database
    :rtype: dict
    """

    db_actions = DatabaseActions()
    all_configurations = db_actions.get(request, 'configurations')
    conf_dict = [dict(pn) for pn in all_configurations]

    for conf in conf_dict:
        for key, val in conf.items():
            if key == '_conf_date':
                conf[key] = val.strftime("%Y-%m-%d")  # Convert the Python datetime to a string for display

    return {'configurations': dumps(conf_dict)}


# - LIST OF APPLICATIONS PAGE
@view_config(route_name='applications', renderer='templates/applications.pt')
def applications(request):
    """
    Returns all of the applications in the database for the 'List of Applications' page

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with all of the applications in the database
    :rtype: dict
    """

    db_actions = DatabaseActions()
    all_applications = db_actions.get(request, 'applications', projection=['_sim_name', '_sim_owner', '_sim_date',
                                                                           '_exp_name', '_conf_name'])
    app_dict = [dict(pn) for pn in all_applications]

    for app in app_dict:
        for key, val in app.items():
            if key == '_sim_date':
                app[key] = val.strftime("%Y-%m-%d")  # Convert the Python datetime to a string for display

    return {'applications': dumps(app_dict)}


# - COMPARE PAGE
@view_config(route_name='compare', renderer='templates/compare.pt')
def compare(request):
    """
    Returns a hierarchical view of the database for jstree for the 'Compare' page

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with all of the experiments in the database
    :rtype: dict
    """

    db_actions = DatabaseActions()
    data_hierarchy = db_actions.get_hierarchy(request)

    return {'hierarchy': dumps(data_hierarchy)}


# - COMPARE RESULTS PAGE (FROM PERMALINK)
@view_config(route_name='compare_results_permalink', renderer='templates/compare_results.pt')
def compare_results_permalink(request):
    """
    Returns the requested data in a tabular format for the `compare/results` page if
    directed from a permalink and not a POST from the `compare` page.

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary containing the requsted data
    :rtype: dict
    """

    stats = request.matchdict['stats'].replace(';', '/').split(',')
    apps = request.matchdict['apps'].replace(';', '/').split(',')

    permalink_data = {'stats': stats, 'apps': apps}

    return compare_results(request, permalink_data=permalink_data)


# - COMPARE RESULTS PAGE (FROM POST ON `COMPARE` PAGE)
@view_config(route_name='compare_results', renderer='templates/compare_results.pt')
def compare_results(request, permalink_data=None):
    """
    Returns the requested data in a tabular format for the `compare/results` page.

    :param request: The Pyramid request object
    :type request: Request

    :param permalink_data: The parsed data from the permalink if it exists
    :type permalink_data: dict

    :return: A dictionary containing the requsted data
    :rtype: dict
    """

    if 'fields[]' in request.POST or permalink_data:

        # - Instantiate the necessary classes
        db_actions = DatabaseActions()
        scanner = Scanner()

        # - Get the list of fields (stats) and applications (apps) from the post data OR permalink
        if permalink_data:
            fields = permalink_data.get('stats')
            apps = permalink_data.get('apps')
        else:
            fields = request.POST.getall('fields[]')
            apps = request.POST.getall('apps[]')

        config = configparser.ConfigParser()
        config.read_file(open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'development.ini')))
        workload_separator = config.get('app:config', 'workload_separator')

        if workload_separator == 'None':
            workload_separator = None

        warnings = []
        workloads = set()
        configs = set()
        projection_set = [x for x in fields if not x[0] == '$'] + ['_exp_name', '_conf_name']
        composite_stats = scanner.get_composite_stats()
        results = {}

        # - For each application, we get the chosen stats
        for app in apps:

            # - Gather the required information from the application
            _exp_name, _conf_name, _sim_name = app.split('/')[:3]

            workload = _sim_name.split(workload_separator)[0]
            config = _exp_name + '/' + _conf_name

            workloads.add(workload)
            configs.add(config)
            filters = {'_exp_name': _exp_name, '_conf_name': _conf_name, '_sim_name': _sim_name}

            # - DATABASE CALL #
            # - Query the database for the requested data
            result = db_actions.get(request, 'applications', selection=filters, projection=projection_set)[0]

            # - If a composite stat was chosen, caclulate the value
            for field in fields:
                if field[0] == '$':
                    equation = composite_stats.get('stats').get(field[1:]).strip()
                    variables = re.findall('{.*?}', equation)

                    for var in variables:
                        variables[variables.index(var)] = var.replace('{', '').replace('}', '')

                    composite_result = db_actions.get(request, 'applications',
                                                      selection=filters, projection=variables)[0]

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

            results[config + '/' + workload] = result

        # - Sort the column and row headings. Unnecessary, but makes for easier reading on results page
        workloads = sorted(workloads)
        configs = sorted(configs)
        return_data = {}

        # - For each stat, return a list of lists to represent a table of values
        for field in fields:
            rows = []

            for workload in workloads:
                rows.append([workload[:20]])

            # - For each cell, find the value in the results if it exists
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

            return_data[field] = rows

        results = {'data': return_data, 'configs': configs, 'stats': fields, 'apps': apps}

        # Data is dealt with slightly differently on the front-end if parsed from the
        # URL, so we need to set a flag
        if permalink_data:
            results['from_permalink'] = True
        else:
            results['from_permalink'] = False

        return_data = {'results': dumps(results)}

        if len(warnings) != 0:
            return_data['warnings'] = warnings

        return return_data
    else:
        return {'results': None}


# - SYNC PAGE
@view_config(route_name='sync', renderer='templates/sync.pt')
def sync(request):
    """
    Scans for new or changed statfiles and updates the database accordingly.

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with a number of inserts and the syncing logs
    :rtype: dict
    """

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


# - DELETE PAGE
@view_config(route_name='delete', renderer='templates/delete.pt')
def delete(request):
    """
    Deletes all of the content in the database and the tracking file.

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with the deletion logs
    :rtype: dict
    """

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


# - COMPOSITE STATS PAGE
@view_config(route_name='composite_stats', renderer='templates/composite_stats.pt')
def composite_stats(request):
    """
    Loads and sets the composite stats from file.

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with the deletion logs
    :rtype: dict
    """

    if request.method == 'POST':
        post = request.POST.get('composite_stats_area')
        stats = post.split("\r\n")

        scanner = Scanner()
        logs = scanner.set_composite_stats(stats)

        stats = scanner.get_composite_stats(raw=True)

        return {'composite_stats': stats, 'logs': logs}
    else:
        scanner = Scanner()
        stats = scanner.get_composite_stats(raw=True)
        return {'composite_stats': stats}

# --------------------------- #
# -- POST and GET requests -- #
# --------------------------- #


@view_config(route_name='get/experiments', renderer='json')
def get_experiments(request):
    """
    Returns a dictionary of all experiments in the database

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary containing all experiments
    :rtype: dict
    """

    db_actions = DatabaseActions()
    exps = db_actions.get(request, 'experiments')
    exp_dict = [dict(pn) for pn in exps]

    return dumps(exp_dict)


@view_config(route_name='get/configurations', renderer='json')
def get_configurations(request):
    """
    Returns a dictionary of all configurations in the database

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary containing all configurations
    :rtype: dict
    """

    if '_exp_name' in request.POST:
        filters = {'_exp_name': request.POST.get('_exp_name')}
        db_actions = DatabaseActions

        confs = db_actions.get(request, 'configurations', selection=filters)
        conf_dict = [dict(pn) for pn in confs]

        for conf in conf_dict:
            for key, val in conf.items():
                if key == '_conf_date':
                    conf[key] = val.strftime("%Y-%m-%d")  # Convert the Python datetime to a string for display

        return dumps(conf_dict)


@view_config(route_name='get/applications', renderer='json')
def get_applications(request):
    """
    Returns a dictionary of all applications in the database

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary containing all applications
    :rtype: dict
    """

    if '_conf_name' in request.POST:
        filters = {'_conf_name': request.POST.get('_conf_name'), '_exp_name': request.POST.get('_exp_name')}
        db_actions = DatabaseActions

        apps = db_actions.get(request, 'applications', selection=filters,
                              projection=['_sim_name', '_sim_owner', '_sim_date', '_exp_name', '_conf_name'])
        app_dict = [dict(pn) for pn in apps]

        for app in app_dict:
            for key, val in app.items():
                if key == '_sim_date':
                    app[key] = val.strftime("%Y-%m-%d")  # Convert the Python datetime to a string for display

        return dumps(app_dict)


@view_config(route_name='get/fields', renderer='json')
def get_fields(request):
    """
    Gets the union of the fields from a set of applications

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary containing all fields
    :rtype: dict
    """

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
                if key[0] != '_':                # Fields starting with an underscore are metadata
                    fields.add(key)

        composite_stats = scanner.get_composite_stats()

        for key, value in composite_stats.get('stats').items():
            fields.add('$' + key)                # Composite stats are signified with a dollar sign at the start

        return {'fields': sorted(list(fields))}


@view_config(route_name='get/hierarchy', renderer='json')
def get_hierarchy(request):
    """
    Returns a hierarchical view of the data in the database for jstree

    :param request: The Pyramid request object
    :type request: Request

    :return: A dictionary with a hierarchical structure for jstree
    :rtype: dict
    """

    db_actions = DatabaseActions()
    data_hierarchy = db_actions.get_hierarchy(request)

    return data_hierarchy
