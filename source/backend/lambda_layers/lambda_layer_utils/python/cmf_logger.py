#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

from imp import reload
import logging
import os

LOGGER_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
}

LOGLEVEL = os.getenv('LOGLEVEL', 'INFO').upper()
# This will not take effect if a basicConfig has already been set for the process
logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=LOGLEVEL) # //NOSONAR Basic configuration doesn't pose security risk
logger = logging.getLogger()
logger.setLevel(LOGGER_LEVELS[LOGLEVEL])


def get_logger(name=None):
    return logging.getLogger(name)


def init_task_execution_logger(filter):
    reload(logging)
    task_execution_logger = logging.getLogger()
    logging.basicConfig(format='[%(task_execution_id)s][%(status)s] %(message)s', level=logging.INFO)
    task_execution_logger.setLevel(logging.INFO)
    task_execution_logger.addFilter(filter)
    return task_execution_logger

def log_event_received(event):
    logger.info(f'RequestId: {event.get("requestContext", {}).get("requestId", "{not provided}")}, '
            f'ExtendedRequestId: {event.get("requestContext", {}).get("extendedRequestId", "{not provided}")}')