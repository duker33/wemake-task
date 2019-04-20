import os
import requests
from pyramid.config import Configurator
from pyramid.response import Response
from waitress import serve

CLIENT_ID = os.environ['WEMAKE_CLIENT_ID']
CLIENT_SECRET = os.environ['WEMAKE_CLIENT_SECRET']

AUTHOR = 'https://github.com/duker33'
CODE_URL = 'https://github.com/duker33/wemake-task'

HTML = """
<html>
    <head>
        <style>.username {{ width: 100px; text-align: center; padding-top: 5px; }}</style>
    </head>
    <body>
        <h1>Your repositories</h1>
        <img src="{avatar_url}" class="avatar" width="100px" height="100px" />
        <div class="username">{username}</div>
        {repos}
        <p>Created by <a href="{author}">{author}</a>, source code: <a href="{code_url}">{code_url}</a></p>
    </body>
</html>
"""

REPOS_LIST = '<ul>{repos}</ul>'

REPOS_ITEM = '<li><a href={url}>{name}</a></li>'

LOGIN_FORM = """
<form action="https://github.com/login/oauth/authorize">
    <input type="hidden" name="client_id" value={client_id}>
    <input type="submit" value="GitHub login">
</form>
""".format(client_id=CLIENT_ID)


class ResponseDataError(Exception):
    pass


def get_access_token(code: str) -> str:
    response = requests.post(
        'https://github.com/login/oauth/access_token',
        headers={'Accept': 'application/json'},
        data={'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'code': code}
    )
    json = response.json()
    access_token = json.get('access_token')
    if not access_token:
        raise ResponseDataError('Failed to receive access token. Error from github:', json.get('error_description'))
    return access_token
    
    
def get_user_data(access_token: str) -> dict:
    user = requests.get(
        'https://api.github.com/user',
        headers={'Authorization': 'token {}'.format(access_token)}
    ).json()
    repos = requests.get(
        'https://api.github.com/user/repos',
        headers={'Authorization': 'token {}'.format(access_token)}
    ).json()
    return {
        'username': user['login'],
        'avatar_url': user['avatar_url'],
        'repos': [{'name': r['name'], 'url': r['url']} for r in repos]
    }
    
def render_repos(repos: dict) -> str:
    return REPOS_LIST.format(
        repos='\n'.join(REPOS_ITEM.format(**repo) for repo in repos)
    )
    

def index(request):
    code = request.params.get('code')
    if code:
        # after auth redirect from github
        try:
            token = get_access_token(code)
        except ResponseDataError:
            return Response(status_code=302, location='/')
        user_data = get_user_data(token)
        return Response(HTML.format(
            username=user_data['username'],
            avatar_url=user_data['avatar_url'],
            repos=render_repos(user_data['repos']),
            author=AUTHOR,
            code_url=CODE_URL,
        ))
    else:
        # user enters the page for the first time
        return Response(LOGIN_FORM)


if __name__ == '__main__':
    with Configurator() as config:
        config.add_route('index', '/')
        config.add_view(index, route_name='index')
        app = config.make_wsgi_app()
    serve(app, host='0.0.0.0', port=6543)
