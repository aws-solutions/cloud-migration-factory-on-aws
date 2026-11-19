import React from "react";
import { Box, Container, SpaceBetween, Spinner, StatusIndicator, Tabs } from "@cloudscape-design/components";
import { ImportSheetDataWorkerProps, SheetToEntityMapping } from "./data-source-types";
import { useWorker } from "../../actions/WorkerHook";
import { UNEXPECTED_ERROR } from "../../resources/recordFunctions";
import {
  DataValidationResult,
  DeduplicatedEntity,
  processBackendValidation,
  ValidationIssues,
  splitEntitiesByOperation,
} from "../data-validation";
import { EntitySchema } from "../../models";
import ImportedEntitiesTable from "../import/ImportedEntitiesTable";
import ImportSummary from "./ImportSummary";
import EntitySelection from "./EntitySelection";
import sheetDataWorker from "./import-sheet-data-worker?worker&url";
import ValidationResultsTable from "../import/ValidationIssuesTable";
import { getAllItemsBySchemaType } from "../../utils/import-utils";
import UserApiClient from "../../api_clients/userApiClient";

export interface DSWImportDataProps {
  readonly sheetToEntityMappings: SheetToEntityMapping[];
  readonly schemas: Record<string, EntitySchema>;
  readonly dataSourceFile?: File;
  onValidationResult?: (result: ValidationResult) => void;
  reloadSchema: (refresh?: boolean) => Promise<() => void>;
}

export interface ValidationResult {
  /** Final validated and processed entities to be created with applied defaults and validation */
  readonly entitiesToCreate: DeduplicatedEntity[];

  /** Final validated and processed entities to be updated with applied defaults and validation */
  readonly entitiesToUpdate: DeduplicatedEntity[];

  /** Comprehensive validation results including all error types */
  readonly issues: ValidationIssues;
}
const userApiClient = new UserApiClient();
/**
 * Data source import wizard step four control, this is responsible for the
 * actual import of the data and managing the tab logic for validated entities.
 */
