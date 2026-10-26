MIN_JS_RUNTIME_VERSIONS = {'deno': (2, 3, 0), 'node': (22, 0, 0)}


def javascript_options() -> dict:
    """Enable Deno and Node.js for YouTube challenges, with EJS script fallback."""
    return {
        'js_runtimes': {name: {} for name in MIN_JS_RUNTIME_VERSIONS},
        'remote_components': ['ejs:github'],
    }
