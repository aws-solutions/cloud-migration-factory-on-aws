/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';

const COLUMN_DEFINITIONS = [
  {
    id: 'description',
    header: 'Display name',
    cell: item => item.description,
    width: '300px',
    minWidth: '100px',
    maxWidth: '200px',
    sortingField: 'description'
  },
  {
    id: 'name',
    header: 'Programtic name',
    cell: item => item.name,
    width: '300px',
    minWidth: '100px',
    maxWidth: '200px',
    sortingField: 'name'
  },
  {
    id: 'system',
    header: 'System Managed',
    cell: item => (
            item.system ? 'Yes' : 'No'
          ),
    width: '100px',
    minWidth: '100px',
    maxWidth: '50px',
    sortingField: 'system'
  },
  {
    id: 'type',
    cell: item => item.type,
    header: 'Type',
    width: '100px',
    minWidth: '160px',
    sortingField: 'type'
  },
  {
    id: 'listvalue',
    header: 'Value List',
    cell: item => item.listvalue,
    width: '400px',
    minWidth: '100px',
    maxWidth: '200px',
    sortingField: 'listvalue'
  },
  {
    id: 'long_desc',
    header: 'Long Description',
    cell: item => item.long_desc,
    width: '300px',
    minWidth: '180px',
    sortingField: 'long_desc'
  },

  {
    id: 'validation_regex',
    header: 'Validation RegEx',
    cell: item => item.validation_regex,
    width: '100px',
    minWidth: '100px',
    maxWidth: '200px',
    sortingField: 'validation_regex'
  },
  {
    id: 'validation_regex_msg',
    header: 'Validation failed msg',
    cell: item => item.validation_regex_msg,
    width: '100px',
    minWidth: '100px',
    maxWidth: '200px',
    sortingField: 'validation_regex_msg'
  },
  {
    id: 'group',
    header: 'UI grouping',
    cell: item => item.group,
    width: '100px',
    minWidth: '100px',
    maxWidth: '200px',
    sortingField: 'group'
  },
  {
    id: 'required',
    header: 'Required',
    cell: item => (
            item.required ? 'Yes' : 'No'
          ),
    width: '50px',
    minWidth: '50px',
    maxWidth: '200px',
    sortingField: 'required'
  }
];


export function getColumnDefinitions(){

  return COLUMN_DEFINITIONS;

};

export function getContentSelectorOptions(){
  const contentSelectorOptions = {
    label: 'Main attributes',
    options: []
  };

  let options = COLUMN_DEFINITIONS.map((attr, index) => {
    let column = {
      id: attr.id,
      label: attr.header,
      editable: true
    };
    return column;
  })

  contentSelectorOptions.options = options;

  return [contentSelectorOptions];

};
export const CONTENT_SELECTOR_OPTIONS = getContentSelectorOptions();

export const PAGE_SELECTOR_OPTIONS = [
  { value: 10, label: '10 Items' },
  { value: 30, label: '30 Items' },
  { value: 50, label: '50 Items' }
];

export const CUSTOM_PREFERENCE_OPTIONS = [{ value: 'table', label: 'Table' }, { value: 'cards', label: 'Cards' }];

export const DEFAULT_PREFERENCES = {
  pageSize: 30,
  visibleContent: ['name','system','long_desc','description','type','listvalue','required'],
  wraplines: false,
  trackBy: 'name'
};
