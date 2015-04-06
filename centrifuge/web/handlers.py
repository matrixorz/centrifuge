# coding: utf-8
# Copyright (c) Alexandr Emelin. MIT license.

import six
import uuid
import functools
import tornado.web
import tornado.escape
import tornado.auth
import tornado.httpclient
import tornado.gen
from tornado.gen import coroutine, Return
from tornado.web import decode_signed_value
from tornado.websocket import WebSocketHandler

import centrifuge
from centrifuge.log import logger
from centrifuge.utils import json_encode, json_decode
from centrifuge.handlers import BaseHandler


def authenticated(method):
    """
    Decorate methods with this to require that the user be logged in.
    As we serve single page app we use our own authenticated decorator
    to just return 401 response code
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            raise tornado.web.HTTPError(401)
        return method(self, *args, **kwargs)
    return wrapper


class WebBaseHandler(BaseHandler):

    def get_current_user(self):
        if not self.opts.get("password"):
            return "authorized"
        auth_header = self.request.headers.get(
            "Authorization", "").split(" ")[-1]
        return decode_signed_value(
            self.application.settings['cookie_secret'],
            'token',
            auth_header
        )


class AuthHandler(BaseHandler):

    def post(self):
        password = self.get_argument("password", None)
        if password and password == self.opts.get("password"):
            token = self.create_signed_value("token", "authorized")
            self.set_header("Content-Type", "application/json")
            self.finish(json_encode({
                "token": token
            }))
        else:
            raise tornado.web.HTTPError(400)


def params_from_request(request):
    return dict(
        (
            k,
            ''.join([x.decode('utf-8') for x in v])
        ) for k, v in six.iteritems(request.arguments)
    )


class InfoHandler(WebBaseHandler):

    @authenticated
    def get(self):
        config = self.application.settings.get('config', {})
        metrics_interval = config.get('metrics', {}).get(
            'interval', self.application.METRICS_EXPORT_INTERVAL)*1000
        context = {
            'structure':  self.application.structure,
            'structure_dict': self.application.structure_dict,
            'metrics_interval': metrics_interval,
            'version': centrifuge.__version__,
            'node_count': len(self.application.nodes) + 1,
            'engine': getattr(self.application.engine, 'NAME', 'unknown'),
            'node_name': self.application.name
        }
        self.set_header("Content-Type", "application/json")
        self.finish(json_encode(context))


class ActionHandler(WebBaseHandler):

    @authenticated
    def post(self):
        result, error = {}, None
        self.set_header("Content-Type", "application/json")
        self.finish(json_encode({
            "body": result,
            "error": error
        }))


class ProjectDetailHandler(WebBaseHandler):

    @coroutine
    def get_project(self, project_name):
        project = self.application.structure_dict.get(project_name)
        if not project:
            raise tornado.web.HTTPError(404)
        raise Return((project, None))

    @coroutine
    def get_credentials(self):
        data = {
            'user': self.current_user,
            'project': self.project,
        }
        raise Return((data, None))

    @coroutine
    def get_actions(self):
        data, error = yield self.get_credentials()
        raise Return((data, None))

    @coroutine
    def post_actions(self):
        params = params_from_request(self.request)
        method = params.pop('method')
        params.pop('_xsrf')
        data = params.get('data', None)
        if data is not None:
            try:
                data = json_decode(data)
            except Exception as e:
                logger.error(e)
            else:
                params["data"] = data

        result, error = yield self.application.process_call(self.project, method, params)

        self.set_header("Content-Type", "application/json")
        self.finish(json_encode({
            "body": result,
            "error": error
        }))

    @authenticated
    @coroutine
    def get(self, project_name, section):

        self.project, error = yield self.get_project(project_name)

        if section == 'credentials':
            template_name = 'project/detail_credentials.html'
            func = self.get_credentials

        elif section == 'actions':
            template_name = 'project/detail_actions.html'
            func = self.get_actions

        else:
            raise tornado.web.HTTPError(404)

        data, error = yield func()

        self.render(template_name, **data)

    @authenticated
    @coroutine
    def post(self, project_name, section):
        self.project, error = yield self.get_project(
            project_name
        )
        if section == 'actions':
            yield self.post_actions()
        else:
            raise tornado.web.HTTPError(404)


class AdminWebSocketHandler(WebSocketHandler):

    def __init__(self, *args, **kwargs):
        super(AdminWebSocketHandler, self).__init__(*args, **kwargs)
        self.uid = None

    @coroutine
    def subscribe(self):
        self.uid = uuid.uuid4().hex
        self.application.add_admin_connection(self.uid, self)
        logger.info('admin connected')

    def unsubscribe(self):
        if not self.uid:
            return
        self.application.remove_admin_connection(self.uid)
        logger.info('admin disconnected')

    def open(self):
        try:
            value = "123"
        except (KeyError, AttributeError):
            self.close()
        else:
            user = "1" #= decode_signed_value(
            #    self.application.settings['cookie_secret'], 'token', value
            #)
            if user:
                self.subscribe()
            else:
                self.close()

    def on_message(self, message):
        pass

    def on_close(self):
        self.unsubscribe()

    send = WebSocketHandler.write_message