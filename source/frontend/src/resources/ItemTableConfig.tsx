/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {capitalize, getNestedValue, getNestedValuePath, returnLocaleDateTime, sortAscendingComparator} from './main'
import {Button, StatusIndicator,} from "@awsui/components-react"
import React from "react";
import {Attribute, EntitySchema} from "../models/EntitySchema";

function status(value: string) {

  let component = undefined;

  let new_value = value.toLowerCase();

  switch (new_value) {
    case 'timed-out':
      component = <StatusIndicator type="error">{value}</StatusIndicator>
      break;
    case 'failed':
      component = <StatusIndicator type="error">{value}</StatusIndicator>
      break;
    case 'running':
      component = <StatusIndicator type="in-progress">{value}</StatusIndicator>
      break;
    case 'complete':
      component = <StatusIndicator type="success">{value}</StatusIndicator>
      break;
    case 'error':
      component = <StatusIndicator type="error">{value}</StatusIndicator>
      break;
    case 'in-progress':
      component = <StatusIndicator type="in-progress">{value}</StatusIndicator>
      break;
    case 'success':
      component = <StatusIndicator type="success">{value}</StatusIndicator>
      break;
    default:
      component = value;
  }

  return component;
}

function getColumnDefinitionsForCheckBox(attr: Attribute) {
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: any) => getNestedValuePath(item, attr.name) ? 'Yes' : 'No',
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

function getColumnDefinitionsForStatus(attr: Attribute) {
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: any) => status(getNestedValuePath(item, attr.name)),
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

function getColumnDefinitionsForPassword(attr: Attribute) {
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: any) => getNestedValuePath(item, attr.name) ? '[value set]' : '',
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

function getColumnDefinitionsForRelationship(attr: Attribute) {
    //Update last element in key name with __.
    let arrName = attr.name.split(".");
    arrName[arrName.length - 1] = '__' + arrName[arrName.length - 1];
    let newName = arrName.join(".");
    return ({
            id: newName,
            header: attr.description,
            cell: (item: any) => getNestedValuePath(item, newName) ? getNestedValuePath(item, newName) : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: newName
        }
    );
}

function getColumnDefinitionsForTag(attr: Attribute) {
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: any) => getNestedValuePath(item, attr.name) ? getNestedValuePath(item, attr.name)
                .map((tag: { key: string; value: string; }, index: any) => {
                    return tag.key + '=' + tag.value
                }).join(';') : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

function getColumnDefinitionsForPolicies(attr: Attribute) {
    //Update last element in key name with __.
    let arrName1 = attr.name.split(".");
    arrName1[arrName1.length - 1] = '__' + arrName1[arrName1.length - 1];
    let newName1 = arrName1.join(".");
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: any) => getNestedValuePath(item, newName1) ? getNestedValuePath(item, newName1).join(', ') : getNestedValuePath(item, newName1),
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

function mapPolicy(policy: any) {
    const finalMsg = [];

    if (policy.create) {
        finalMsg.push('C')
    }

    if (policy.read) {
        finalMsg.push('R')
    }

    if (policy.update) {
        finalMsg.push('U')
    }

    if (policy.delete) {
        finalMsg.push('D')
    }

    return <div
        key={policy.schema_name}>{policy.friendly_name ? policy.friendly_name : policy.schema_name + ' [' + finalMsg.join('') + ']'}</div>
}

function getColumnDefinitionsForPolicy(attr: Attribute) {
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: any) => getNestedValuePath(item, attr.name) ? getNestedValuePath(item, attr.name)
                .map((policy: any) => {
                    return mapPolicy(policy);
                }) : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

function getColumnDefinitionsForGroups(attr: Attribute) {
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: any) => getNestedValuePath(item, attr.name) ? getNestedValuePath(item, attr.name)
                .map((group: { group_name: any; }, index: any) => {
                    return group.group_name
                }).join(', ') : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

