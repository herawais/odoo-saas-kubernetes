import json
import logging

import requests
import werkzeug
from odoo import http, api, SUPERUSER_ID, _
from odoo import registry as registry_get
from odoo.addons.auth_oauth.controllers.main import OAuthLogin, OAuthController, fragment_to_query_string
from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home
from odoo.addons.web.controllers.main import set_cookie_and_redirect, login_and_redirect, ensure_db
from odoo.exceptions import AccessDenied
from odoo.http import request
from werkzeug.exceptions import BadRequest

_logger = logging.getLogger(__name__)


class TTAuthLoginHome(Home):
    @http.route()
    def web_login(self, *args, **kw):
        ensure_db()
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            return request.redirect(request.params.get('redirect'))
        tt_providers = self.list_providers()

        response = super(OAuthLogin, self).web_login(*args, **kw)
        if response.is_qweb:
            error = request.params.get('oauth_error')
            if error == '1':
                error = _("You are not allowed to signup on this database.")
            elif error == '2':
                error = _("Access Denied")
            elif error == '3':
                error = _("Email Already Exist.\nPlease contact your Administrator.")
            elif error == '4':
                error = _("Validation End Point either Not present or invalid.\nPlease contact your Administrator")
            elif error == '5':
                error = _("Github Oauth Api Failed, For more information please contact Administrator")
            elif error == '6':
                error = _("Github Oauth Api Failed,\nClient ID or Client Secret Not present or has been compromised\n"
                          "For more information please contact Administrator")
            else:
                error = None
            response.qcontext['providers'] = tt_providers
            if error:
                response.qcontext['error'] = error

        return response


class TTGitHubOAuthController(OAuthController):

    @http.route('/tt/auth_oauth/signin', type='http', auth='none')
    @fragment_to_query_string
    def tt_signin(self, **kw):
        tt_state = json.loads(kw['state'])
        tt_user_data = json.loads((kw['user_data']))
        tt_dbname = tt_state['d']
        if not http.db_filter([tt_dbname]):
            return BadRequest()
        tt_provider = tt_state['p']
        tt_context = tt_state.get('c', {})
        tt_registry = registry_get(tt_dbname)
        with tt_registry.cursor() as cr:
            try:
                env = api.Environment(cr, SUPERUSER_ID, tt_context)
                validation = {
                    'user_id': tt_user_data.get('github_id'),
                    'email': tt_user_data.get('email') or tt_user_data.get('username'),
                    'name': tt_user_data.get('github_name') or tt_user_data.get("username"),
                }
                tt_login = env['res.users'].sudo()._auth_oauth_signin(tt_provider, validation, kw)
                tt_user = env['res.users'].sudo().search([('login', '=', tt_login)])
                tt_user.write({'git_username': tt_user_data.get('username'),
                               'git_email': tt_user_data.get("email")})
                tt_credentials = (request.env.cr.dbname, tt_login, kw.get('access_token'))
                cr.commit()
                tt_action = tt_state.get('a')
                tt_menu = tt_state.get('m')
                redirect = werkzeug.urls.url_unquote_plus(tt_state['r']) if tt_state.get('r') else False
                url = '/web'
                # Since /web is hardcoded, verify user has right to land on it
                if redirect:
                    url = redirect
                elif tt_action:
                    url = '/web#action=%s' % tt_action
                elif tt_menu:
                    url = '/web#menu_id=%s' % tt_menu
                resp = login_and_redirect(*tt_credentials, redirect_url=url)
                return resp
            except AttributeError:
                # auth_signup is not installed
                _logger.error("auth_signup not installed on database %s: oauth sign up cancelled." % (tt_dbname,))
                url = "/web/login?oauth_error=1"
            except AccessDenied:
                # oauth credentials not valid, user could be on a temporary session
                _logger.info('OAuth2: access denied, redirect to main page in case a valid session exists,\n'
                             'without setting cookies')
                url = "/web/login?oauth_error=3"
                redirect = werkzeug.utils.redirect(url, 303)
                redirect.autocorrect_location_header = False
                return redirect
            except Exception as e:
                # signup error
                _logger.exception("OAuth2: %s" % str(e))
                url = "/web/login?oauth_error=2"
        return set_cookie_and_redirect(url)


