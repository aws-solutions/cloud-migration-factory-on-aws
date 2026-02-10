/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState, useEffect, useContext, useCallback, useMemo, useReducer, useRef } from "react";
import {
  Container,
  Header,
  SpaceBetween,
  KeyValuePairs,
  Tabs,
  Box,
  Button,
  Alert,
  Spinner,
  StatusIndicator,
  Table,
  Badge,
  ExpandableSection,
  Pagination,
} from "@cloudscape-design/components";
import { NotificationContext } from "../../contexts/NotificationContext";
import { DataUploadJob, DataUploadJobResult } from "../../models/DataUploadJob";
import ToolsApiClient from "../../api_clients/toolsApiClient";
import ValidationResultsTable from "../import/ValidationIssuesTable";
import { returnLocaleDateTime, getNestedValue } from "../../resources/main";

interface DataItemSelectedJobProps {
  readonly jobId: string;
}

// Constants and configuration
export const CONFIG = {
  REFRESH_INTERVAL_MS: 10000,
  MAX_RETRY_ATTEMPTS: 3,
  RETRY_BASE_DELAY: 1000,
  TIME_FORMAT_OPTIONS: {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  },
} as const;

// Job status constants
export const JOB_STATUS = {
  PENDING: "pending",
  IN_PROGRESS: "in-progress",
  COMPLETE: "complete",
  FAILED: "failed",
  COMPLETE_WITH_WARNINGS: "complete-with-warnings",
  SUPERSEDED: "superseded",
} as const;

// Loading state management types
export interface LoadingState {
  job: boolean;
  results: boolean;
  refreshing: boolean;
}

export type LoadingAction =
  | { type: "START_JOB_LOADING" }
  | { type: "STOP_JOB_LOADING" }
  | { type: "START_RESULTS_LOADING" }
  | { type: "STOP_RESULTS_LOADING" }
  | { type: "START_REFRESHING" }
  | { type: "STOP_REFRESHING" };

export const loadingReducer = (state: LoadingState, action: LoadingAction): LoadingState => {
  switch (action.type) {
    case "START_JOB_LOADING":
      return { ...state, job: true };
    case "STOP_JOB_LOADING":
      return { ...state, job: false };
    case "START_RESULTS_LOADING":
      return { ...state, results: true };
    case "STOP_RESULTS_LOADING":
      return { ...state, results: false };
    case "START_REFRESHING":
      return { ...state, refreshing: true };
    case "STOP_REFRESHING":
      return { ...state, refreshing: false };
    default:
      return state;
  }
};

/**
 * Returns a status indicator component based on the job status
 * @param status - The current status of the data upload job
 * @returns React element representing the status with appropriate styling
 */
export const getStatusIndicator = (status: DataUploadJob["status"]): React.ReactElement => {
  const statusConfig = {
    [JOB_STATUS.COMPLETE]: { type: "success" as const, text: "Completed" },
    [JOB_STATUS.IN_PROGRESS]: { type: "loading" as const, text: "Processing" },
    [JOB_STATUS.PENDING]: { type: "pending" as const, text: "Submitted" },
    [JOB_STATUS.FAILED]: { type: "error" as const, text: "Failed" },
    [JOB_STATUS.COMPLETE_WITH_WARNINGS]: { type: "warning" as const, text: "Completed (with warnings)" },
    [JOB_STATUS.SUPERSEDED]: { type: "stopped" as const, text: "Superseded" },
  };

  const config = statusConfig[status] || { type: "warning" as const, text: `Unknown (${status})` };
  return <StatusIndicator type={config.type}>{config.text}</StatusIndicator>;
};

/**
 * Formats a file size in bytes to a human-readable string
 * @param bytes - The file size in bytes (optional)
 * @returns Formatted string with appropriate unit (Bytes, KB, MB, GB)
 * @example formatFileSize(1024) // returns "1 KB"
 */
