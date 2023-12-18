#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import logging
import os


LOGLEVEL = os.getenv('LOGLEVEL', 'INFO').upper()
logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s', level=LOGLEVEL) # //NOSONAR Basic configuration doesn't pose security risk
logger = logging.getLogger()


def get_logger(name=None):
    return logging.getLogger(name)