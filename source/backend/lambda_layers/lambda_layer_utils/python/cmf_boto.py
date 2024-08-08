#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from botocore.config import Config
import boto3
import os


def client(*args, **kwargs):
    """
    returns a boto client instrumented with a user agent
    """
    _add_user_agent(kwargs)
    return boto3.client(*args, **kwargs)


def resource(*args, **kwargs):
    """
    returns a boto resource instrumented with a user agent
    """
    _add_user_agent(kwargs)
    return boto3.resource(*args, **kwargs)


def session_client(session, *args, **kwargs):
    """
    returns a boto session_client instrumented with a user agent
    """
    _add_user_agent(kwargs)
    return session.client(*args, **kwargs)


def _add_user_agent(kwargs):
    """
    adds a user agent to the kwargs if there isn't none
    """
    solution_id = os.getenv('SOLUTION_ID', 'SO0097')
    solution_version = os.getenv('SOLUTION_VERSION', 'unknown')
    user_agent = f'AwsSolution/{solution_id}/{solution_version}'
    if 'config' not in kwargs:
        boto_config = Config(user_agent_extra=user_agent)
        kwargs['config'] = boto_config
    else:
        kwargs['config'] = kwargs['config'].merge(Config(user_agent_extra=user_agent))
