from pyramid.config import Configurator
from urllib.parse import urlparse
from gridfs import GridFS
from pymongo import MongoClient


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_chameleon')
    config.add_static_view('static', 'static', cache_max_age=3600)

    db_url = urlparse(settings['mongo_uri'])
    config.registry.db = MongoClient(
        host=db_url.hostname,
        port=db_url.port,
    )

    def add_db(request):
        db = config.registry.db[db_url.path[1:]]
        if db_url.username and db_url.password:
            db.authenticate(db_url.username, db_url.password)
        return db

    def add_fs(request):
        return GridFS(request.db)

    config.add_request_method(add_db, 'db', reify=True)
    config.add_request_method(add_fs, 'fs', reify=True)

    config.add_route('home', '/')
    config.add_route('upload', '/add/application')
    config.add_route('add/configuration', '/add/configuration')
    config.add_route('upload_processor', '/upload_processor')
    config.add_route('applications', '/applications')
    config.add_route('configurations', '/configurations')
    config.add_route('experiments', '/experiments')
    config.add_route('flot', '/flot')
    config.add_route('sync', '/sync')
    config.add_route('query', '/query')
    config.add_route('get/configurations', '/get/configurations')
    config.add_route('get/applications', '/get/applications')
    config.add_route('get/experiments', '/get/experiments')
    config.add_route('get/fields', '/get/fields')
    config.add_route('compare', '/compare')
    config.add_route('compare_results', '/compare/results')
    config.add_route('app_info', '/data/{_exp_name}/{_conf_name}/{_sim_name}')

    config.scan()
    return config.make_wsgi_app()