const DSWImportData = (props: DSWImportDataProps) => {
  const { schemas, dataSourceFile, sheetToEntityMappings, onValidationResult } = props;

  // Define the type for the worker result
  type WorkerResultType = {
    validationResult: DataValidationResult;
  };

  // State to store the worker result
  const [workerResult, setWorkerResult] = React.useState<WorkerResultType | undefined>(undefined);
  const [importResult, setImportResult] = React.useState<ValidationResult | undefined>(undefined);
  const [error, setError] = React.useState<string | undefined>(undefined);
  const [processingState, setProcessingState] = React.useState<"idle" | "worker" | "backend" | "complete" | "error">(
    "idle"
  );

  // Local schemas state to handle updates
  const [localSchemas, setLocalSchemas] = React.useState(schemas);

  // Update local schemas when props change
  React.useEffect(() => {
    setLocalSchemas(schemas);
  }, [schemas]);

  // Tab logic state
  const [activeTabId, setActiveTabId] = React.useState<string>("validation");
  const [selectedEntity, setSelectedEntity] = React.useState<string | undefined>(undefined);

  const [importDataWorker] = useWorker<ImportSheetDataWorkerProps, WorkerResultType>(
    new URL(sheetDataWorker, import.meta.url)
  );

  const entities = React.useMemo(() => {
    const entities = sheetToEntityMappings.reduce((acc, mapping) => {
      if (mapping.isSelected) {
        mapping.headers.forEach((header) => {
          acc.push(...header.entityAttributes.map((ea) => ea.entityName));
        });
      }
      return acc;
    }, [] as string[]);
    return new Set(entities).values().toArray().sort();
  }, [sheetToEntityMappings]);

  // Helper function to process backend validation
  const processBackendValidationAsync = React.useCallback(
    async (result: WorkerResultType) => {
      const allItemsBySchemaType = await getAllItemsBySchemaType(entities, userApiClient);
      const { cleanedEntities, crossReferenceErrors } = await processBackendValidation(
        result.validationResult.entities,
        result.validationResult.backendValidationRequests,
        allItemsBySchemaType
      );

      const updatedValidationResult = {
        ...result.validationResult,
        entities: cleanedEntities,
        issues: {
          ...result.validationResult.issues,
          crossReferenceErrors: [...result.validationResult.issues.crossReferenceErrors, ...crossReferenceErrors],
        },
      };

      setWorkerResult({ validationResult: updatedValidationResult });
      const { entitiesToCreate, entitiesToUpdate } = splitEntitiesByOperation(cleanedEntities, allItemsBySchemaType);
      const updatedImportResult = {
        entitiesToCreate,
        entitiesToUpdate,
        issues: updatedValidationResult.issues,
      };

      setImportResult(updatedImportResult);
      return updatedImportResult;
    },
    [entities]
  );

  // Set default selected entity when entities change
  React.useEffect(() => {
    if (entities.length > 0 && !selectedEntity) {
      setSelectedEntity(entities[0]);
    } else if (entities.length === 0) {
      setSelectedEntity(undefined);
    }
  }, [entities, selectedEntity]);

  React.useEffect(() => {
    // Reset worker result and tab state when data source file changes
    setWorkerResult(undefined);
    setImportResult(undefined);
    setActiveTabId("validation");
    setSelectedEntity(undefined);
    setProcessingState("idle");
  }, [dataSourceFile]);

  // Track if we've already notified the parent to prevent multiple calls
  const hasNotifiedRef = React.useRef(false);

  // Helper function to notify parent with final validation result
  const notifyParentWithResult = React.useCallback(
    (finalResult: ValidationResult) => {
      if (onValidationResult && !hasNotifiedRef.current) {
        hasNotifiedRef.current = true;
        onValidationResult(finalResult);
      }
    },
    [onValidationResult]
  );

  // Reset the notification flag when the data source file changes
  React.useEffect(() => {
    hasNotifiedRef.current = false;
  }, [dataSourceFile]);

  React.useEffect(() => {
    const asyncWrapper = async () => {
      if (!dataSourceFile) {
        setError("An error occurred importing data: No file found to import.");
        return;
      }
      setProcessingState("worker");

      try {
        const result = await importDataWorker({
          schemas,
          dataSourceFile,
          sheetToEntityMappings,
        });

        // Set initial result immediately to show UI
        setWorkerResult(result);
        setProcessingState("backend");

        // Process backend validation requests asynchronously in main thread
        setTimeout(async () => {
          try {
            const updatedImportResult = await processBackendValidationAsync(result);
            // Notify parent now that backend validation is complete
            notifyParentWithResult(updatedImportResult);
            setProcessingState("complete");
          } catch (backendError) {
            console.error("Backend validation failed:", backendError);
          }
        }, 0);
        if (result === undefined) {
          setError("An error occurred importing data: no data returned from import");
          setProcessingState("error");
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : UNEXPECTED_ERROR;
        setError(message);
        setProcessingState("error");
      }
    };
    asyncWrapper();
  }, [
    schemas,
    dataSourceFile,
    importDataWorker,
    sheetToEntityMappings,
    notifyParentWithResult,
    entities,
    processBackendValidationAsync,
  ]);

  // Function to trigger re-validation
  const handleRevalidate = React.useCallback(async () => {
    if (!dataSourceFile) return;

    // Update local schemas to remove server_name regex
    const updatedSchemas = {
      ...localSchemas,
      server: {
        ...localSchemas.server,
        attributes:
          localSchemas.server?.attributes?.map((attr) =>
            attr.name === "server_name" ? { ...attr, validation_regex: "" } : attr
          ) || [],
      },
    };

    setLocalSchemas(updatedSchemas);
    setProcessingState("worker");

    try {
      const result = await importDataWorker({
        schemas: updatedSchemas,
        dataSourceFile,
        sheetToEntityMappings,
      });

      setWorkerResult(result);
      setProcessingState("backend");

      const updatedImportResult = await processBackendValidationAsync(result);
      // Reset notifyParent flag to notify parent again with updated validation result
      hasNotifiedRef.current = false;
      notifyParentWithResult(updatedImportResult);
      setProcessingState("complete");
    } catch (error) {
      console.error("Re-validation failed:", error);
      setProcessingState("error");
    }
  }, [
    dataSourceFile,
    localSchemas,
    sheetToEntityMappings,
    importDataWorker,
    processBackendValidationAsync,
    notifyParentWithResult,
  ]);

  const renderValidationTabs = () => {
    if (!workerResult?.validationResult || !importResult) return null;

    return (
      <SpaceBetween size="l">
        <ImportSummary validationResult={workerResult.validationResult} />
        <EntitySelection
          schemas={schemas}
          entities={entities}
          selectedEntity={selectedEntity}
          onEntitySelectionChange={setSelectedEntity}
        />
        <Tabs
          activeTabId={activeTabId}
          onChange={({ detail }) => setActiveTabId(detail.activeTabId)}
          tabs={[
            {
              id: "validation",
              label: "Validation Issues",
              content: (
                <ValidationResultsTable
                  schemas={localSchemas}
                  validationIssues={importResult.issues}
                  entityFilter={selectedEntity}
                  header="Validation Results"
                  onRevalidate={handleRevalidate}
                />
              ),
            },
            {
              id: "entities",
              label: "Validated Entities",
              content: (
                <SpaceBetween size="l">
                  <ImportedEntitiesTable
                    entitiesToCreate={importResult.entitiesToCreate}
                    entitiesToUpdate={importResult.entitiesToUpdate}
                    entityFilter={selectedEntity}
                  />
                </SpaceBetween>
              ),
            },
          ]}
        />
      </SpaceBetween>
    );
  };

  return (
    <>
      {processingState === "complete" && renderValidationTabs()}
      {(processingState === "idle" || processingState === "worker" || processingState === "backend") && (
        <Container>
          <Box textAlign="center" padding={{ top: "xxxl", bottom: "xxxl" }}>
            <SpaceBetween size="m" direction="vertical" alignItems="center">
              <Spinner size="large" />
              <Box variant="h3" color="text-status-info">
                Importing and validating data...
              </Box>
              <Box variant="p" color="text-body-secondary">
                This may take a moment depending on the size of your data file.
              </Box>
            </SpaceBetween>
          </Box>
        </Container>
      )}
      {processingState === "error" && (
        <Container>
          <Box textAlign="center" padding={{ top: "xxxl", bottom: "xxxl" }}>
            <SpaceBetween size="m" direction="vertical" alignItems="center">
              <StatusIndicator type="error" />
              <Box variant="h3" color="text-status-error">
                An error occurred importing data
              </Box>
              <Box variant="p" color="text-body-secondary">
                {error}
              </Box>
            </SpaceBetween>
          </Box>
        </Container>
      )}
    </>
  );
};

export default DSWImportData;
