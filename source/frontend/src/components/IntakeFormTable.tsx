// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

/************************************************************************
 DISCLAIMER

 This is just a playground package. It does not comply with best practices
 of using AWS-UI components. For production code, follow the integration
 guidelines:

 https://polaris.a2z.com/develop/integration/react/
 ************************************************************************/
import React, { useState } from "react";

import { Box, Button, CollectionPreferences, Pagination, Table, TextFilter } from "@cloudscape-design/components";

import {
  DEFAULT_PREFERENCES,
  getColumnDefinitions,
  getContentSelectorOptions,
  PAGE_SELECTOR_OPTIONS,
} from "../resources/intakeform-table-config";

import { useCollection } from "@cloudscape-design/collection-hooks";
import TableHeader from "./TableHeader";
import { filterCounter, headerCounter } from "../utils/table-utils";

const IntakeFormTable = (props) => {
  const locaStorageKeys = {
    tablePrefs: "Intake_Import_Table_Prefs",
    tableAttributes: "Intake_Import_Table_Atrributes",
  };
  const [preferences, setPreferences] = useState(DEFAULT_PREFERENCES);

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
            <Box color="inherit" margin={{ top: "xxs", bottom: "s" }}>
              No results match your query
            </Box>
            <Button onClick={() => actions.setFiltering("")}>Clear filter</Button>
          </Box>
        ),
      },
    }
  );

  async function handleOnRowClick(detail) {
    if (props.handleSelectionChange) {
      let selectedItem = [];
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
      //trackBy={preferences.trackBy}
      columnDefinitions={getColumnDefinitions("import", props.schema)}
      visibleColumns={preferences.visibleContent}
      items={items}
      loading={props.isLoading}
      loadingText={props.error === undefined ? "Loading data" : "Error getting data from import file."}
      resizableColumns
      stickyHeader={true}
      header={
        <TableHeader
          title="Import"
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
            title: "Page size",
            options: PAGE_SELECTOR_OPTIONS,
          }}
          visibleContentPreference={{
            title: "Select visible columns",
            options: getContentSelectorOptions(props.schema),
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
        props.handleSelectionChange ? ({ detail }) => props.handleSelectionChange(detail.selectedItems) : null
      }
      onRowClick={({ detail }) => handleOnRowClick(detail)}
      selectionType={props.handleSelectionChange ? "multi" : undefined}
      pagination={<Pagination {...paginationProps} />}
      filter={
        <TextFilter {...filterProps} countText={filterCounter(filteredItemsCount)} filteringPlaceholder="Search data" />
      }
    />
  );
};

export default IntakeFormTable;