export const formatFileSize = (bytes?: number): string => {
  if (!bytes || bytes === 0) return "0 Bytes";
  const units = ["Bytes", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const size = Math.round((bytes / Math.pow(1024, i)) * 100) / 100;
  return `${size} ${units[i]}`;
};

/**
 * Formats a Date object to a time string for display in "last refreshed" context
 * @param date - Date object or null
 * @returns Formatted time string or empty string if date is null/invalid
 * @example formatLastRefreshed(new Date()) // returns "12:34:56 PM"
 */
export const formatLastRefreshed = (date: Date | null): string => {
  if (!date) return "";
  try {
    return date.toLocaleString(undefined, CONFIG.TIME_FORMAT_OPTIONS);
  } catch {
    return "";
  }
};

/**
 * Formats an error object into a user-friendly string message
 * @param error - Error object, string, or unknown type
 * @returns Formatted error message string
 * @example formatError(new Error("Network failed")) // returns "Network failed"
 */
export const formatError = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  return "An unexpected error occurred";
};

/**
 * Sanitizes a string to prevent XSS attacks by escaping HTML characters
 * @param str - String to sanitize
 * @returns Sanitized string safe for display
 */
const sanitizeString = (str: string): string => {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
};

/**
 * Formats API error objects into a React component for display with XSS protection
 * @param errors - Record of error key-value pairs from API response
 * @returns React element displaying formatted errors or null if no errors
 * @example formatApiError({field: "Required field missing"}) // returns formatted error display
 */
export const formatApiError = (errors: Record<string, unknown>): React.ReactElement | null => {
  if (Object.keys(errors).length === 0) return null;

  return (
    <Box>
      {Object.entries(errors).map(([key, value]) => {
        const sanitizedKey = sanitizeString(String(key));
        const displayValue =
          typeof value === "string" ? sanitizeString(value) : sanitizeString(JSON.stringify(value, null, 2));

        return (
          <Box key={key} margin={{ bottom: "xs" }}>
            <Box variant="strong">{sanitizedKey}: </Box>
            <Box variant="code">{displayValue}</Box>
          </Box>
        );
      })}
    </Box>
  );
};

// Reusable loading component
const LoadingState: React.FC<{ message: string }> = ({ message }) => (
  <Container>
    <Box textAlign="center" padding="xxl">
      <Spinner size="large" />
      <Box variant="p" margin={{ top: "s" }}>
        {message}
      </Box>
    </Box>
  </Container>
);

// Reusable empty state component
const EmptyState: React.FC<{ title: string; message: string }> = ({ title, message }) => (
  <Container>
    <Box textAlign="center" padding="xxl">
      <Box variant="h3" color="text-status-inactive">
        {title}
      </Box>
      <Box variant="p" color="text-status-inactive">
        {message}
      </Box>
    </Box>
  </Container>
);

/**
 * Component for displaying detailed information about a selected data upload job
 * Includes job summary, validation results, and API operation results with auto-refresh capability
 * @param props - Component props
 * @param props.jobId - The unique identifier of the job to display
 */
