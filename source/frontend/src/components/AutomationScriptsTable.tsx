// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';

import {Box, Button, CollectionPreferences, Pagination, Table, TextFilter,} from '@awsui/components-react';

import {
  DEFAULT_PREFERENCES,
  getColumnDefinitions,
  getContentSelectorOptions,
  PAGE_SELECTOR_OPTIONS
} from '../resources/auto-script-table-config';

import {resolveRelationshipValues} from '../resources/main'

import {useCollection} from '@awsui/collection-hooks';

import TableHeader from './TableHeader';
import {filterCounter, headerCounter} from "../utils/table-utils";

const AutomationJobsTable = (props) => {

  const locaStorageKeys = {
    tablePrefs: "Automation_Scripts_Table_Prefs",
    tableAttributes: "Automation_Scripts_Table_Atrributes"
  }

  const [preferences, setPreferences] = useState(localStorage[locaStorageKeys.tablePrefs] ? JSON.parse(localStorage.getItem(locaStorageKeys.tablePrefs)) : DEFAULT_PREFERENCES);
  const [contentAttributes,] = useState(getContentSelectorOptions(props.schema));

  useEffect(() => {
    localStorage.setItem(locaStorageKeys.tablePrefs, JSON.stringify(preferences));
  }, [preferences]);

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

  async function handleRefresh(e) {
    e.preventDefault();
    await props.handleRefreshClick(e);
    // Force update of current item to ensure latest data is available on viewer.

    // Search for previously selected items, and update based on refreshed data.
    let updatedItems = []
    if (props.selectedItems.length > 0) {
      for (const selectedItem of props.selectedItems) {
        const findResult = items.find(item => item[props.schemaKeyAttribute] === selectedItem[props.schemaKeyAttribute])

        if (findResult) {
          updatedItems.push(findResult);
        }
      }
      await props.handleSelectionChange(updatedItems);
    }
  }

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

  function getEntityAccess() {
    let disabledButtons = {}
    if (props.userAccess) {
      //access permissions provided.
      if (props.userAccess[props.schemaName]) {
        disabledButtons = getEntityAccessForSchema();
      } else
      {
        //access permissions provided but schema not present so default to no buttons enabled.
        disabledButtons.add = true;
        disabledButtons.edit = true;
        disabledButtons.delete = true;
      }
    }
    return disabledButtons;
  }

  function getEntityAccessForSchema() {
    const disabledButtons = {}
    if (props.userAccess[props.schemaName].create !== undefined) {
      if (!props.userAccess[props.schemaName].create){
        disabledButtons.add = true;
      }
    } else{
      //user does not have this right defined, disable button.
      disabledButtons.add = true;
    }
    if (props.userAccess[props.schemaName].update !== undefined) {
      if (!props.userAccess[props.schemaName].update) {
        disabledButtons.edit = true;
      }
    } else {
      //user does not have this right defined, disable button.
      disabledButtons.edit = true;
    }
    if (props.userAccess[props.schemaName].delete !== undefined) {
      if (!props.userAccess[props.schemaName].delete) {
        disabledButtons.delete = true;
      }
    } else{
      //user does not have this right defined, disable button.
      disabledButtons.delete = true;
    }
    return disabledButtons;
  }

  return (
      <Table
        {...collectionProps}
        trackBy={preferences.trackBy}
        columnDefinitions={getColumnDefinitions(props.schema)}
        visibleColumns={preferences.visibleContent}
        items={resolveRelationshipValues(props.dataAll, items, props.schema)}
        loading={props.isLoading}
        loadingText={props.error === undefined ? "Loading scripts" : "Error getting data from API"}
        resizableColumns
        stickyHeader={true}
        header={
          <TableHeader
            title='Automation Scripts'
            selectedItems={props.selectedItems ? props.selectedItems : undefined}
            counter={headerCounter(props.selectedItems, props.items)}
            handleRefreshClick={props.handleRefreshClick ? handleRefresh : undefined}
            handleDeleteClick={props.handleDeleteItem ? props.handleDeleteItem : undefined}
            handleEditClick={props.handleUpdateItem ? props.handleUpdateItem : undefined}
            handleAddClick={props.handleAddItem ? props.handleAddItem : undefined}
            handleActionSelection={props.handleActionSelection ? props.handleActionSelection : undefined}
            actionsButtonDisabled={props.actionsButtonDisabled}
            actionItems={props.actionItems ? props.actionItems : []}
            disabledButtons={getEntityAccess()}
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
        selectionType={props.handleSelectionChange ? 'multi' : undefined}
        pagination={<Pagination {...paginationProps} />}
        filter={
          <TextFilter
            {...filterProps}
            countText={filterCounter(filteredItemsCount)}
            filteringPlaceholder="Search automation scripts"
          />
        }
      />
  );
};

export default AutomationJobsTable;