class TTOAuthLogin(OAuthLogin):

    def list_providers(self):
        try:
            tt_providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception:
            tt_providers = []
        for tt_provider in tt_providers:
            tt_state = self.get_state(tt_provider)
            if tt_provider.get('name') in ['GitHub', 'github']:
                params = dict(
                    client_id=tt_provider['client_id'],
                    scope=tt_provider['scope'],
                    state=json.dumps(tt_state),
                )
                tt_provider['auth_link'] = "%s?%s" % (tt_provider['auth_endpoint'], werkzeug.urls.url_encode(params))
            else:
                return_url = request.httprequest.url_root + 'auth_oauth/signin'
                params = dict(
                    response_type='token',
                    client_id=tt_provider['client_id'],
                    redirect_uri=return_url,
                    scope=tt_provider['scope'],
                    state=json.dumps(tt_state),
                )
                tt_provider['auth_link'] = "%s?%s" % (tt_provider['auth_endpoint'], werkzeug.urls.url_encode(params))
        return tt_providers


class TTCallbackHandler(http.Controller):

    @http.route(['/oauth/callback'], auth='public', csrf=False, methods=['GET', 'POST'], type='http')
    def get_oauth_token(self, **post):
        if post.get('state'):
            provider = request.env['auth.oauth.provider'].sudo().browse(json.loads(post.get('state')).get('p'))
        else:
            provider = request.env.ref('tt_github_oauth_app.tt_provider_github')
            provider = request.env[provider._name].sudo().browse(provider.id)
        tt_redirect_url = request.httprequest.url_root + "tt/auth_oauth/signin"
        if post.get("code"):
            client_id = provider.client_id
            client_secret = provider.tt_client_secret
            if not client_id or not client_secret:
                r_url = "/web/login?oauth_error=6"
                _logger.info(
                    'OAuth2: Either of Client ID or Client Secret not present, access denied, redirect to main page in case a valid session exists, without setting cookies')
                redirect = werkzeug.utils.redirect(r_url, 303)
                redirect.autocorrect_location_header = False
                return redirect
            data = {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": post.get("code")
            }
            url = provider.validation_endpoint  # "https://github.com/login/oauth/access_token"
            if "oauth" not in url:
                r_url = "/web/login?oauth_error=4"
                _logger.info(
                    'OAuth2: Validation Endpoint not presesnt, access denied, redirect to main page in case a valid session exists, without setting cookies')
                redirect = werkzeug.utils.redirect(r_url, 303)
                redirect.autocorrect_location_header = False
                return redirect
            response = requests.post(url, json=data)
            if response.status_code in [200, 201] and response.reason == 'OK':
                response_data = response.content.decode("UTF-8").split('&')
                if 'error=' in response_data or 'error=' in response_data[0]:
                    r_url = "/web/login?oauth_error=5"
                    _logger.info(
                        'OAuth2: access denied, redirect to main page in case a valid session exists, without setting cookies. REASON :- %s' % str(
                            response_data[0]))
                    redirect = werkzeug.utils.redirect(r_url, 303)
                    redirect.autocorrect_location_header = False
                    return redirect
                auth_token = response_data[0].split('=')[1]
                tt_user_data = requests.get('https://api.github.com/user', auth=('', auth_token)).json()
                # Todo: update the image of user in odoo
                params = {
                    'username': tt_user_data.get('login'),
                    'github_id': tt_user_data.get('id'),
                    'github_name': tt_user_data.get('name'),
                    'email': tt_user_data.get('email'),
                }
                tt_post_url = 'access_token=%s&state=%s&user_data=%s&provider=%s' % (
                    auth_token, post.get('state'), json.dumps(params), provider.id)
                tt_redirect_url = "%s?%s" % (tt_redirect_url, tt_post_url)
                return werkzeug.utils.redirect(tt_redirect_url)