function getColumnDefinitionsForJson(attr: Attribute) {
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: any) => getNestedValuePath(item, attr.name) ? JSON.stringify(getNestedValuePath(item, attr.name)) : '',
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

function getColumnDefinitionsDefault(attr: Attribute, schemaName: string, provide_link: boolean) {
    return ({
            id: attr.name,
            header: attr.description,
            cell: (item: { [x: string]: string; }) => attr.name === schemaName + '_name' && provide_link ?
                <div>
                    <Button
                        href={'/' + schemaName + 's/' + item[schemaName + '_id']}
                        iconName="external"
                        variant="icon"
                        target="_blank"
                    />
                    {getNestedValuePath(item, attr.name)}
                </div> : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: attr.name
        }
    );
}

export function getColumnDefinitions(
  schemaName: string,
  schema: EntitySchema,
  provide_link = false
) {

  let columnDefinitions = schema.attributes.map((attr: Attribute) => {
    switch (attr.type) {
      case 'checkbox':
          return getColumnDefinitionsForCheckBox(attr);
    case 'status':
        return getColumnDefinitionsForStatus(attr);
    case 'password':
        return getColumnDefinitionsForPassword(attr);
    case 'relationship':
        return getColumnDefinitionsForRelationship(attr);
    case 'tag':
        return getColumnDefinitionsForTag(attr);
    case 'policies':
        return getColumnDefinitionsForPolicies(attr);
    case 'policy':
        return getColumnDefinitionsForPolicy(attr);
    case 'groups':
        return getColumnDefinitionsForGroups(attr);
    case 'json':
        return getColumnDefinitionsForJson(attr);
    default:
        return getColumnDefinitionsDefault(attr, schemaName, provide_link);
    }
  })

  defaultAuditColumns(columnDefinitions);

  //Remove any dynamic embedded_entity attributes as currently not supported in table.
  //ATTN: add support for embedded_entity in table column.
  // columnDefinitions = columnDefinitions.filter((filterAttribute) => {
  //   return filterAttribute.type !== 'embedded_entity'
  // });

  return columnDefinitions;

}

function defaultAuditColumns(columnDefinitions: {
  id: string;
  header: string;
  cell: (item: any) => any;
  minWidth: number;
  sortingField: string;
  sortingComparator?: ((item1: any, item2: any) => number)
}[]) {

  columnDefinitions.push({
    id: 'createdTimestamp',
    header: 'Created on',
    cell: item => returnLocaleDateTime(getNestedValue(item, '_history', 'createdTimestamp')),
    minWidth: 180,
    sortingField: 'createdTimestamp',
    sortingComparator: (item1, item2) => sortAscendingComparator(returnLocaleDateTime(getNestedValue(item1, '_history', 'createdTimestamp'), true), returnLocaleDateTime(getNestedValue(item2, '_history', 'createdTimestamp'), true))
  });

  columnDefinitions.push({
    id: 'createdBy',
    header: 'Created by',
    cell: item => getNestedValue(item, '_history', 'createdBy', 'email'),
    minWidth: 180,
    sortingField: 'createdBy',
    sortingComparator: (item1, item2) => sortAscendingComparator(getNestedValue(item1, '_history', 'createdBy', 'email'), getNestedValue(item2, '_history', 'createdBy', 'email'))
  });

  columnDefinitions.push({
    id: 'lastModifiedTimestamp',
    header: 'Last modified on',
    cell: item => getNestedValue(item, '_history', 'lastModifiedTimestamp') ? returnLocaleDateTime(getNestedValue(item, '_history', 'lastModifiedTimestamp')) : returnLocaleDateTime(getNestedValue(item, '_history', 'createdTimestamp')),
    minWidth: 180,
    sortingField: 'lastModifiedTimestamp',
    sortingComparator: (item1, item2) =>
      sortAscendingComparator(
        getNestedValue(item1, '_history', 'lastModifiedTimestamp') ? returnLocaleDateTime(getNestedValue(item1, '_history', 'lastModifiedTimestamp'), true) : returnLocaleDateTime(getNestedValue(item1, '_history', 'createdTimestamp'), true),
        getNestedValue(item2, '_history', 'lastModifiedTimestamp') ? returnLocaleDateTime(getNestedValue(item2, '_history', 'lastModifiedTimestamp'), true) : returnLocaleDateTime(getNestedValue(item2, '_history', 'createdTimestamp'), true)
      )
  });

  columnDefinitions.push({
    id: 'lastModifiedBy',
    header: 'Last modified by',
    cell: item => getNestedValue(item, '_history', 'lastModifiedBy', 'email') ? getNestedValue(item, '_history', 'lastModifiedBy', 'email') : getNestedValue(item, '_history', 'createdBy', 'email'),
    minWidth: 180,
    sortingField: 'lastModifiedBy',
    sortingComparator: (item1, item2) =>
      sortAscendingComparator(
        getNestedValue(item1, '_history', 'lastModifiedBy', 'email') ? returnLocaleDateTime(getNestedValue(item1, '_history', 'lastModifiedBy', 'email'), true) : returnLocaleDateTime(getNestedValue(item1, '_history', 'createdBy', 'email'), true),
        getNestedValue(item2, '_history', 'lastModifiedBy', 'email') ? returnLocaleDateTime(getNestedValue(item2, '_history', 'lastModifiedBy', 'email'), true) : returnLocaleDateTime(getNestedValue(item2, '_history', 'createdBy', 'email'), true)
      )
  });
}

