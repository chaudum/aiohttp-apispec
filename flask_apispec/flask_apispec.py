import copy
from pathlib import Path
from typing import Callable
from functools import partial

from apispec import APISpec
from apispec.core import VALID_METHODS_OPENAPI_V2
from apispec.ext.marshmallow import MarshmallowPlugin, common
from flask import Flask, make_response, jsonify, request, current_app
from jinja2 import Template
from webargs.flaskparser import parser

from .utils import get_path, get_path_keys

VALID_RESPONSE_FIELDS = {"description", "headers", "examples"}


def resolver(schema):
    schema_instance = common.resolve_schema_instance(schema)
    prefix = "Partial-" if schema_instance.partial else ""
    schema_cls = common.resolve_schema_cls(schema)
    name = prefix + schema_cls.__name__
    if name.endswith("Schema"):
        return name[:-6] or name
    return name


class FlaskApiSpec:
    def __init__(
        self,
        url="/api/docs/swagger.json",
        app=None,
        request_data_name="data",
        swagger_path=None,
        static_path='/static/swagger',
        error_callback=None,
        in_place=False,
        prefix='',
        **kwargs
    ):

        self.plugin = MarshmallowPlugin(schema_name_resolver=resolver)
        self.spec = APISpec(plugins=(self.plugin,), openapi_version="2.0", **kwargs)

        self.url = url
        self.swagger_path = swagger_path
        self.static_path = static_path
        self._registered = False
        self._request_data_name = request_data_name
        self.error_callback = error_callback
        self.prefix = prefix
        if app is not None:
            self.register(app, in_place)

    def swagger_dict(self):
        """ Returns swagger spec representation in JSON format """
        return self.spec.to_dict()

    def register(self, app: Flask, in_place: bool = False):
        """ Creates spec based on registered app routes and registers needed view """
        if self._registered is True:
            return None

        app._apispec_request_data_name = self._request_data_name

        if self.error_callback:
            parser.error_callback = self.error_callback
        app._apispec_parser = parser

        if in_place:
            self._register(app)
        else:
            app.before_first_request(partial(self._register, app))

        self._registered = True

        if self.url is not None:

            def swagger_handler():
                return current_app.swagger_dict

            app.add_url_rule(self.url, "swagger.spec", swagger_handler, methods=["GET"])

            if self.swagger_path is not None:
                self._add_swagger_web_page(app, self.static_path, self.swagger_path)

    def _add_swagger_web_page(self, app: Flask, static_path: str, view_path: str):
        static_files = Path(__file__).parent / "static"
        app.static_folder = str(static_files.resolve())
        print(app.static_folder, app.static_url_path)

        with open(str(static_files / "index.html")) as swg_tmp:
            tmp = Template(swg_tmp.read()).render(path=self.url, static=static_path)

        def swagger_view():
            response = make_response(tmp)
            response.headers["Content-Type"] = "text/html"
            return response

        app.add_url_rule(view_path, "swagger.docs", swagger_view, methods=["GET"])

    def _register(self, app: Flask):
        for rule in app.url_map.iter_rules():
            for method in rule.methods:
                if method in {"OPTIONS", "HEAD"}:
                    continue
                view = app.view_functions[rule.endpoint]
                print(method, rule)
                self._register_route(rule, method.lower(), view)
        app.swagger_dict = self.swagger_dict()

    def _register_route(self, route, method: str, view: Callable):
        if not hasattr(view, "__apispec__"):
            return None

        url_path = get_path(route)
        if not url_path:
            return None

        self._update_paths(view.__apispec__, method, self.prefix + url_path)

    def _update_paths(self, data: dict, method: str, url_path: str):
        if method not in VALID_METHODS_OPENAPI_V2:
            return None
        for schema in data.pop("schemas", []):
            parameters = self.plugin.converter.schema2parameters(
                schema["schema"], **schema["options"]
            )
            data["parameters"].extend(parameters)

        existing = [p["name"] for p in data["parameters"] if p["in"] == "path"]
        data["parameters"].extend(
            {"in": "path", "name": path_key, "required": True, "type": "string"}
            for path_key in get_path_keys(url_path)
            if path_key not in existing
        )

        if "responses" in data:
            responses = {}
            for code, actual_params in data["responses"].items():
                if "schema" in actual_params:
                    raw_parameters = self.plugin.converter.schema2parameters(
                        actual_params["schema"],
                        required=actual_params.get("required", False),
                    )[0]
                    updated_params = {
                        k: v
                        for k, v in raw_parameters.items()
                        if k in VALID_RESPONSE_FIELDS
                    }
                    updated_params['schema'] = actual_params["schema"]
                    for extra_info in ("description", "headers", "examples"):
                        if extra_info in actual_params:
                            updated_params[extra_info] = actual_params[extra_info]
                    responses[code] = updated_params
                else:
                    responses[code] = actual_params
            data["responses"] = responses

        operations = copy.deepcopy(data)
        self.spec.path(path=url_path, operations={method: operations})


def setup_flask_apispec(
    app: Flask,
    *,
    title: str = "API documentation",
    version: str = "0.0.1",
    url: str = "/api/docs/swagger.json",
    request_data_name: str = "data",
    swagger_path: str = None,
    static_path: str = '/static/swagger',
    error_callback=None,
    in_place: bool = False,
    prefix: str = '',
    **kwargs
) -> None:
    """
    flask-apispec extension.

    Usage:

    .. code-block:: python

        from flask_apispec import docs, request_schema, setup_flask_apispec
        from aiohttp import web
        from marshmallow import Schema, fields


        class RequestSchema(Schema):
            id = fields.Int()
            name = fields.Str(description='name')
            bool_field = fields.Bool()


        @docs(tags=['mytag'],
              summary='Test method summary',
              description='Test method description')
        @request_schema(RequestSchema)
        async def index(request):
            return web.json_response({'msg': 'done', 'data': {}})


        app = Flask(__name__)
        app.router.add_post('/v1/test', index)

        # init docs with all parameters, usual for ApiSpec
        setup_flask_apispec(app=app,
                            title='My Documentation',
                            version='v1',
                            url='/api/docs/api-docs')

        # now we can find it on 'http://localhost:8080/api/docs/api-docs'
        web.run_app(app)

    :param Flask app: Flask application instance
    :param str title: API title
    :param str version: API version
    :param str url: url for swagger spec in JSON format
    :param str request_data_name: name of the key in Request object
                                  where validated data will be placed by
                                  validation_middleware (``'data'`` by default)
    :param str swagger_path: experimental SwaggerUI support (starting from v1.1.0).
                             By default it is None (disabled)
    :param str static_path: path for static files used by SwaggerUI
                            (if it is enabled with ``swagger_path``)
    :param error_callback: custom error handler
    :param in_place: register all routes at the moment of calling this function
                     instead of the moment of the on_startup signal.
                     If True, be sure all routes are added to router
    :param prefix: prefix to add to all registered routes
    :param kwargs: any apispec.APISpec kwargs
    """
    FlaskApiSpec(
        url,
        app,
        request_data_name,
        title=title,
        version=version,
        swagger_path=swagger_path,
        static_path=static_path,
        error_callback=error_callback,
        in_place=in_place,
        prefix=prefix,
        **kwargs
    )
