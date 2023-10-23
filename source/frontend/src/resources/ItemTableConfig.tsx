// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  getNestedValue,
  sortAscendingComparator,
  returnLocaleDateTime,
  capitalize, getNestedValuePath
} from '../resources/main'
import {
  Button, StatusIndicator,
} from "@awsui/components-react"
import React from "react";

function status(value) {

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

export function getColumnDefinitions(schemaName, schema, provide_link = false){

  let columnDefinitions = schema.attributes.map((attr, index) => {
    switch (attr.type) {
      case 'checkbox':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => getNestedValuePath(item, attr.name) ? 'Yes' : 'No',
            minWidth: 180,
            sortingField: attr.name
          }
        )
      case 'status':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => status(getNestedValuePath(item, attr.name)),
            minWidth: 180,
            sortingField: attr.name
          }
        )
      case 'password':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => getNestedValuePath(item, attr.name) ? '[value set]' : '',
            minWidth: 180,
            sortingField: attr.name
          }
        )
      case 'relationship':
        //Update last element in key name with __.
        let arrName = attr.name.split(".");
        arrName[arrName.length-1] = '__' + arrName[arrName.length-1];
        let newName = arrName.join(".");
        return ({
            id: newName,
            header: attr.description,
            cell: item => getNestedValuePath(item, newName) ? getNestedValuePath(item, newName) : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: newName
          }
        )
      case 'tag':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => getNestedValuePath(item, attr.name) ? getNestedValuePath(item, attr.name).map((tag, index) => { return tag.key + '=' + tag.value}).join(';') : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: attr.name
          }
        )
      case 'policies':
        //Update last element in key name with __.
        let arrName1 = attr.name.split(".");
        arrName1[arrName1.length-1] = '__' + arrName1[arrName1.length-1];
        let newName1 = arrName1.join(".");
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => getNestedValuePath(item, newName1) ? getNestedValuePath(item, newName1).join(', ') : getNestedValuePath(item, newName1),
            minWidth: 180,
            sortingField: attr.name
          }
        )
      case 'policy':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => getNestedValuePath(item, attr.name) ? getNestedValuePath(item, attr.name).map((policy, index) => {
              let finalMsg = [];

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

              return <div key={policy.schema_name}>{policy.friendly_name ? policy.friendly_name : policy.schema_name + ' ['+ finalMsg.join('') +']'}</div>}) : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: attr.name
          }
        )
      case 'groups':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => getNestedValuePath(item, attr.name) ? getNestedValuePath(item, attr.name).map((group, index) => { return group.group_name}).join(', ') : getNestedValuePath(item, attr.name),
            minWidth: 180,
            sortingField: attr.name
          }
        )
      case 'json':
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => getNestedValuePath(item, attr.name) ? JSON.stringify(getNestedValuePath(item, attr.name)) : '',
            minWidth: 180,
            sortingField: attr.name
          }
        )
      default:
        return ({
            id: attr.name,
            header: attr.description,
            cell: item => attr.name === schemaName + '_name' && provide_link ?
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
        )
      }
  })

  defaultAuditColumns(columnDefinitions);

  //Remove any dynamic embedded_entity attributes as currently not supported in table.
  //TODO add support for embedded_entity in table column.
  columnDefinitions = columnDefinitions.filter(filterAttribute => {return filterAttribute.type !== 'embedded_entity'});

  return columnDefinitions;

};

function defaultAuditColumns(columnDefinitions){

    columnDefinitions.push({
        id: 'createdTimestamp',
        header: 'Created on',
        cell: item => returnLocaleDateTime(getNestedValue(item, '_history', 'createdTimestamp')),
        minWidth: 180,
        sortingField: 'createdTimestamp',
        sortingComparator: (item1, item2) => sortAscendingComparator(returnLocaleDateTime(getNestedValue(item1, '_history', 'createdTimestamp'),true), returnLocaleDateTime(getNestedValue(item2, '_history', 'createdTimestamp'),true))
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
        cell: item => getNestedValue(item, '_history', 'lastModifiedTimestamp') ? returnLocaleDateTime(getNestedValue(item, '_history', 'lastModifiedTimestamp') ) : returnLocaleDateTime(getNestedValue(item, '_history', 'createdTimestamp')),
        minWidth: 180,
        sortingField: 'lastModifiedTimestamp',
        sortingComparator: (item1, item2) =>
          sortAscendingComparator(
            getNestedValue(item1, '_history', 'lastModifiedTimestamp') ? returnLocaleDateTime(getNestedValue(item1, '_history', 'lastModifiedTimestamp'), true ) : returnLocaleDateTime(getNestedValue(item1, '_history', 'createdTimestamp'),true),
            getNestedValue(item2, '_history', 'lastModifiedTimestamp') ? returnLocaleDateTime(getNestedValue(item2, '_history', 'lastModifiedTimestamp'), true ) : returnLocaleDateTime(getNestedValue(item2, '_history', 'createdTimestamp'), true)
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
            getNestedValue(item1, '_history', 'lastModifiedBy', 'email') ? returnLocaleDateTime(getNestedValue(item1, '_history', 'lastModifiedBy', 'email'), true ) : returnLocaleDateTime(getNestedValue(item1, '_history', 'createdBy', 'email'),true),
            getNestedValue(item2, '_history', 'lastModifiedBy', 'email') ? returnLocaleDateTime(getNestedValue(item2, '_history', 'lastModifiedBy', 'email'), true ) : returnLocaleDateTime(getNestedValue(item2, '_history', 'createdBy', 'email'), true)
          )
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

  //Remove any dynamic embedded_entity attributes as currently not supported in table.
  //TODO add support for embedded_entity in table column.

  let cleansedSchema = schema.attributes.filter(filterAttribute => {return (filterAttribute.type !== 'embedded_entity' || filterAttribute.type !== 'policy' || filterAttribute.type !== 'policies'|| filterAttribute.type !== 'groups')});

  let options = cleansedSchema.map((attr, index) => {
    let option = {};
    if (attr.type === 'relationship'){
      //Update last element in key name with __.
      let arrName = attr.name.split(".");
      arrName[arrName.length-1] = '__' + arrName[arrName.length-1];
      let newName = arrName.join(".");

      option = {
        id: newName,
        label: attr.description,
        editable: attr.alwaysDisplay ? !attr.alwaysDisplay : true,
      };
    } else if (attr.type === 'json' || attr.type === 'embedded_entity'){
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

}

export function getPageSelectorOptions(schemaName){
  return [
    { value: 10, label: '10 ' + capitalize(schemaName + 's') },
    { value: 30, label: '30 ' + capitalize(schemaName + 's') },
    { value: 50, label: '50 ' + capitalize(schemaName + 's') }
  ];
}

export const CUSTOM_PREFERENCE_OPTIONS = [{ value: 'table', label: 'Table' }, { value: 'cards', label: 'Cards' }];

export function getDefaultPreferences(schema, table_key){

  //Get all required attributes from schema.
  let visibleAttributes = schema.attributes.filter(attribute => {
    return attribute.required && !attribute.hidden && attribute.type !== 'embedded_entity' && attribute.type !== 'policy' && attribute.type !== 'policies'&& attribute.type !== 'groups';
  });

  visibleAttributes = visibleAttributes.map(attribute => {
    return attribute.name;
  });

  //Add default audit attributes to display.
  visibleAttributes.push('lastModifiedTimestamp');
  visibleAttributes.push('lastModifiedBy');

  return {
    pageSize: 10,
    visibleContent: visibleAttributes,
    wraplines: false,
    trackBy: table_key
  };
}
