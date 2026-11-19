/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState, useEffect, useContext, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  SpaceBetween,
  Table,
  Header,
  Box,
  Link,
  Modal,
  StatusIndicator,
  Pagination,
  CollectionPreferences,
} from "@cloudscape-design/components";
import { useCollection } from "@cloudscape-design/collection-hooks";
import { NotificationContext } from "../../contexts/NotificationContext";
import { DataUploadJob } from "../../models/DataUploadJob";
import ToolsApiClient from "../../api_clients/toolsApiClient";
import { defaultAuditColumns } from "../../resources/ItemTableConfig";
import DataItemSelectedJob from "./DataImportSelectedJob";

interface DataImportTableProps {
  onAddJob?: () => void;
  onRefresh?: () => void;
}

const DataImportTable: React.FC<DataImportTableProps> = ({ onAddJob, onRefresh }) => {
  const navigate = useNavigate();
  const { addNotification } = useContext(NotificationContext);

  const [jobs, setJobs] = useState<DataUploadJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedJob, setSelectedJob] = useState<DataUploadJob | null>(null);

  const columnDefinitions = React.useMemo(() => {
    const cols = [
      {
        id: "id",
        header: "Upload ID",
        isRowHeader: true,
        sortingField: "id",
        cell: (item: DataUploadJob) => (
          <Link
            onFollow={(event) => {
              event.preventDefault();
              setSelectedJob(item);
              setModalVisible(true);
            }}
            fontSize="body-m"
          >
            {item.id}
          </Link>
        ),
      },
      {
        id: "status",
        header: "Status",
        sortingField: "status",
        cell: (item: DataUploadJob) => getStatusIndicator(item.status),
      },
      {
        id: "filename",
        header: "File name",
        sortingField: "filename",
        cell: (item: DataUploadJob) => item.filename,
      },
      {
        id: "uploaded_by",
        header: "Uploaded by",
        sortingField: "uploaded_by",
        cell: (item: DataUploadJob) => item.uploaded_by,
      },
    ];
    defaultAuditColumns(cols);
    return cols;
  }, []);

  const tablePreferenceLocalStorageKey = "upload_entities_table_prefs";
  const [preferences, setPreferences] = useState(() => {
    const defaultPreferences = {
      pageSize: 10,
      visibleContent: columnDefinitions.map((column) => column.id || ""),
    };
    if (!tablePreferenceLocalStorageKey) {
      return defaultPreferences;
    }
    try {
      // Same local storage key naming as ItemTable so as to reuse the same preference
      return JSON.parse(localStorage.getItem(tablePreferenceLocalStorageKey) ?? "");
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (e) {
      return defaultPreferences;
    }
  });

  const visibleColumnDefinitions = React.useMemo(() => {
    if (!preferences.visibleContent) {
      return columnDefinitions;
    }
    return columnDefinitions.filter((column) =>
      preferences.visibleContent ? preferences.visibleContent.includes(column.id ?? "") : true
    );
  }, [columnDefinitions, preferences.visibleContent]);

  useEffect(() => {
    try {
      localStorage.setItem(tablePreferenceLocalStorageKey, JSON.stringify(preferences));
    } catch (e) {
      console.warn("Failed to save table preferences to localStorage", e);
    }
  }, [preferences, tablePreferenceLocalStorageKey]);

  const { items, actions, paginationProps, collectionProps } = useCollection(jobs, {
    pagination: { pageSize: preferences.pageSize },
    sorting: {
      defaultState: {
        sortingColumn: { sortingField: "id" },
        isDescending: true,
      },
    },
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
  });

  const [refreshTrigger, setRefreshTrigger] = useState(0); // Used to force refresh

  const fetchAllJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const toolsApiClient = new ToolsApiClient();
      const allJobs = await toolsApiClient.listAllUploadDataJobs();
      setJobs(allJobs);
    } catch (error) {
      console.error("Error loading jobs:", error);
      addNotification({
        type: "error",
        header: "Error loading jobs",
        content: "Failed to load data import jobs. Please try again.",
        dismissible: true,
      });
    } finally {
      setIsLoading(false);
    }
  }, [addNotification]);

  useEffect(() => {
    fetchAllJobs();
  }, [fetchAllJobs, refreshTrigger]);

  const getStatusIndicator = (status: DataUploadJob["status"]) => {
    const statusConfig = {
      complete: { type: "success" as const, text: "Completed" },
      "in-progress": { type: "in-progress" as const, text: "Processing" },
      pending: { type: "pending" as const, text: "Pending" },
      failed: { type: "error" as const, text: "Failed" },
      "complete-with-warnings": { type: "warning" as const, text: "Completed (with warnings)" },
      superseded: { type: "stopped" as const, text: "Superseded" },
    };

    const config = statusConfig[status] || { type: "warning" as const, text: `Unknown (${status})` };
    return <StatusIndicator type={config.type}>{config.text}</StatusIndicator>;
  };

  const closeModal = () => {
    setModalVisible(false);
    setSelectedJob(null);
  };

  const handleRefreshClick = () => {
    if (onRefresh) {
      onRefresh();
    }
    // Force refresh of all jobs
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleAddClick = () => {
    if (onAddJob) {
      onAddJob();
    } else {
      navigate("/data-import/new");
    }
  };

  const handleRowClick = (event: { detail: { item: DataUploadJob } }) => {
    const job = event.detail.item;
    setSelectedJob(job);
    setModalVisible(true);
  };

  const renderJobDetails = () => {
    if (!selectedJob) return null;

    return <DataItemSelectedJob jobId={selectedJob.id} />;
  };

  return (
    <>
      <Table
        columnDefinitions={visibleColumnDefinitions}
        items={items}
        resizableColumns
        stickyHeader={true}
        onRowClick={handleRowClick}
        loading={isLoading}
        {...collectionProps}
        empty={
          <Box textAlign="center" color="inherit">
            <b>No data import jobs</b>
            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
              No data import jobs to display.
            </Box>
            <Button onClick={handleAddClick} variant="primary">
              Add
            </Button>
          </Box>
        }
        header={
          <Header
            variant="h2"
            counter={`(${jobs.length})`}
            description="View and manage data upload jobs. Click on a job to view details."
            actions={
              <SpaceBetween direction="horizontal" size="s">
                <Button onClick={handleRefreshClick} iconAlign="right" iconName="refresh" ariaLabel="Refresh" />
                <Button onClick={handleAddClick} variant="primary">
                  Add
                </Button>
              </SpaceBetween>
            }
          >
            Data import jobs
          </Header>
        }
        pagination={jobs.length > 0 && <Pagination {...paginationProps} />}
        preferences={
          <CollectionPreferences
            title="Preferences"
            confirmLabel="Confirm"
            cancelLabel="Cancel"
            preferences={preferences}
            onConfirm={({ detail }) => setPreferences(detail)}
            pageSizePreference={{
              title: "Page size",
              options: [
                { value: 10, label: "10 items" },
                { value: 20, label: "20 items" },
                { value: 50, label: "50 items" },
              ],
            }}
            visibleContentPreference={{
              title: "Select visible columns",
              options: [
                {
                  label: "Columns",
                  options: columnDefinitions.map((column) => ({
                    id: column.id ?? "",
                    label: String(column.header),
                  })),
                },
              ],
            }}
            wrapLinesPreference={{
              label: "Wrap lines",
              description: "Check to see all the text and wrap the lines",
            }}
          />
        }
      />

      <Modal
        onDismiss={closeModal}
        visible={modalVisible}
        closeAriaLabel="Close modal"
        size="max"
        header={"Job Details"}
      >
        {renderJobDetails()}
      </Modal>
    </>
  );
};

export default DataImportTable;
