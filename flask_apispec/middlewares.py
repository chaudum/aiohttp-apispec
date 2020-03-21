from flask import request, current_app, g


def validation_middleware():
    """
    Validation middleware

    Usage:

    .. code-block:: python

        app.before_request(validation_middleware)
    """
    name, params = current_app.url_map.bind("", "/").match(request.path, request.method)
    orig_handler = current_app.view_functions[name]
    if not hasattr(orig_handler, "__schemas__"):
        sub_handler = getattr(orig_handler, request.method.lower(), None)
        if sub_handler is None:
            return
        if not hasattr(sub_handler, "__schemas__"):
            return
        schemas = sub_handler.__schemas__
    else:
        schemas = orig_handler.__schemas__
    result = {}
    for schema in schemas:
        data = current_app._apispec_parser.parse(
            schema["schema"], request, locations=schema["locations"]
        )
        if schema["put_into"]:
            setattr(g, schema["put_into"], data)
        elif data:
            try:
                result.update(data)
            except (ValueError, TypeError):
                result = data
                break
    setattr(g, current_app._apispec_request_data_name, result)
