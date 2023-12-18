/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useContext, useState} from 'react';

import {
  Box,
  Button,
  Checkbox,
  CollectionPreferences,
  CollectionPreferencesProps,
  Link,
  Pagination,
  Table,
  TableProps,
  TextFilter
} from '@awsui/components-react';

import {
  getColumnDefinitions,
  getContentSelectorOptions,
  getDefaultPreferences,
  getPageSelectorOptions
} from '../resources/ItemTableConfig';
import {useCollection} from '@awsui/collection-hooks';

import {capitalize, resolveRelationshipValues} from '../resources/main'


import TableHeader from './TableHeader';
import {filterCounter, headerCounter} from "../utils/table-utils";
import {CancelableEventHandler, ClickDetail} from '@awsui/components-react/internal/events';
import {EntitySchema} from '../models/EntitySchema';
import {EntityAccess, UserAccess} from "../models/UserAccess";
import {ClickEvent} from "../models/Events";
import {ToolsContext} from "../contexts/ToolsContext";


type ItemTableParams = {
  actionItems?: any;
  actionsButtonDisabled?: any;
  dataAll: any;
  description?: any;
  errorLoading: string;
  handleAction?: any;
  handleAddItem?: CancelableEventHandler<ClickDetail>;
  handleDaysFilterChange?: (arg0: any) => void;
  handleDeleteItem?: any;
  handleDownloadItems?: any;
  handleEditItem?: any;
  handleRefreshClick?: (arg0: any) => any;
  handleSelectionChange?: (arg0: any[]) => void;
  isLoading?: boolean;
  items: readonly any[];
  provideLink?: boolean;
  schema: EntitySchema;
  schemaKeyAttribute: string;
  schemaName: string;
  selectedItems?: any[];
  selectionType?: any;
  userAccess?: UserAccess;
};
const ItemTable = ({
                     actionItems,
                     actionsButtonDisabled,
                     dataAll,
                     description,
                     errorLoading,
                     handleAction,
                     handleAddItem,
                     handleDaysFilterChange,
                     handleDeleteItem,
                     handleDownloadItems,
                     handleEditItem,
                     handleRefreshClick,
                     handleSelectionChange,
                     isLoading,
                     items,
                     provideLink,
                     schema,
                     schemaKeyAttribute,
                     schemaName,
                     selectedItems,
                     selectionType,
                     userAccess
                   }: ItemTableParams) => {

  const {setHelpPanelContent} = useContext(ToolsContext);

  const locaStorageKeys = {
    tablePrefs: schemaName + "_table_prefs",
    tableAttributes: schemaName + "_table_attributes"
  }

  const [preferences, setPreferences] = useState(localStorage[locaStorageKeys.tablePrefs] ?
    JSON.parse(localStorage.getItem(locaStorageKeys.tablePrefs)!) :
    getDefaultPreferences(schema, schemaKeyAttribute));
  const [contentAttributes,] = useState(getContentSelectorOptions(schema));

  React.useEffect(() => {
    localStorage.setItem(locaStorageKeys.tablePrefs, JSON.stringify(preferences));
  }, [preferences]);

  const {items: collectionItems, actions, collectionProps, filterProps, paginationProps, filteredItemsCount} = useCollection(
    items,
    {
      pagination: {pageSize: preferences.pageSize},
      sorting: {},
      filtering: {
        noMatch: (
          <Box textAlign="center" color="inherit">
            <b>No matches</b>
            <Box color="inherit" margin={{top: 'xxs', bottom: 's'}}>
              No results match your query
            </Box>
            <Button onClick={() => actions.setFiltering('')}>Clear filter</Button>
          </Box>
        )
      }
    }
  );


  async function handleRefresh(e: ClickEvent) {
    e.preventDefault();
    if (!handleRefreshClick || !handleSelectionChange) return;
    await handleRefreshClick(e);
    // Force update of current item to ensure latest data is available on viewer.

    // Search for previously selected items, and update based on refreshed data.
    let updatedItems = []
    if (selectedItems?.length) {
      for (const selectedItem of selectedItems) {
        const findResult = collectionItems.find(item => item[schemaKeyAttribute] === selectedItem[schemaKeyAttribute])

        if (findResult) {
          updatedItems.push(findResult);
        }
      }
      handleSelectionChange(updatedItems);
    }
  }

  async function handleOnRowClick(detail: TableProps.OnRowClickDetail<any>) {
    if (handleSelectionChange) {
      let selectedItem = []
      selectedItem.push(detail.item);

      handleSelectionChange(selectedItem);
    }
  }

  function handleConfirmPreferences(detail: CollectionPreferencesProps.Preferences<any>) {
    let lPreferences: any = detail;
    let defaults = getDefaultPreferences(schema, schemaKeyAttribute);

    lPreferences.trackBy = defaults.trackBy;

    if (handleDaysFilterChange) {
      handleDaysFilterChange(lPreferences.custom)
    }

    setPreferences(lPreferences);
  }

  function getEntityAccess() {
    let disabledButtons: EntityAccess = {}
    if (userAccess) {
      //access permissions provided.
      if (userAccess[schemaName]) {

        if (userAccess[schemaName].create) {
          if (!userAccess[schemaName].create) {
            disabledButtons.add = true;
          }
        } else {
          //user does not have this right defined, disable button.
          disabledButtons.add = true;
        }
        if (userAccess[schemaName].update) {
          if (!userAccess[schemaName].update) {
            disabledButtons.edit = true;
          }
        } else {
          //user does not have this right defined, disable button.
          disabledButtons.edit = true;
        }
        if (userAccess[schemaName].delete) {
          if (!userAccess[schemaName].delete) {
            disabledButtons.delete = true;
          }
        } else {
          //user does not have this right defined, disable button.
          disabledButtons.delete = true;
        }
      } else {
        //access permissions provided but schema not present so default to no buttons enabled.
        disabledButtons.add = true;
        disabledButtons.edit = true;
        disabledButtons.delete = true;
      }
    }
    return disabledButtons;
  }

  //If attribute passed has a help_content key then the info link will be displayed.
  function displayHelpInfoLink() {

    if (!schema.help_content) {
      //SetHelp not provided so do not display.
      return undefined;
    }

    return <Link variant="info" onFollow={() => setHelpPanelContent(schema.help_content, false)}>Info</Link>
  }

  function getSelectionType() {

    if (selectedItems && selectionType) {
      return selectionType;
    } else if (selectedItems) {
      return 'multi';
    } else {
      return undefined;
    }
  }

  const onSelectionChange = handleSelectionChange ? ({detail}: any) => handleSelectionChange(detail.selectedItems) : undefined;
  return (
    <Table
      {...collectionProps}
      trackBy={preferences.trackBy}
      columnDefinitions={getColumnDefinitions(schemaName, schema, provideLink ? provideLink : false)}
      visibleColumns={preferences.visibleContent}
      items={resolveRelationshipValues(dataAll, collectionItems, schema)}
      loading={!errorLoading ? isLoading : true}
      loadingText={!errorLoading ? "Loading " + schemaName + "s" : "Error getting data from API : " + errorLoading}
      resizableColumns={true}
      stickyHeader={true}
      empty={
        <Box textAlign="center" color="inherit">
          <b>No {schemaName + "s"}</b>
          <Box
            padding={{bottom: "s"}}
            variant="p"
            color="inherit"
          >
            No {schemaName + "s"} to display.
          </Box>
          {handleAddItem ? <Button onClick={handleAddItem}>Add {schemaName}</Button> : undefined}
        </Box>
      }
      header={
        <TableHeader
          title={schema.friendly_name ? schema.friendly_name + "s" : capitalize(schemaName + "s")}
          description={description ? description : undefined}
          selectedItems={selectedItems ? selectedItems : undefined}
          counter={headerCounter(selectedItems || [], items)}
          info={displayHelpInfoLink()}
          handleActionSelection={handleAction ? handleAction : undefined}
          actionsButtonDisabled={actionsButtonDisabled}
          actionItems={actionItems ? actionItems : []}
          handleRefreshClick={handleRefresh}
          handleDeleteClick={handleDeleteItem ? handleDeleteItem : undefined}
          handleEditClick={handleEditItem ? handleEditItem : undefined}
          handleAddClick={handleAddItem ? handleAddItem : undefined}
          handleDownload={handleDownloadItems ? handleDownloadItems : undefined}
          disabledButtons={getEntityAccess()}
        />
      }
      preferences={
        <CollectionPreferences
          title="Preferences"
          confirmLabel="Confirm"
          cancelLabel="Cancel"
          preferences={preferences}
          onConfirm={({detail}) => handleConfirmPreferences(detail)}
          customPreference={handleDaysFilterChange ?
            (customValue, setCustomValue) => (
              <Checkbox checked={customValue} onChange={({detail}) => setCustomValue(detail.checked)}>Display all jobs
                [default is last 30 days]</Checkbox>)
            : undefined
          }
          pageSizePreference={{
            title: 'Page size',
            options: getPageSelectorOptions(schemaName)
          }}
          visibleContentPreference={{
            title: 'Select visible columns',
            options: contentAttributes as any
          }}
          wrapLinesPreference={{
            label: 'Wrap lines',
            description: 'Check to see all the text and wrap the lines'
          }}
        />
      }
      wrapLines={preferences.wrapLines}
      selectedItems={selectedItems ? selectedItems : []}
      onSelectionChange={onSelectionChange}
      onRowClick={({detail}) => handleOnRowClick(detail)}
      selectionType={getSelectionType()} //If selectionItems not provided then selection disabled for table. Default to multi select if selectionType not provided.
      pagination={<Pagination {...paginationProps} />}
      filter={
        <TextFilter
          {...filterProps}
          countText={filterCounter(filteredItemsCount)}
          filteringPlaceholder={"Search " + schemaName + "s"}
        />
      }
    />
  );
};

export default ItemTable;
