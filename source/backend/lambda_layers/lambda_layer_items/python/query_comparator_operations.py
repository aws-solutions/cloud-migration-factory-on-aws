#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0

import query_conditions

# list of operation names as constants
EQUAL_COMPARATOR = "="
NOT_EQUAL_COMPARATOR = "!="
EMPTY_COMPARATOR = "empty"
NOT_EMPTY_COMPARATOR = "!empty"

query_comparator_operations_dictionary = {
    EQUAL_COMPARATOR: query_conditions.equal_query_condition,
    NOT_EQUAL_COMPARATOR: query_conditions.not_equal_query_condition,
    EMPTY_COMPARATOR: query_conditions.empty_query_condition,
    NOT_EMPTY_COMPARATOR: query_conditions.not_empty_query_condition
}