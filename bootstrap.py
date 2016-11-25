'''
Derek Merck <derek_merck@brown.edu>
Vanessa Sochat <vsochat@stanford.edu>
Spring 2016

The Medical Image Informatics Platform Bootstrapper

Utility scripts for cleaning and setting up config for docker-compose defined MIIP services.
'''

import argparse
import logging
from jinja2 import Environment, FileSystemLoader
import os
import pprint
import re
import subprocess
import yaml


__version__ = "0.2"
__description__ = "Utility scripts for cleaning and setting up config for docker-compose defined MIIP services."

# TODO: If forward in orthanc env, modify and copy the autorouter lua
# TODO: Better setup of Docker env vars or use Docker python API

def parse_args():
    parser = argparse.ArgumentParser(prog='MIIP Bootstrapper', description=__description__)

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s (version ' + __version__ + ')')

    parser.add_argument('--clean', action='store_true')
    parser.add_argument('services', nargs="+",
                        choices=['orthanc', 'orthanc-receiver', 'xnat'])

    _opts = parser.parse_args()
    return _opts


def parse_template(template_file, out_file, env):
    '''parse_template will take a template file and an output
    file, and parse variables from the environment into it
    '''
    jinja = Environment(loader=FileSystemLoader('.'))
    template = jinja.get_template(template_file)
    env['globals'] = global_env
    parsed_template = template.render(env)
    # logging.debug(output_from_parsed_template)
    with open(out_file, "w") as fh:
        fh.write(parsed_template)


def get_container_id(name):
    '''get_container_id will return the docker container id of a running container,
    based on the name in the compose file
    :param name: the name of the docker-compose container (eg, postgres)
    '''
    cmd = subprocess.Popen(['docker-compose','ps','-q',name],
                           stdout=subprocess.PIPE)
    container_id = cmd.stdout.read().decode('utf-8').strip('\n')
    logging.debug("Container id found for %s as %s", name, container_id)
    return container_id


def exec_sql(sql,postgres_container):
    p = ['docker', 'exec', postgres_container, 'psql', '-c', sql, '-U', 'postgres']
    subprocess.call(p)


def add_postgres_database(user,database_name,postgres_container):
    '''add_postgres_database will take a database name, username
    and send a command to docker-compose to parse
    :param user: the user to create the database for
    :param database_name: the name of the database to create
    '''
    sql = "CREATE DATABASE {DB_NAME} WITH OWNER {DB_USER}".format(
        DB_USER=user,
        DB_NAME=database_name)
    exec_sql(sql,postgres_container)
    exec_sql("\l",postgres_container)


def drop_postgres_database(database_name,postgres_container):
    '''drop_postgres_database will drop the database
    :param database_name: the name of the database
    :param postgres_container: the postgres_container to use
    '''
    sql = "DROP DATABASE {DB_NAME}".format(
        DB_NAME=database_name)
    exec_sql(sql,postgres_container)
    exec_sql("\l",postgres_container)


def drop_postgres_user(user,postgres_container):

    # # List roles in DB
    # exec_sql("\du")
    #
    sql = "DROP USER {DB_USER}".format(
        DB_USER=user)
    exec_sql(sql,postgres_container)
    #
    # # List revised roles in DB
    # exec_sql("\du")


def add_postgres_user(user,password,postgres_container):

    # # List roles in DB
    # exec_sql("\du")

    sql = "CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}'".format(
        DB_USER=user,
        DB_PASSWORD=password)
    exec_sql(sql,postgres_container)

    sql = "ALTER USER {DB_USER} WITH CREATEDB".format(
        DB_USER=user)

    exec_sql(sql,postgres_container)

    # List revised roles in DB
    exec_sql("\du",postgres_container)


def setup_orthanc(env, postgres_container, **kwargs):

    add_postgres_user(user=env['environment']['DB_USER'],
                      password=env['environment']['DB_PASSWORD'],
                      postgres_container=postgres_container)

    add_postgres_database(user=env['environment']['DB_USER'],
                          database_name=env['environment']['DB_NAME'],
                          postgres_container=postgres_container)

    # Create the config file

    # Figure out where the data dir belongs
    for f in env['volumes']:
        if re.search("^data:",f):
            env['DATA_DIR'] = f.split(":")[1]

    # Figure out where to output the config file
    for f in env['volumes']:
        if re.search('shadow',f):
            out_file = f.split(":")[0]

    # Create it
    parse_template('orthanc.template.json', out_file, env)


def setup_xnat(env, postgres_container, **kwargs):

    add_postgres_user(user=env['environment']['DB_USER'],
                      password=env['environment']['DB_PASSWORD'],
                      postgres_container=postgres_container)
    # No need to create the database itself; the xnat builder insists on creating it

    # Create the config file
    parse_template('xnat-docker/xnat.config.template', 'xnat-docker/xnat.shadow.config', env)

    # TODO: Build and tag the xnat template image for docker-compose if it doesn't exist
    # TODO: Allow build even if the database already exists <https://github.com/chaselgrove/xnat-docker/issues/2>


def clean_db(env,postgres_container):
    drop_postgres_database(env,postgres_container)
    drop_postgres_user(env,postgres_container)


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    logging.debug("MIIP Bootstrapper v{version}".format(version=__version__))

    opts = parse_args()

    with open("docker-compose.yml", 'r') as f:
        env = yaml.load(f)

    logging.info(pprint.pformat(env))

    # Get the running container id
    postgres_container = get_container_id(name='postgres')

    # Get the DB host and port
    global_env = {}
    global_env['DB_HOST'] = 'postgres'
    global_env['DB_PORT'] = 5432

    # Do we want to clean database?
    if opts.clean:
        if 'orthanc' in opts.services:
            clean_db(env['orthanc'],postgres_container)
        if 'orthanc-receiver' in opts.services:
            clean_db(env['orthanc-receiver'],postgres_container)
        if 'xnat' in opts.services:
            clean_db(env['xnat'],postgres_container)


    if 'orthanc' in opts.services:
        setup_orthanc(env['orthanc'],postgres_container)

    if 'orthanc-receiver' in opts.services:
        setup_orthanc(env['orthanc-receiver'],postgres_container)

    if 'xnat' in opts.services:
        setup_xnat(env['xnat'],postgres_container)
