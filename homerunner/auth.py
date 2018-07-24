import flask
import google.oauth2.credentials
from googleapiclient.discovery import build as build_service

def credentials_to_dict(credentials):
    return {'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes}


def get_user_google_account_info():
    """ Given oauth2 ``credentials``, retrieve the google user's id, email,
    name, and url of user's picture.

    Return: tuple of (id, email, name, picture_url)
    """
    credentials = google.oauth2.credentials.Credentials(
        **flask.session['credentials'])

    oauth2_service = build_service(serviceName='oauth2', version='v2',
                                   credentials=credentials)
    user_info = oauth2_service.userinfo().get().execute()

    return (user_info.get('id'),
            user_info.get('email'),
            user_info.get('name'),
            user_info.get('picture'))
