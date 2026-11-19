import React, { useState } from "react";
import {
  Box,
  Button,
  Container,
  Header,
  Modal,
  Pagination,
  Select,
  SelectProps,
  SpaceBetween,
  StatusIndicator,
  Table,
  TableProps,
} from "@cloudscape-design/components";
import AdminApiClient from "../../api_clients/adminApiClient";
import {
  CrossReferenceError,
  DeduplicationError,
  RequiredAttributeError,
  ValidationError,
  ValidationIssues,
} from "../data-validation";
import { EntitySchema } from "../../models";
import { capitalize } from "../../resources/main";

export interface ValidationResultsTableProps {
  readonly schemas: Record<string, EntitySchema>;
  readonly validationIssues: ValidationIssues;
  readonly entityFilter?: string;
  readonly header?: string;
  readonly onRevalidate?: () => Promise<void>;
}

type ValidatorError = DeduplicationError | RequiredAttributeError | ValidationError | CrossReferenceError;

// Define a type for errors with severity information
type ErrorWithSeverity = ValidatorError & {
  readonly severity: "error" | "warning";
};

type GroupedError = ErrorWithSeverity & {
  readonly children: ErrorWithSeverity[];
  readonly id: string;
};

/**
 * Helper function to determine the severity of an item based on its children
 * @param item The grouped error item to check
 * @returns The severity level ('error' or 'warning')
 */
const getSeverity = (item: GroupedError): "error" | "warning" => {
  if (item.children && item.children.length > 0) {
    const hasErrors = item.children.some((child) => child.severity === "error" || !child.severity);
    return hasErrors ? "error" : "warning";
  }
  return item.severity === "warning" ? "warning" : "error";
};

/**
 * Helper function to get the message for an item
 * @param item The grouped error item
 * @returns The message to display
 */
const getMessage = (item: GroupedError): string => {
  // For parent rows with multiple children, show a summary message
  if (item.children && item.children.length > 1) {
    return `${item.children.length} validation issues found`;
  }
  // For single issues or ungrouped items, show the direct message
  return item.message;
};

/**
 * Helper function to get the attribute name for an item
 * @param item The grouped error item
 * @returns The attribute name to display
 */
const getAttributeName = (item: GroupedError): string => {
  // Don't show for parent rows with multiple children
  if (item.children && item.children.length > 1) {
    return "";
  }
  return item.attributeName;
};

/**
 * Component that displays validation errors in a table.
 */