function defaultAuditSelectorOptions() {

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

export function getContentSelectorOptions(schema: { attributes: any[]; }) {

  //Remove any dynamic embedded_entity attributes as currently not supported in table.
  //ATTN: add support for embedded_entity in table column.

  let cleansedSchema = schema.attributes.filter(filterAttribute => {
    return (filterAttribute.type !== 'embedded_entity' ||
      filterAttribute.type !== 'policy' ||
      filterAttribute.type !== 'policies' ||
      filterAttribute.type !== 'groups')
  });

  let options = cleansedSchema.map((attr, index) => {
    let option = {};
    if (attr.type === 'relationship') {
      //Update last element in key name with __.
      let arrName = attr.name.split(".");
      arrName[arrName.length - 1] = '__' + arrName[arrName.length - 1];
      let newName = arrName.join(".");

      option = {
        id: newName,
        label: attr.description,
        editable: attr.alwaysDisplay ? !attr.alwaysDisplay : true,
      };
    } else if (attr.type === 'json' || attr.type === 'embedded_entity') {
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

  return [
    {
      label: 'Main attributes',
      options: options
    },
    {
      label: 'Audit',
      options: defaultAuditSelectorOptions()
    }];

}

export function getPageSelectorOptions(schemaName: string) {
  return [
    {value: 10, label: '10 ' + capitalize(schemaName + 's')},
    {value: 30, label: '30 ' + capitalize(schemaName + 's')},
    {value: 50, label: '50 ' + capitalize(schemaName + 's')}
  ];
}

export const CUSTOM_PREFERENCE_OPTIONS = [{value: 'table', label: 'Table'}, {value: 'cards', label: 'Cards'}];

export function getDefaultPreferences(schema: EntitySchema, table_key: any) {

  //Get all required attributes from schema.
  const visibleAttributes = schema.attributes.filter(attribute => {
    return attribute.required && !attribute.hidden && attribute.type !== 'embedded_entity' && attribute.type !== 'policy' && attribute.type !== 'policies' && attribute.type !== 'groups';
  });

  const visibleAttributeNames = visibleAttributes.map(attribute => {
    return attribute.name;
  });

  //Add default audit attributes to display.
  visibleAttributeNames.push('lastModifiedTimestamp');
  visibleAttributeNames.push('lastModifiedBy');

  return {
    pageSize: 10,
    visibleContent: visibleAttributeNames,
    wraplines: false,
    trackBy: table_key
  };
}
