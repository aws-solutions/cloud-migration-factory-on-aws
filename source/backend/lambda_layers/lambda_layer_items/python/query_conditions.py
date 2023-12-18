#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  SPDX-License-Identifier: Apache-2.0


def equal_query_condition(item, query, query_result):
    if query['attribute'] in item and query['value']:
        if item[query['attribute']] == query['value']:
            query_result = True if query_result != False else query_result
            return query_result

    return False


def not_equal_query_condition(item, query, query_result):
    if query['attribute'] in item and query['value']:
        if item[query['attribute']] != query['value']:
            query_result = True if query_result != False else query_result
            return query_result
    
    return False


def empty_query_condition(item, query, query_result):  
    if query['attribute'] in item:
        query_result = non_list_type_attribute_for_empty_comparator(item, query, query_result)
    elif query['attribute'] not in item and 'comparator' in query:
       query_result = True if query_result != False else query_result

    return query_result


def not_empty_query_condition(item, query, query_result):
    if query['attribute'] in item:
        query_result = non_list_type_attribute_for_not_empty_comparator(item, query, query_result)

    return query_result
    

def non_list_type_attribute_for_empty_comparator(item, query, query_result):
    if item[query['attribute']] == '':
        query_result = True if query_result != False else query_result
        return query_result
        
    return False


def non_list_type_attribute_for_not_empty_comparator(item, query, query_result):
    if item[query['attribute']] != '':
        query_result = True if query_result != False else query_result
        return query_result
        
    return False


def parse_outcomes(outcomes):
    return_required = False
    return_hidden = False

    for outcome in outcomes:
        if outcome == 'required':
            return_required = True
        elif outcome == 'not_required':
            return_required = False
        elif outcome == 'hidden':
            return_hidden = True
        elif outcome == 'not_hidden':
            return_hidden = False

    return return_required, return_hidden