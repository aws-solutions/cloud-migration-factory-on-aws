/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';

import {
  Box,
  Button,
  CollectionPreferences,
  Pagination,
  TextFilter,
  Table,
  Link,
  SpaceBetween
} from '@awsui/components-react';

 import {
   getColumnDefinitions,
   getContentSelectorOptions,
   getPageSelectorOptions,
   getDefaultPreferences
} from '../resources/ItemTableConfig.jsx';
import { useCollection } from '@awsui/collection-hooks';

import {
  resolveRelationshipValues,
  capitalize
} from '../resources/main.js'


import TableHeader from './TableHeader.jsx';

const ItemTable = (props) => {

  const locaStorageKeys = {
    tablePrefs: props.schemaName + "_table_prefs",
    tableAttributes: props.schemaName + "_table_attributes"
  }

  const [preferences, setPreferences] = useState(localStorage[locaStorageKeys.tablePrefs] ? JSON.parse(localStorage.getItem(locaStorageKeys.tablePrefs)) : getDefaultPreferences(props.schema, props.schemaKeyAttribute));
  const [contentAttributes, setContentAttributes] = useState(getContentSelectorOptions(props.schema));

  React.useEffect(() => {
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

  // Keeps track of how many items are selected
  function headerCounter(selectedItems, items) {
    if(selectedItems !== undefined){
      return selectedItems.length
        ? `(${selectedItems.length} of ${items.length})`
        : `(${items.length})`;
    } else {
      return undefined;
    }
  }

  function filterCounter(count) {
    return `${count} ${count === 1 ? 'match' : 'matches'}`;
  }

  async function handleSelectionChange(detail) {
    props.setSelectedItems(detail);
  }

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
    let defaults = getDefaultPreferences(props.schema, props.schemaKeyAttribute);

    lPreferences.trackBy = defaults.trackBy;

    setPreferences(lPreferences);
  }

  function getEntityAccess() {
    let disabledButtons = {}
    if (props.userAccess) {
      //access permissions provided.
      if (props.userAccess[props.schemaName]) {

        if (props.userAccess[props.schemaName].create) {
          if (props.userAccess[props.schemaName].create == false){
            disabledButtons.add = true;
          }
        } else{
          //user does not have this right defined, disable button.
          disabledButtons.add = true;
        }
        if (props.userAccess[props.schemaName].update) {
          if (props.userAccess[props.schemaName].update == false) {
            disabledButtons.edit = true;
          }
        } else {
          //user does not have this right defined, disable button.
          disabledButtons.edit = true;
        }
        if (props.userAccess[props.schemaName].delete) {
          if (props.userAccess[props.schemaName].delete == false) {
            disabledButtons.delete = true;
          }
        } else{
          //user does not have this right defined, disable button.
          disabledButtons.delete = true;
        }
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

  //If attribute passed has a help_content key then the info link will be displayed.
  function displayHelpInfoLink(){

    if (!props.setHelpPanelContent || !props.schema.help_content){
      //SetHelp not provided so do not display.
      return undefined;
    }

    return <Link variant="info" onFollow={() => props.setHelpPanelContent(props.schema.help_content, false)}>Info</Link>
  }

  return (
      <Table
        {...collectionProps}
        trackBy={preferences.trackBy}
        columnDefinitions={getColumnDefinitions(props.schemaName, props.schema, props.provideLink ? props.provideLink : false)}
        visibleColumns={preferences.visibleContent}
        items={resolveRelationshipValues(props.dataAll, items, props.schema)}
        loading={!props.errorLoading ? props.isLoading : true}
        loadingText={!props.errorLoading ? "Loading " + props.schemaName + "s" : "Error getting data from API : " + props.errorLoading}
        resizableColumns={true}
        stickyHeader={true}
        empty={
          <Box textAlign="center" color="inherit">
            <b>No {props.schemaName + "s"}</b>
            <Box
              padding={{ bottom: "s" }}
              variant="p"
              color="inherit"
            >
              No {props.schemaName + "s"} to display.
            </Box>
            {props.handleAddItem ? <Button onClick={props.handleAddItem}>Add {props.schemaName}</Button> : undefined}
          </Box>
        }
        header={
          <TableHeader
            title={props.schema.friendly_name ? props.schema.friendly_name + "s" : capitalize(props.schemaName + "s")}
            description={props.description ? props.description : undefined}
            selectedItems={props.selectedItems ? props.selectedItems : undefined}
            counter={headerCounter(props.selectedItems, props.items)}
            info={displayHelpInfoLink()}
            handleActionSelection={props.handleAction ? props.handleAction : undefined}
            actionsButtonDisabled={props.actionsButtonDisabled}
            actionItems={props.actionItems ? props.actionItems : []}
            handleRefreshClick={props.handleRefreshClick ? handleRefresh : undefined}
            handleDeleteClick={props.handleDeleteItem ? props.handleDeleteItem : undefined}
            handleEditClick={props.handleEditItem ? props.handleEditItem : undefined}
            handleAddClick={props.handleAddItem ? props.handleAddItem : undefined}
            handleDownload={props.handleDownloadItems ? props.handleDownloadItems : undefined}
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
              options: getPageSelectorOptions(props.schemaName)
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
        selectionType={props.selectedItems ? props.selectionType ? props.selectionType : 'multi' : undefined} //If selectionItems not provided then selection disabled for table. Default to multi select if selectionType not provided.
        pagination={<Pagination {...paginationProps} />}
        filter={
          <TextFilter
            {...filterProps}
            countText={filterCounter(filteredItemsCount)}
            filteringPlaceholder={"Search " + props.schemaName + "s"}
          />
        }
      />
  );
};

export default ItemTable;
