from setuptools import setup

setup(
    name='homerunner',
    packages=['homerunner'],
    include_package_data=True,
    install_requires=[
        'flask',
        'google_auth_oauthlib',
        'pyopenssl',
        'bs4',
        'google-api-python-client',
    ],
)