/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
    getNestedValue,
    sortAscendingComparator,
    returnLocaleDateTime
} from '../resources/main.js'

export function getColumnDefinitions(schema, provide_link = false){


  let columnDefinitions = schema.attributes.map((attr, index) => {
    switch (attr.type) {
      case 'password':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => item[attr.name] ? '[value set]' : '',
            minWidth: 180,
            sortingField: attr.name
          }
        )
      case 'relationship':
        return ({
            id: '__' + attr.name,
            header: attr.description,
            cell: item => item['__' + attr.name] ? item['__' + attr.name] : item[attr.name],
            minWidth: 180,
            sortingField: '__' + attr.name
          }
        )
      case 'tag':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => item[attr.name] ? item[attr.name].map((tag, index) => { return tag.key + '=' + tag.value}).join(';') : item[attr.name],
            minWidth: 180,
            sortingField: attr.name
          }
        )
      default:
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => item[attr.name],
            minWidth: 180,
            sortingField: attr.name
          }
        )
      }
  })

    defaultAuditColumns(columnDefinitions);

  return columnDefinitions;

};

function defaultAuditColumns(columnDefinitions){

    columnDefinitions.push({
        id: 'createdTimestamp',
        header: 'Created on',
        cell: item => returnLocaleDateTime(getNestedValue(item, '_history', 'createdTimestamp')),
        minWidth: 180,
        sortingComparator: (item1, item2) => sortAscendingComparator(returnLocaleDateTime(getNestedValue(item1, '_history', 'createdTimestamp'),true), returnLocaleDateTime(getNestedValue(item2, '_history', 'createdTimestamp'),true))
    });

    columnDefinitions.push({
        id: 'createdBy',
        header: 'Created by',
        cell: item => getNestedValue(item, '_history', 'createdBy', 'email'),
        minWidth: 180,
        sortingComparator: (item1, item2) => sortAscendingComparator(getNestedValue(item1, '_history', 'createdBy', 'email'), getNestedValue(item2, '_history', 'createdBy', 'email'))
    });

    columnDefinitions.push({
        id: 'lastModifiedTimestamp',
        header: 'Last modified on',
        cell: item => returnLocaleDateTime(getNestedValue(item, '_history', 'lastModifiedTimestamp')),
        minWidth: 180,
        sortingComparator: (item1, item2) => sortAscendingComparator(returnLocaleDateTime(getNestedValue(item1, '_history', 'lastModifiedTimestamp'),true), returnLocaleDateTime(getNestedValue(item2, '_history', 'lastModifiedTimestamp'),true))
    });

    columnDefinitions.push({
        id: 'lastModifiedBy',
        header: 'Last modified by',
        cell: item => getNestedValue(item, '_history', 'lastModifiedBy', 'email'),
        minWidth: 180,
        sortingComparator: (item1, item2) => sortAscendingComparator(getNestedValue(item1, '_history', 'lastModifiedBy', 'email'), getNestedValue(item2, '_history', 'lastModifiedBy', 'email'))
    });


}

function defaultAuditSelectorOptions(options){

    let auditSelectorOptions = [];

    auditSelectorOptions.push({
        id: 'createdTimestamp',
        label: 'Created on',
        editable: true,
    });

    auditSelectorOptions.push({
        id: 'createdBy',
        label: 'Created by',
        editable: true,
    });

    auditSelectorOptions.push({
        id: 'lastModifiedTimestamp',
        label: 'Last modified on',
        editable: true,
    });

    auditSelectorOptions.push({
        id: 'lastModifiedBy',
        label: 'Last modified by',
        editable: true,
    });

    return auditSelectorOptions;
}

export function getContentSelectorOptions(schema){

  let options = schema.attributes.map((attr, index) => {
    let option = {};
    if (attr.type === 'relationship'){
      option = {
        id: '__' + attr.name,
        label: attr.description,
        editable: attr.alwaysDisplay ? !attr.alwaysDisplay : true,
      };
    } else if (attr.type === 'json'){
      option = {
        id: attr.name,
        label: attr.description,
        editable: false,
      };
    } else {
      option = {
        id: attr.name,
        label: attr.description,
        editable: attr.alwaysDisplay ? !attr.alwaysDisplay : true,
      };
    }
    return option;
  })

    const contentSelectorOptions = [
        {
            label: 'Main attributes',
            options: options
        },
        {
            label: 'Audit',
            options: defaultAuditSelectorOptions()
        }];


  return contentSelectorOptions;

};

export const PAGE_SELECTOR_OPTIONS = [
  { value: 10, label: '10 Scripts' },
  { value: 30, label: '30 Scripts' },
  { value: 50, label: '50 Scripts' }
];

export const CUSTOM_PREFERENCE_OPTIONS = [];

export const DEFAULT_PREFERENCES = {
  pageSize: 10,
  visibleContent: ['script_name', 'script_description', 'default', 'latest'],
  wraplines: false,
  trackBy: 'package_uuid'
};