const ValidationResultsTable: React.FC<ValidationResultsTableProps> = ({
  schemas,
  validationIssues,
  entityFilter,
  header,
  onRevalidate,
}) => {
  // State for error type selection
  const [selectedErrorType, setSelectedErrorType] = useState<"all" | "errors" | "warnings">("all");

  // State for pagination
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // Memoize error type options for the dropdown
  const errorTypeOptions: SelectProps.Option[] = React.useMemo(
    () => [
      { label: "All issues", value: "all" },
      { label: "Errors only", value: "errors" },
      { label: "Warnings only", value: "warnings" },
    ],
    []
  );

  // Memoize the processed errors from the validation result
  const processedErrors = React.useMemo(() => {
    try {
      // Provide default empty issues if validationResult or issues is undefined
      const issues = validationIssues || {};

      // Create arrays with severity information
      const deduplicationErrors = (issues.deduplicationErrors || []).map((error) => ({
        ...error,
        severity: "error" as const,
      }));

      const deduplicationWarnings = (issues.deduplicationWarnings || []).map((warning) => ({
        ...warning,
        severity: "warning" as const,
      }));

      const requiredAttributeErrors = (issues.requiredAttributeErrors || []).map((error) => ({
        ...error,
        severity: "error" as const,
      }));

      const validationErrors = (issues.validationErrors || []).map((error) => ({
        ...error,
        severity: "error" as const,
      }));

      const validationWarnings = (issues.validationWarnings || []).map((warning) => ({
        ...warning,
        severity: "warning" as const,
      }));

      const crossReferenceErrors = (issues.crossReferenceErrors || []).map((error) => ({
        ...error,
        severity: "error" as const,
      }));

      // All errors and warnings
      const allErrors = [
        ...deduplicationErrors,
        ...requiredAttributeErrors,
        ...validationErrors,
        ...crossReferenceErrors,
      ];

      const allWarnings = [...deduplicationWarnings, ...validationWarnings];

      return { allErrors, allWarnings };
    } catch (error) {
      console.error("Error processing validation results:", error);
      return { allErrors: [], allWarnings: [] };
    }
  }, [validationIssues]);

  // Memoize filtered errors based on selected error type and entity filter
  const allErrors = React.useMemo(() => {
    const { allErrors, allWarnings } = processedErrors;

    // First, collect all errors based on the selected error type
    let allErrorsList: ErrorWithSeverity[] = [];

    switch (selectedErrorType) {
      case "errors":
        allErrorsList = [...allErrors];
        break;
      case "warnings":
        allErrorsList = [...allWarnings];
        break;
      case "all":
      default:
        allErrorsList = [...allErrors, ...allWarnings];
    }

    // Filter by entity if entityFilter is provided
    if (entityFilter) {
      allErrorsList = allErrorsList.filter((error) => error.entityName === entityFilter);
    }

    // Group errors by entityName and uniqueKey
    const groupedErrorsMap = new Map<string, GroupedError>();

    allErrorsList.forEach((error) => {
      // Create a composite key for grouping
      const groupKey = `${error.entityName}:${error.uniqueKey}`;

      if (!groupedErrorsMap.has(groupKey)) {
        // Create a new parent grouped error for this group
        const parentError = {
          ...error,
          children: [] as ErrorWithSeverity[],
          id: groupKey,
        } as GroupedError;

        groupedErrorsMap.set(groupKey, parentError);
      }

      // Add this error as a child to the parent error
      const parentError = groupedErrorsMap.get(groupKey);
      if (parentError) {
        parentError.children.push(error);
      }
    });

    // Convert the map to an array
    return Array.from(groupedErrorsMap.values()).map((groupedError) => {
      // If there's only one issue for this entity/key, return it directly without grouping
      if (groupedError.children.length === 1) {
        return {
          ...groupedError.children[0],
          id: groupedError.id,
          children: [], // Empty children array to indicate it's not expandable
          severity: groupedError.children[0].severity,
        } as GroupedError;
      }
      return groupedError;
    });
  }, [processedErrors, selectedErrorType, entityFilter]);

  // Reset to first page and clear expanded items when entity filter or error type changes
  React.useEffect(() => {
    setCurrentPage(1);
    setExpandedItems(new Set());
  }, [entityFilter, selectedErrorType]);

  // Pagination calculations
  const paginationData = React.useMemo(() => {
    const totalItems = allErrors.length;
    const totalPages = Math.ceil(totalItems / pageSize);
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, totalItems);
    const currentItems = allErrors.slice(startIndex, endIndex);

    return { totalItems, totalPages, currentItems };
  }, [allErrors, currentPage, pageSize]);

  // Use the pagination data
  const { totalItems, totalPages, currentItems } = paginationData;

  // Calculate error and warning counts for display
  const errorWarningCounts = React.useMemo(() => {
    const { allErrors, allWarnings } = processedErrors;

    let filteredErrors = allErrors;
    let filteredWarnings = allWarnings;

    // Apply entity filter if provided
    if (entityFilter) {
      filteredErrors = allErrors.filter((error) => error.entityName === entityFilter);
      filteredWarnings = allWarnings.filter((warning) => warning.entityName === entityFilter);
    }

    return {
      totalErrors: filteredErrors.length,
      totalWarnings: filteredWarnings.length,
      totalIssues: filteredErrors.length + filteredWarnings.length,
    };
  }, [processedErrors, entityFilter]);

  // State for expanded items - track by ID instead of the whole object
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // State for remove server name regex modal
  const [showRemoveServerNameRegexModal, setShowRemoveServerNameRegexModal] = useState(false);
  const [isRemovingServerNameRegex, setIsRemovingServerNameRegex] = useState(false);

  // Check if there are server_name regex validation errors and get current regex
  const serverNameRegexInfo = React.useMemo(() => {
    const { allErrors } = processedErrors;
    const hasErrors = allErrors.some(
      (error) =>
        error.entityName === "server" &&
        error.attributeName === "server_name" &&
        error.message?.includes("Server names must contain only alphanumeric, hyphen or period characters.")
    );
    const currentRegex =
      schemas.server?.attributes?.find((attr) => attr.name === "server_name")?.validation_regex || "";
    return { hasErrors, currentRegex };
  }, [processedErrors, schemas]);

  // Handle remove server_name regex
  const handleRemoveServerNameRegex = async () => {
    setIsRemovingServerNameRegex(true);
    try {
      const adminApi = new AdminApiClient();
      const serverNameAttr = schemas.server?.attributes?.find((attr) => attr.name === "server_name");

      if (serverNameAttr) {
        const updatedAttr = {
          ...serverNameAttr,
          validation_regex: "",
        };
        await adminApi.putSchemaAttr("server", updatedAttr, "server_name");
      }

      setShowRemoveServerNameRegexModal(false);

      // Trigger re-validation if callback is provided
      if (onRevalidate) {
        await onRevalidate();
      }
    } catch (error) {
      console.error("Failed to remove server_name regex:", error);
    } finally {
      setIsRemovingServerNameRegex(false);
    }
  };

  const columnDefinitions: TableProps.ColumnDefinition<GroupedError>[] = React.useMemo(
    () => [
      {
        id: "entityName",
        header: "Entity",
        cell: (item) => schemas[item.entityName]?.friendly_name ?? capitalize(item.entityName),
        sortingField: "entityName",
      },
      {
        id: "uniqueKey",
        header: "Unique Key",
        cell: (item) => item.uniqueKey,
        sortingField: "uniqueKey",
      },
      {
        id: "severity",
        header: "Severity",
        cell: (item) => {
          const severity = getSeverity(item);
          return (
            <StatusIndicator
              type={severity === "error" ? "error" : "warning"}
              aria-label={`${severity === "error" ? "Error" : "Warning"} in ${item.entityName}`}
            >
              {severity === "error" ? "Error" : "Warning"}
            </StatusIndicator>
          );
        },
      },
      {
        id: "message",
        header: "Message",
        cell: getMessage,
      },
      {
        id: "attributeName",
        header: "Attribute",
        cell: getAttributeName,
      },
    ],
    [schemas]
  );

  // Define event types for better type safety
  type SelectChangeEvent = {
    detail: {
      selectedOption: SelectProps.Option;
    };
  };

  type PaginationChangeEvent = {
    detail: {
      currentPageIndex: number;
    };
  };

  // Handle error type selection change
  const handleErrorTypeChange = (event: SelectChangeEvent): void => {
    setSelectedErrorType(event.detail.selectedOption.value as "all" | "errors" | "warnings");
    setCurrentPage(1); // Reset to first page when changing error type
  };

  // Handle pagination change
  const handlePaginationChange = (event: PaginationChangeEvent): void => {
    setCurrentPage(event.detail.currentPageIndex);
  };

  return (
    <SpaceBetween size="l">
      <Container header={header && <Header>{header}</Header>}>
        <SpaceBetween size="m">
          <SpaceBetween size="m">
            <Select
              selectedOption={
                errorTypeOptions.find((option) => option.value === selectedErrorType) || errorTypeOptions[0]
              }
              onChange={handleErrorTypeChange}
              options={errorTypeOptions}
            />
            {onRevalidate && serverNameRegexInfo.hasErrors && (
              <Box float="right">
                <Button variant="normal" onClick={() => setShowRemoveServerNameRegexModal(true)}>
                  Remove server_name regex validation
                </Button>
              </Box>
            )}
          </SpaceBetween>

          <Table
            columnDefinitions={columnDefinitions}
            items={currentItems}
            loadingText="Loading validation results"
            sortingDisabled
            empty={
              <Box textAlign="center" color="inherit">
                <b>No validation issues</b>
                <Box padding={{ bottom: "s" }} variant="p" color="inherit">
                  {entityFilter
                    ? `No validation issues were found for entity '${entityFilter}'.`
                    : "No validation issues were found in the imported data."}
                </Box>
              </Box>
            }
            header={
              <Header
                counter={`(${errorWarningCounts.totalErrors})`}
                description={
                  errorWarningCounts.totalIssues > 0 ? (
                    <>
                      {entityFilter
                        ? `${errorWarningCounts.totalErrors} blocking errors found for entity '${entityFilter}'.`
                        : `${errorWarningCounts.totalErrors} blocking errors found in the imported data.`}
                      {errorWarningCounts.totalWarnings > 0 && (
                        <>
                          {" "}
                          {errorWarningCounts.totalWarnings} warnings and {errorWarningCounts.totalIssues} issues in
                          total.
                        </>
                      )}
                    </>
                  ) : entityFilter ? (
                    `No validation issues were found for entity '${entityFilter}'.`
                  ) : (
                    "No validation issues were found in the imported data."
                  )
                }
              >
                Blocking Issues
              </Header>
            }
            expandableRows={{
              getItemChildren: (item: GroupedError) => {
                if (!item.children || !Array.isArray(item.children)) {
                  return [];
                }

                // Convert ErrorWithSeverity[] to GroupedError[] for the table
                return item.children.map(
                  (child, index) =>
                    ({
                      ...child,
                      children: [],
                      id: `${item.id}-child-${index}`, // Create unique IDs for children
                      severity: (child as ErrorWithSeverity).severity || "error",
                    }) as GroupedError
                );
              },
              isItemExpandable: (item: GroupedError) => Boolean(item.children && item.children.length > 1),
              expandedItems: currentItems.filter((item) => item.id && expandedItems.has(item.id)),
              onExpandableItemToggle: ({ detail }) => {
                if (!detail || !detail.item || !detail.item.id) {
                  return;
                }

                const itemId = detail.item.id;
                setExpandedItems((prevExpandedItems) => {
                  const newExpandedItems = new Set(prevExpandedItems);
                  if (detail.expanded) {
                    newExpandedItems.add(itemId);
                  } else {
                    newExpandedItems.delete(itemId);
                  }
                  return newExpandedItems;
                });
              },
            }}
          />

          {totalItems > 0 && (
            <Pagination
              currentPageIndex={currentPage}
              pagesCount={totalPages}
              onChange={handlePaginationChange}
              ariaLabels={{
                nextPageLabel: "Next page",
                previousPageLabel: "Previous page",
                pageLabel: (pageNumber) => `Page ${pageNumber} of all pages`,
              }}
            />
          )}
        </SpaceBetween>
      </Container>

      <Modal
        onDismiss={() => setShowRemoveServerNameRegexModal(false)}
        visible={showRemoveServerNameRegexModal}
        closeAriaLabel="Close modal"
        footer={
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              <Button variant="link" onClick={() => setShowRemoveServerNameRegexModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleRemoveServerNameRegex} loading={isRemovingServerNameRegex}>
                Remove server_name regex validation
              </Button>
            </SpaceBetween>
          </Box>
        }
        header="Remove server_name regex validation"
      >
        <SpaceBetween size="m">
          <Box variant="p">
            <strong>Warning:</strong> This action will permanently remove all regex validation for the server_name
            attribute during data import.
          </Box>
          {serverNameRegexInfo.currentRegex && (
            <Box variant="p">
              The current regex pattern is: <code>{serverNameRegexInfo.currentRegex}</code>
            </Box>
          )}
          <Box variant="p">After removing the regex validation:</Box>
          <Box variant="p">
            <ul>
              <li>All server_name values will be accepted during import, regardless of format</li>
              <li>This change affects all future imports, not just the current one</li>
              <li>
                You can re-add or modify regex validation by going to Admin → Attributes → Server tab → server_name →
                Advanced options
              </li>
            </ul>
          </Box>
          <Box variant="p">Are you sure you want to proceed?</Box>
        </SpaceBetween>
      </Modal>
    </SpaceBetween>
  );
};

export default ValidationResultsTable;
