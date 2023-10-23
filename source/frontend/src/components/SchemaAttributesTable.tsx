// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';

import {
  Box,
  Button,
  CollectionPreferences,
  Pagination,
  TextFilter,
  Table
} from '@awsui/components-react';

 import {
   PAGE_SELECTOR_OPTIONS,
   DEFAULT_PREFERENCES,
   getColumnDefinitions,
   getContentSelectorOptions
} from '../resources/schemaattr-table-config';

import { useCollection } from '@awsui/collection-hooks';

import TableHeader from './TableHeader';

const SchemaAttributesTable = (props) => {

  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);
  const [contentAttributes, ] = useState(getContentSelectorOptions());

    const { items, actions, collectionProps, filterProps, paginationProps, filteredItemsCount } = useCollection(
    props.items,
    {
      pagination: { pageSize: preferences.pageSize },
      sorting: {},
      filtering: {
        noMatch: (
          <Box textAlign="center" color="inherit">
            <b>No matches</b>
            <Box color="inherit" margin={{ top: 'xxs', bottom: 's' }}>
              No results match your query
            </Box>
            <Button onClick={() => actions.setFiltering('')}>Clear filter</Button>
          </Box>
        )
      }
    }
  );

  // Keeps track of how many applications are selected
  function headerCounter(selectedApps, applications) {
    return selectedApps.length
      ? `(${selectedApps.length} of ${applications.length})`
      : `(${applications.length})`;
  }

  function filterCounter(count) {
    return `${count} ${count === 1 ? 'match' : 'matches'}`;
  }

  //moved up to handler
  // function handleSelectionChange(detail) {
  //   detail.preventDefault();
  //   props.handleSelectionChange(detail.selectedItems);
  // }

  async function handleOnRowClick(detail) {

    if (props.handleSelectionChange){
      let selectedItem = []
      selectedItem.push(detail.item);

      await props.handleSelectionChange(selectedItem);
    }
  }

  function handleConfirmPreferences(detail) {
    let lPreferences = detail;

    lPreferences.trackBy = DEFAULT_PREFERENCES.trackBy;

    setPreferences(lPreferences);
  }

  return (
      <Table
        {...collectionProps}
        trackBy={preferences.trackBy}
        columnDefinitions={getColumnDefinitions()}
        visibleColumns={preferences.visibleContent}
        items={items}
        loading={props.isLoading}
        loadingText={props.error === undefined ? "Loading attributes" : "Error getting data from API"}
        resizableColumns
        stickyHeader={true}
        header={
          <TableHeader
            title='Attributes'
            selectedItems={props.selectedItems ? props.selectedItems : undefined}
            counter={props.selectedItems ? headerCounter(props.selectedItems, items) : undefined}
            handleDeleteClick={props.handleDeleteItem ? props.handleDeleteItem : undefined}
            handleEditClick={props.handleEditItem ? props.handleEditItem : undefined}
            handleAddClick={props.handleAddItem ? props.handleAddItem : undefined}
          />
        }
        preferences={
          <CollectionPreferences
            title="Preferences"
            confirmLabel="Confirm"
            cancelLabel="Cancel"
            preferences={preferences}
            onConfirm={({ detail }) => handleConfirmPreferences(detail)}
            pageSizePreference={{
              title: 'Page size',
              options: PAGE_SELECTOR_OPTIONS
            }}
            visibleContentPreference={{
              title: 'Select visible columns',
              options: contentAttributes
            }}
            wrapLinesPreference={{
              label: 'Wrap lines',
              description: 'Check to see all the text and wrap the lines'
            }}
          />
        }
        wrapLines={preferences.wrapLines}
        selectedItems={props.selectedItems ? props.selectedItems : []}
        onSelectionChange={props.handleSelectionChange ? ({ detail }) => props.handleSelectionChange(detail.selectedItems) : null}
        onRowClick={({ detail }) => handleOnRowClick(detail)}
        selectionType={props.handleSelectionChange ? 'single' : undefined}
        pagination={<Pagination {...paginationProps} />}
        filter={
          <TextFilter
            {...filterProps}
            countText={filterCounter(filteredItemsCount)}
            filteringPlaceholder="Search attributes"
          />
        }
      />
  );
};

export default SchemaAttributesTable;