const DataItemSelectedJob: React.FC<DataItemSelectedJobProps> = ({ jobId }) => {
  const { addNotification } = useContext(NotificationContext);
  const [activeTabId, setActiveTabId] = useState("summary");
  const [job, setJob] = useState<DataUploadJob | null>(null);
  const [jobResults, setJobResults] = useState<DataUploadJobResult | null>(null);
  const [loading, dispatchLoading] = useReducer(loadingReducer, {
    job: true,
    results: false,
    refreshing: false,
  });
  const [jobError, setJobError] = useState<string | null>(null);
  const [resultsError, setResultsError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  // Refs for cleanup and mounted state
  const isMountedRef = useRef(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const lastRefreshRequestRef = useRef<Promise<void> | null>(null);

  // Retry with exponential backoff
  const retryWithBackoff = useCallback(
    async (attempt: number) => {
      if (attempt >= CONFIG.MAX_RETRY_ATTEMPTS || !isMountedRef.current) return;

      const delay = CONFIG.RETRY_BASE_DELAY * Math.pow(2, attempt);
      setTimeout(() => {
        if (isMountedRef.current) {
          // Create a new fetchJobData call to avoid circular dependency
          const retryFetch = async () => {
            try {
              const toolsApiClient = new ToolsApiClient();
              const latestJob = await toolsApiClient.getUploadDataJob(jobId);
              if (isMountedRef.current) {
                setJob(latestJob);
                setLastRefreshed(new Date());
                setRetryCount(0);
              }
            } catch (retryError) {
              console.error("Retry fetch failed:", retryError);
              if (isMountedRef.current) {
                setRetryCount((prev) => prev + 1);
                if (attempt + 1 < CONFIG.MAX_RETRY_ATTEMPTS) {
                  retryWithBackoff(attempt + 1);
                }
              }
            }
          };
          retryFetch();
        }
      }, delay);
    },
    [jobId]
  );

  // Fetch job data and detailed results
  const fetchJobData = useCallback(
    async (isManualRefresh = false) => {
      if (!isMountedRef.current) return;

      // Prevent concurrent requests
      if (lastRefreshRequestRef.current) {
        await lastRefreshRequestRef.current;
        if (!isMountedRef.current) return;
      }

      const fetchPromise = (async () => {
        setJobError(null);
        setResultsError(null);

        if (isManualRefresh) {
          dispatchLoading({ type: "START_REFRESHING" });
        } else {
          // Use a ref to check current job state instead of dependency
          const currentJob = job;
          if (!currentJob) {
            dispatchLoading({ type: "START_JOB_LOADING" });
          }
        }

        try {
          const toolsApiClient = new ToolsApiClient();

          // First, fetch the latest job data
          const latestJob = await toolsApiClient.getUploadDataJob(jobId);

          if (!isMountedRef.current) return;
          setJob(latestJob);

          // Then, fetch detailed results if job is complete and has results URL
          if (
            latestJob.results_url &&
            (latestJob.status === JOB_STATUS.COMPLETE ||
              latestJob.status === JOB_STATUS.COMPLETE_WITH_WARNINGS ||
              latestJob.status === JOB_STATUS.FAILED)
          ) {
            dispatchLoading({ type: "START_RESULTS_LOADING" });
            try {
              const results = await toolsApiClient.getDataUploadJobResults(latestJob.results_url);
              if (isMountedRef.current) {
                setJobResults(results);
              }
            } catch (resultsError) {
              console.error("Error fetching job results:", resultsError);
              const errorMessage = formatError(resultsError);

              if (isMountedRef.current) {
                setResultsError(errorMessage);

                // Only show notification for manual refreshes to avoid spam
                if (isManualRefresh) {
                  addNotification({
                    type: "error",
                    header: "Error loading job results",
                    content: errorMessage,
                    dismissible: true,
                  });
                }
              }
            } finally {
              if (isMountedRef.current) {
                dispatchLoading({ type: "STOP_RESULTS_LOADING" });
              }
            }
          } else {
            // Clear previous results if job is no longer complete or doesn't have results URL
            if (isMountedRef.current) {
              setJobResults(null);
            }
          }

          if (isMountedRef.current) {
            setLastRefreshed(new Date());
            setRetryCount(0); // Reset retry count on success
          }
        } catch (error) {
          console.error("Error fetching job data:", error);
          const errorMessage = formatError(error);

          if (isMountedRef.current) {
            setJobError(errorMessage);

            // Only show notification for manual refreshes to avoid spam
            if (isManualRefresh) {
              addNotification({
                type: "error",
                header: "Error loading job data",
                content: errorMessage,
                dismissible: true,
              });
            } else {
              // For auto-refresh failures, try with backoff
              const currentRetryCount = retryCount;
              retryWithBackoff(currentRetryCount);
            }
          }
        } finally {
          if (isMountedRef.current) {
            dispatchLoading({ type: "STOP_JOB_LOADING" });
            if (isManualRefresh) {
              dispatchLoading({ type: "STOP_REFRESHING" });
            }
          }
        }
      })();

      lastRefreshRequestRef.current = fetchPromise;
      await fetchPromise;
      lastRefreshRequestRef.current = null;
    },
    [job, retryCount, jobId, addNotification, retryWithBackoff]
  );

  // Manual refresh handler
  const handleManualRefresh = useCallback(() => {
    fetchJobData(true);
  }, [fetchJobData]);

  // Cleanup effect
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  // Initial data fetch
  useEffect(() => {
    if (isMountedRef.current) {
      fetchJobData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]); // Only depend on jobId, not fetchJobData

  // Auto-refresh for in-progress jobs
  useEffect(() => {
    // Clear existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (!job || job.status !== JOB_STATUS.IN_PROGRESS || !isMountedRef.current) {
      return;
    }

    const refreshJob = async () => {
      if (!isMountedRef.current) return;

      try {
        const toolsApiClient = new ToolsApiClient();
        const latestJob = await toolsApiClient.getUploadDataJob(jobId);

        if (isMountedRef.current) {
          setJob(latestJob);
          setLastRefreshed(new Date());
          setRetryCount(0);
        }
      } catch (error) {
        console.warn("Auto-refresh failed:", error);
        if (isMountedRef.current) {
          setRetryCount((prev) => prev + 1);
        }
      }
    };

    intervalRef.current = setInterval(refreshJob, CONFIG.REFRESH_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [job?.status, jobId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Memoized calculations
  const validationCounts = useMemo(() => {
    if (!jobResults?.validationIssues) {
      return { errors: 0, warnings: 0, total: 0 };
    }

    const issues = jobResults.validationIssues;
    const errors =
      issues.validationErrors.length +
      issues.requiredAttributeErrors.length +
      issues.crossReferenceErrors.length +
      issues.deduplicationErrors.length;
    const warnings = issues.validationWarnings.length + issues.deduplicationWarnings.length;
    const total = errors + warnings;

    return { errors, warnings, total };
  }, [jobResults?.validationIssues]);

  const processingCounts = useMemo(() => {
    if (!jobResults) {
      return { created: 0, updated: 0, createFailed: 0, updateFailed: 0 };
    }

    const created = Object.values(jobResults.createdItems).reduce((sum, items) => sum + items.length, 0);
    const updated = Object.values(jobResults.updatedItems).reduce((sum, items) => sum + items.length, 0);
    const createFailed = Object.values(jobResults.createFailures).reduce(
      (sum, failures) => sum + Object.keys(failures).length,
      0
    );
    const updateFailed = Object.values(jobResults.updateFailures).reduce(
      (sum, failures) => sum + Object.keys(failures).length,
      0
    );

    return { created, updated, createFailed, updateFailed };
  }, [jobResults]);

  // Transform data for tables grouped by entity type
  const processedItemsByEntityType = useMemo(() => {
    if (!jobResults) return {};

    const groupedItems: Record<
      string,
      Array<{
        operation: string;
        [key: string]: unknown;
      }>
    > = {};

    // Add created items
    Object.entries(jobResults.createdItems).forEach(([entityType, entityItems]) => {
      if (!groupedItems[entityType]) groupedItems[entityType] = [];
      entityItems.forEach((item) => {
        groupedItems[entityType].push({
          ...item,
          operation: "create",
        });
      });
    });

    // Add updated items
    Object.entries(jobResults.updatedItems).forEach(([entityType, entityItems]) => {
      if (!groupedItems[entityType]) groupedItems[entityType] = [];
      entityItems.forEach((item) => {
        groupedItems[entityType].push({
          ...item,
          operation: "update",
        });
      });
    });

    return groupedItems;
  }, [jobResults]);

  const failedItemsByEntityType = useMemo(() => {
    if (!jobResults) return {};

    const groupedItems: Record<
      string,
      Array<{
        operation: string;
        error_message: string;
        [key: string]: unknown;
      }>
    > = {};

    // Add create failures
    Object.entries(jobResults.createFailures).forEach(([entityType, failures]) => {
      if (!groupedItems[entityType]) groupedItems[entityType] = [];
      Object.entries(failures).forEach(([itemName, failure]) => {
        groupedItems[entityType].push({
          ...failure.data,
          operation: "Create",
          error_message: failure.error_message,
          item_name: itemName,
        });
      });
    });

    // Add update failures
    Object.entries(jobResults.updateFailures).forEach(([entityType, failures]) => {
      if (!groupedItems[entityType]) groupedItems[entityType] = [];
      Object.entries(failures).forEach(([itemName, failure]) => {
        groupedItems[entityType].push({
          ...failure.data,
          operation: "Update",
          error_message: failure.error_message,
          item_name: itemName,
        });
      });
    });

    return groupedItems;
  }, [jobResults]);

  const isJobInProgress = job?.status === JOB_STATUS.IN_PROGRESS;
  const isJobPending = job?.status === JOB_STATUS.PENDING;
  const isJobFailed = job?.status === JOB_STATUS.FAILED;
  const hasJobCompletedWithWarnings = job?.status === JOB_STATUS.COMPLETE_WITH_WARNINGS;
  const areResultsTabsDisabled = isJobInProgress || isJobPending;

  const renderSummaryTab = () => {
    if (!job) return null;

    const summaryItems = [
      {
        label: "Upload ID",
        value: job.id,
      },
      {
        label: "File Name",
        value: job.filename ?? "-",
      },
      {
        label: "Status",
        value: (
          <SpaceBetween direction="horizontal" size="xs" alignItems="center">
            {getStatusIndicator(job.status)}
          </SpaceBetween>
        ),
      },
      {
        label: "Uploaded By",
        value: job.uploaded_by ?? "-",
      },
      {
        label: "Data Source ID",
        value: job.data_source_id ?? "-",
      },
      {
        label: "Created At",
        value: returnLocaleDateTime(getNestedValue(job, "_history", "createdTimestamp")) as React.ReactNode,
      },
      {
        label: "Updated At",
        value: returnLocaleDateTime(getNestedValue(job, "_history", "lastModifiedTimestamp")) as React.ReactNode,
      },
    ];

    // Add entities created section
    if (jobResults) {
      const createdEntities: string[] = [];
      Object.entries(jobResults.createdItems).forEach(([entityType, items]) => {
        if (items.length > 0) {
          createdEntities.push(`${items.length} ${entityType}${items.length === 1 ? "" : "s"}`);
        }
      });

      summaryItems.push({
        label: "Entities Created",
        value: createdEntities.length > 0 ? createdEntities.join(", ") : "None",
      });

      // Add entities updated section
      const updatedEntities: string[] = [];
      Object.entries(jobResults.updatedItems).forEach(([entityType, items]) => {
        if (items.length > 0) {
          updatedEntities.push(`${items.length} ${entityType}${items.length === 1 ? "" : "s"}`);
        }
      });

      summaryItems.push({
        label: "Entities Updated",
        value: updatedEntities.length > 0 ? updatedEntities.join(", ") : "None",
      });

      // Add failed items section
      const failedItems: string[] = [];
      Object.entries(jobResults.createFailures).forEach(([entityType, failures]) => {
        const count = Object.keys(failures).length;
        if (count > 0) {
          failedItems.push(`${count} ${entityType}${count === 1 ? "" : "s"} failed create`);
        }
      });
      Object.entries(jobResults.updateFailures).forEach(([entityType, failures]) => {
        const count = Object.keys(failures).length;
        if (count > 0) {
          failedItems.push(`${count} ${entityType}${count === 1 ? "" : "s"} failed update`);
        }
      });

      summaryItems.push({
        label: "Failed Items",
        value: failedItems.length > 0 ? failedItems.join(", ") : "None",
      });
    }

    return (
      <Container>
        <SpaceBetween size="l">
          <KeyValuePairs columns={2} items={summaryItems} />

          {isJobInProgress && (
            <Alert type="info" header="Job in progress">
              This job is currently being processed. The details will automatically refresh every{" "}
              {CONFIG.REFRESH_INTERVAL_MS / 1000} seconds.
            </Alert>
          )}

          {isJobFailed && (
            <Alert type="error" header="Job failed">
              The job failed to complete. Please check the validation issues and failed items tabs for more details.
            </Alert>
          )}

          {hasJobCompletedWithWarnings && (
            <Alert type="warning" header="Job completed with warnings">
              The job completed successfully but encountered some warnings. Check the failed items tab for details.
            </Alert>
          )}
        </SpaceBetween>
      </Container>
    );
  };

  const renderValidationResultsTab = () => {
    if (loading.results) {
      return <LoadingState message="Loading validation issues..." />;
    }

    if (resultsError) {
      return (
        <Container>
          <Alert
            type="error"
            header="Error loading validation issues"
            action={
              <Button onClick={() => fetchJobData(true)} iconName="refresh">
                Retry
              </Button>
            }
          >
            {resultsError}
          </Alert>
        </Container>
      );
    }

    if (!jobResults?.validationIssues || validationCounts.total === 0) {
      const title = "Validation Issues";
      const message = isJobInProgress
        ? "Validation issues will be available once processing is complete."
        : "No validation issues found.";

      return <EmptyState title={title} message={message} />;
    }

    return <ValidationResultsTable schemas={{}} validationIssues={jobResults.validationIssues} />;
  };

  const [processedItemsPages, setProcessedItemsPages] = useState<Record<string, number>>({});

  const renderEntityTypeTable = (
    entityType: string,
    items: Array<Record<string, unknown>>,
    currentPage: number,
    onPageChange: (page: number) => void,
    isFailedItems = false
  ) => {
    const pageSize = 5;
    const startIndex = (currentPage - 1) * pageSize;
    const paginatedItems = items.slice(startIndex, startIndex + pageSize);

    const allKeys = new Set<string>();
    items.forEach((item) => Object.keys(item).forEach((key) => allKeys.add(key)));

    const excludedKeys = isFailedItems ? ["operation", "error_message", "_history"] : ["operation", "_history"];

    const columns = Array.from(allKeys)
      .filter((key) => !excludedKeys.includes(key))
      .map((key) => ({
        id: key,
        header: key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
        cell: (item: Record<string, unknown>) => {
          const value = item[key];
          if (value === null || value === undefined) return "-";
          if (typeof value === "object") {
            if (Array.isArray(value)) {
              return value.map((v) => (typeof v === "object" ? JSON.stringify(v) : String(v))).join(", ");
            }
            return JSON.stringify(value);
          }
          return String(value);
        },
      }));

    const columnDefinitions = [
      {
        id: "operation",
        header: "Operation",
        cell: (item: Record<string, unknown>) => (
          <Badge color={item.operation === "create" || item.operation === "Create" ? "green" : "blue"}>
            {item.operation === "create" ? "Create" : item.operation === "update" ? "Update" : String(item.operation)}
          </Badge>
        ),
      },
      ...columns,
      ...(isFailedItems
        ? [
            {
              id: "error_message",
              header: "Error",
              cell: (item: Record<string, unknown>) => (
                <Box variant="strong" color="text-status-error">
                  {String(item.error_message)}
                </Box>
              ),
            },
          ]
        : []),
    ];

    const headerText = isFailedItems ? (
      <SpaceBetween direction="horizontal" size="xs" alignItems="center">
        <StatusIndicator type="error" />
        {`${entityType.charAt(0).toUpperCase() + entityType.slice(1)}s (${items.length})`}
      </SpaceBetween>
    ) : (
      `${entityType.charAt(0).toUpperCase() + entityType.slice(1)}s (${items.length})`
    );

    return (
      <ExpandableSection key={entityType} headerText={headerText} defaultExpanded={false}>
        <Table
          variant="embedded"
          columnDefinitions={columnDefinitions}
          items={paginatedItems}
          pagination={
            <Pagination
              currentPageIndex={currentPage}
              pagesCount={Math.ceil(items.length / pageSize)}
              onChange={({ detail }) => onPageChange(detail.currentPageIndex)}
            />
          }
          empty={
            <EmptyState
              title={`No ${entityType}`}
              message={`No ${entityType} items were ${isFailedItems ? "failed" : "processed"}.`}
            />
          }
        />
      </ExpandableSection>
    );
  };

  const renderProcessedItemsTab = () => {
    if (loading.results) {
      return <LoadingState message="Loading processed items..." />;
    }

    if (resultsError) {
      return (
        <Container>
          <Alert type="error" header="Error loading processed items">
            {resultsError}
          </Alert>
        </Container>
      );
    }

    const entityTypes = Object.keys(processedItemsByEntityType);
    if (entityTypes.length === 0) {
      return <EmptyState title="No Processed Items" message="No items were processed during this import." />;
    }

    return (
      <SpaceBetween size="l">
        {entityTypes.map((entityType) => {
          const items = processedItemsByEntityType[entityType];
          const currentPage = processedItemsPages[entityType] || 1;
          return renderEntityTypeTable(entityType, items, currentPage, (page) =>
            setProcessedItemsPages((prev) => ({ ...prev, [entityType]: page }))
          );
        })}
      </SpaceBetween>
    );
  };

  const [failedItemsPages, setFailedItemsPages] = useState<Record<string, number>>({});

  const renderFailedItemsTab = () => {
    if (loading.results) {
      return <LoadingState message="Loading failed items..." />;
    }

    if (resultsError) {
      return (
        <Container>
          <Alert type="error" header="Error loading failed items">
            {resultsError}
          </Alert>
        </Container>
      );
    }

    const entityTypes = Object.keys(failedItemsByEntityType);
    if (entityTypes.length === 0) {
      return <EmptyState title="No Failed Items" message="All items were processed successfully." />;
    }

    return (
      <SpaceBetween size="l">
        {entityTypes.map((entityType) => {
          const items = failedItemsByEntityType[entityType];
          const currentPage = failedItemsPages[entityType] || 1;
          return renderEntityTypeTable(
            entityType,
            items,
            currentPage,
            (page) => setFailedItemsPages((prev) => ({ ...prev, [entityType]: page })),
            true
          );
        })}
      </SpaceBetween>
    );
  };

  // Loading state
  if (loading.job) {
    return <LoadingState message="Loading job details..." />;
  }

  // Error state
  if (jobError) {
    return (
      <Container>
        <Alert
          type="error"
          header="Error loading job details"
          action={
            <Button onClick={() => fetchJobData(true)} iconName="refresh" loading={loading.refreshing}>
              Retry
            </Button>
          }
        >
          {jobError}
        </Alert>
      </Container>
    );
  }

  // Job not found state
  if (!job) {
    return (
      <Container>
        <Alert type="warning" header="Job not found">
          The requested job could not be found. It may have been deleted or you may not have access to it.
        </Alert>
      </Container>
    );
  }

  return (
    <Container
      header={
        <Header
          variant="h2"
          actions={
            <SpaceBetween direction="horizontal" size="s" alignItems="center">
              {lastRefreshed && (
                <Box variant="small" color="text-status-inactive">
                  Last refreshed: {formatLastRefreshed(lastRefreshed)}
                </Box>
              )}
              <Button
                onClick={handleManualRefresh}
                iconName="refresh"
                loading={loading.refreshing}
                disabled={loading.job || loading.results}
              >
                Refresh
              </Button>
            </SpaceBetween>
          }
        >
          {job.id}
        </Header>
      }
    >
      <Tabs
        activeTabId={activeTabId}
        onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
        tabs={[
          {
            id: "summary",
            label: "📝 Summary",
            content: renderSummaryTab(),
          },
          ...(processingCounts.created + processingCounts.updated > 0
            ? [
                {
                  id: "processed-items",
                  label: `✅ Processed Items (${processingCounts.created + processingCounts.updated})`,
                  content: renderProcessedItemsTab(),
                  disabled: areResultsTabsDisabled,
                },
              ]
            : []),
          ...(processingCounts.createFailed + processingCounts.updateFailed > 0
            ? [
                {
                  id: "failed-items",
                  label: `❌ Failed Import Items (${processingCounts.createFailed + processingCounts.updateFailed})`,
                  content: renderFailedItemsTab(),
                  disabled: areResultsTabsDisabled,
                },
              ]
            : []),
          ...(validationCounts.total > 0
            ? [
                {
                  id: "validation",
                  label: `⚠️ Validation Issues (${validationCounts.total})`,
                  content: renderValidationResultsTab(),
                  disabled: areResultsTabsDisabled,
                },
              ]
            : []),
        ]}
      />
    </Container>
  );
};

// Memoize the component for performance optimization
const MemoizedDataItemSelectedJob = React.memo(DataItemSelectedJob, (prevProps, nextProps) => {
  // Only re-render if jobId changes
  return prevProps.jobId === nextProps.jobId;
});

MemoizedDataItemSelectedJob.displayName = "DataItemSelectedJob";

export default MemoizedDataItemSelectedJob;
