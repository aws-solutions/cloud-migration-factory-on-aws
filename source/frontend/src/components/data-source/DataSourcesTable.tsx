/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import React from "react";
import { Box, Table } from "@cloudscape-design/components";
import TableHeader from "../TableHeader";
import { useNavigate } from "react-router-dom";
import { Schemas } from "../../utils/Constants";
import { useGetItems } from "../../actions/ItemsHook";
import { DataSource } from "../../models/DataSource";
import UserApiClient from "../../api_clients/userApiClient";
import { EntitySchema } from "../../models";

export interface DataSourceTableProps {
  readonly editable: boolean;
  readonly selectionType: "multi" | "single";
  readonly onSelectionChange?: (selectedItems: DataSource[]) => void;
  readonly selectedDataSources?: DataSource[];
  readonly schemas: Record<string, EntitySchema>;
}

const DataSourceTable = (props: DataSourceTableProps) => {
  const navigate = useNavigate();

  const [getDataSourceState, { update: updateItems }] = useGetItems<DataSource>(Schemas.DataSource.name);
  const [selectedDataSources, setSelectedDataSources] = React.useState<DataSource[] | undefined>(
    props.selectedDataSources ? props.selectedDataSources : undefined
  );

  const handleAddClick = () => {
    navigate("/admin/wave-planning/data-source/add");
  };

  const handleEditClick = () => {
    const dataSource = selectedDataSources?.length === 1 ? selectedDataSources[0] : undefined;
    if (!dataSource) {
      return;
    }

    navigate("/admin/wave-planning/data-source/edit", {
      state: {
        dataSource,
      },
    });
  };

  const dataSourceSelectionsChange = (selectedDataSources: DataSource[]) => {
    setSelectedDataSources(selectedDataSources);
    // Call the external selection handler if provided
    if (props.onSelectionChange) {
      props.onSelectionChange(selectedDataSources);
    }
  };

  const deleteSelectedDataSources = async () => {
    const userApi = new UserApiClient();
    if (selectedDataSources) {
      try {
        await userApi.deleteDataSources(selectedDataSources);
      } catch (e) {
        // TODO: alert user to the error
        console.error("Error occurred deleting data:", e);
      }
      refreshItems();
    }
  };

  const refreshItems = () => {
    setSelectedDataSources(undefined);
    updateItems(Schemas.DataSource.name);
  };

  return (
    <Table
      columnDefinitions={[
        {
          id: "name",
          header: "Name",
          cell: (item) => item.data_source_name,
          isRowHeader: true,
        },
        {
          id: "filename",
          header: "File name",
          cell: (item) => item.file_name,
        },
        {
          id: "headercount",
          header: "Number of headers",
          cell: (item) => {
            const count = item.header_mappings.reduce((acc, mapping) => {
              return acc + mapping.headers.length;
            }, 0);
            return count;
          },
        },
        {
          id: "createdby",
          header: "Created by",
          cell: (item) => item._history?.createdBy.email,
        },
        {
          id: "createddate",
          header: "Created date",
          cell: (item) => item._history?.createdTimestamp,
        },
      ]}
      empty={
        <Box textAlign="center" color="inherit">
          <b>No data sources</b>
          <Box padding={{ bottom: "s" }} variant="p" color="inherit">
            No data sources to display.
          </Box>
        </Box>
      }
      items={getDataSourceState.data}
      resizableColumns
      stickyHeader={true}
      selectionType={props.selectionType}
      onSelectionChange={(event) => dataSourceSelectionsChange(event.detail.selectedItems)}
      selectedItems={selectedDataSources}
      loading={getDataSourceState.isLoading}
      header={
        <TableHeader
          title="Data sources"
          selectedItems={selectedDataSources ?? []}
          counter={`(${getDataSourceState.data.length})`}
          handleRefreshClick={refreshItems}
          handleDeleteClick={props.editable ? deleteSelectedDataSources : undefined}
          handleEditClick={props.editable ? handleEditClick : undefined}
          handleAddClick={props.editable ? handleAddClick : undefined}
          handleActionSelection={undefined}
          actionsButtonDisabled={true}
          actionItems={[]}
          disabledButtons={[]}
          description={""}
          handleDuplicateClick={undefined}
          handleDownload={undefined}
          info={""}
        />
      }
    />
  );
};

export default DataSourceTable;
