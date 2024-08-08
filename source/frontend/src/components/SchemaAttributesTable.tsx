/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from "react";

import {
  Box,
  Button,
  CollectionPreferences,
  CollectionPreferencesProps,
  Pagination,
  Table,
  TableProps,
  TextFilter,
} from "@awsui/components-react";

import {
  DEFAULT_PREFERENCES,
  getColumnDefinitions,
  getContentSelectorOptions,
  PAGE_SELECTOR_OPTIONS,
} from "../resources/schemaattr-table-config";

import { useCollection } from "@awsui/collection-hooks";

import TableHeader from "./TableHeader";
import { filterCounter, headerCounter } from "../utils/table-utils";

type SchemaAttributesTableParams = {
  items: unknown[];
  handleSelectionChange?: (selectedItems: any[]) => void;
  isLoading: boolean | undefined;
  error: string | undefined;
  selectedItems: any[];
  handleDeleteItem: any;
  handleEditItem: any;
  handleAddItem: any;
};
const SchemaAttributesTable = (props: SchemaAttributesTableParams) => {
  const [preferences, setPreferences] = useState<CollectionPreferencesProps.Preferences>(DEFAULT_PREFERENCES);
  const [contentAttributes] = useState(getContentSelectorOptions());

  const { items, actions, collectionProps, filterProps, paginationProps, filteredItemsCount } = useCollection(
    props.items,
    {
      pagination: { pageSize: preferences.pageSize },
      sorting: {},
      filtering: {
        noMatch: (
          <Box textAlign="center" color="inherit">
            <b>No matches</b>
            <Box color="inherit" margin={{ top: "xxs", bottom: "s" }}>
              No results match your query
            </Box>
            <Button onClick={() => actions.setFiltering("")}>Clear filter</Button>
          </Box>
        ),
      },
    }
  );

  async function handleOnRowClick(detail: TableProps.OnRowClickDetail<any>) {
    if (props.handleSelectionChange) {
      let selectedItem = [];
      selectedItem.push(detail.item);

      props.handleSelectionChange(selectedItem);
    }
  }

  const header = (
    <TableHeader
      title="Attributes"
      selectedItems={props.selectedItems ? props.selectedItems : undefined}
      counter={props.selectedItems ? headerCounter(props.selectedItems, items) : undefined}
      handleDeleteClick={props.handleDeleteItem ? props.handleDeleteItem : undefined}
      handleEditClick={props.handleEditItem ? props.handleEditItem : undefined}
      handleAddClick={props.handleAddItem ? props.handleAddItem : undefined}
      description={undefined}
      handleRefreshClick={undefined}
      handleActionSelection={undefined}
      actionItems={undefined}
      handleDownload={undefined}
      actionsButtonDisabled={undefined}
      disabledButtons={undefined}
      info={undefined}
    />
  );

  const handleSelectionChange = props.handleSelectionChange;

  return (
    <Table
      {...collectionProps}
      trackBy={"name"}
      columnDefinitions={getColumnDefinitions()}
      visibleColumns={preferences.visibleContent}
      items={items}
      loading={props.isLoading}
      loadingText={props.error === undefined ? "Loading attributes" : "Error getting data from API"}
      resizableColumns
      stickyHeader={true}
      header={header}
      preferences={
        <CollectionPreferences
          title="Preferences"
          confirmLabel="Confirm"
          cancelLabel="Cancel"
          preferences={preferences}
          onConfirm={({ detail }) => setPreferences(detail)}
          pageSizePreference={{
            title: "Page size",
            options: PAGE_SELECTOR_OPTIONS,
          }}
          visibleContentPreference={{
            title: "Select visible columns",
            options: contentAttributes,
          }}
          wrapLinesPreference={{
            label: "Wrap lines",
            description: "Check to see all the text and wrap the lines",
          }}
        />
      }
      wrapLines={preferences.wrapLines}
      selectedItems={props.selectedItems ? props.selectedItems : []}
      onSelectionChange={
        handleSelectionChange ? ({ detail }) => handleSelectionChange(detail.selectedItems) : undefined
      }
      onRowClick={({ detail }) => handleOnRowClick(detail)}
      selectionType={props.handleSelectionChange ? "single" : undefined}
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
