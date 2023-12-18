/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {useState} from 'react';

import {Box, Button, CollectionPreferences, Pagination, Table, TableProps, TextFilter} from '@awsui/components-react';

import {
  DEFAULT_PREFERENCES,
  getColumnDefinitions,
  getContentSelectorOptions,
  PAGE_SELECTOR_OPTIONS
} from '../resources/credential-table-config';

import {useCollection} from '@awsui/collection-hooks';

import TableHeader from './TableHeader';
import {filterCounter, headerCounter} from "../utils/table-utils";

const CredentialManagerTable = (props: {
  items: readonly unknown[];
  handleSelectionChange?: (arg0: any[]) => void;
  isLoading: boolean | undefined;
  selectedItems: any[] | undefined;
  handleDeleteItem: any;
  handleEditItem: any;
  handleAddItem: any;
  handleRefresh: any;
}) => {

  const [preferences, setPreferences] = useState<any>(DEFAULT_PREFERENCES);
  const [contentAttributes,] = useState(getContentSelectorOptions());

  const {items, actions, collectionProps, filterProps, paginationProps, filteredItemsCount} = useCollection(
    props.items,
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

  const handleSelectionChange = props.handleSelectionChange;

  async function handleOnRowClick(detail: TableProps.OnRowClickDetail<any>) {

    if (handleSelectionChange) {
      let selectedItem = []
      selectedItem.push(detail.item);

      handleSelectionChange(selectedItem);
    }
  }

  function handleConfirmPreferences(detail: any) {
    setPreferences(detail);
  }

  const tableHeader = <TableHeader
    title='Secrets'
    selectedItems={props.selectedItems ? props.selectedItems : undefined}
    counter={props.selectedItems ? headerCounter(props.selectedItems, items) : undefined}
    handleDeleteClick={props.handleDeleteItem ? props.handleDeleteItem : undefined}
    handleEditClick={props.handleEditItem ? props.handleEditItem : undefined}
    handleAddClick={props.handleAddItem ? props.handleAddItem : undefined}
    handleRefreshClick={props.handleRefresh ? props.handleRefresh : undefined}
    description={undefined}
    handleActionSelection={undefined}
    actionItems={undefined}
    handleDownload={undefined}
    actionsButtonDisabled={undefined}
    disabledButtons={undefined}
    info={undefined}/>;
  const collectionPreferences = <CollectionPreferences
    title="Preferences"
    confirmLabel="Confirm"
    cancelLabel="Cancel"
    preferences={preferences}
    onConfirm={({detail}) => handleConfirmPreferences(detail)}
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
  />;
  return (
    <Table
      {...collectionProps}
      columnDefinitions={getColumnDefinitions()}
      visibleColumns={preferences.visibleContent}
      items={items}
      loading={props.isLoading}
      loadingText={"Loading secrets"}
      resizableColumns
      stickyHeader={true}
      header={tableHeader}
      preferences={collectionPreferences}
      wrapLines={preferences.wrapLines}
      selectedItems={props.selectedItems ? props.selectedItems : []}
      onSelectionChange={handleSelectionChange ?
        ({detail}) => handleSelectionChange(detail.selectedItems)
        : undefined}
      onRowClick={({detail}) => handleOnRowClick(detail)}
      selectionType={handleSelectionChange ? 'single' : undefined}
      pagination={<Pagination {...paginationProps} />}
      filter={
        <TextFilter
          {...filterProps}
          countText={filterCounter(filteredItemsCount)}
          filteringPlaceholder="Search secrets"
        />
      }
    />
  );
};

export default CredentialManagerTable;
