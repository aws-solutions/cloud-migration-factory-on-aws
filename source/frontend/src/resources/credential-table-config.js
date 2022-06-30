import {getNestedValue, returnLocaleDateTime, sortAscendingComparator} from './main.js';

function getSecretType(item) {
  if (item.data.SECRET_TYPE === 'keyValue') {
    return 'Key / Value';
  } else if (item.data.SECRET_TYPE === 'OS') {
    return item.data.OS_TYPE + ' OS';
  } else if (item.data.SECRET_TYPE === 'plainText') {
    return 'Plaintext';
  } else {
    return item.data.SECRET_TYPE;
  }
}

const COLUMN_DEFINITIONS = [
  {
    id: 'secretname',
    header: 'Secret name',
    cell: item => item.Name,
    minWidth: '20%',
    maxWidth: '25%',
    sortingField: 'Name'
  },
  {
    id: 'secrettype',
    header: 'Secret Type',
    cell: item => getSecretType(item),
    width: '14%',
    sortingField: 'data',
    sortingComparator: (item1, item2) => sortAscendingComparator(returnLocaleDateTime(getSecretType(item1),true), returnLocaleDateTime(getSecretType(item2),true))
  },
  {
    id: 'description',
    header: 'Description',
    cell: item => item.Description,
    minWidth: '20%',
    maxWidth: '30%',
    sortingField: 'Description'
  },
  {
    id: 'createdon',
    header: 'Created on',
    cell: item => returnLocaleDateTime(item.LastChangedDate),
    width: '19%',
    sortingField: 'LastChangedDate',
    sortingComparator: (item1, item2) => sortAscendingComparator(returnLocaleDateTime(getNestedValue(item1, 'LastChangedDate'),true), returnLocaleDateTime(getNestedValue(item2, 'LastChangedDate'),true))
  },
  {
    id: 'lastretrieved',
    header: 'Last retrieved',
    cell: item => returnLocaleDateTime(item.LastAccessedDate),
    width: '19%',
    sortingField: 'LastAccessedDate',
    sortingComparator: (item1, item2) => sortAscendingComparator(returnLocaleDateTime(getNestedValue(item1, 'LastAccessedDate'),true), returnLocaleDateTime(getNestedValue(item2, 'LastAccessedDate'),true))
  }
];

export function getColumnDefinitions() {

  return COLUMN_DEFINITIONS;

}

export function getContentSelectorOptions() {
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
  visibleContent: ['secretname', 'secrettype', 'description', 'createdon'],
  wraplines: false,
};
