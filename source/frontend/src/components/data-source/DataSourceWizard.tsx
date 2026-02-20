import * as React from "react";
import Wizard from "@cloudscape-design/components/wizard";
import { Location, useLocation, useNavigate } from "react-router-dom";
import DSWConfigureDataSource from "./DSWConfigureDataSource";
import DSWManageHeaderMappings from "./DSWManageHeaderMappings";
import { WebWorkerState } from "../../actions/WorkerHook";
import { AppChildProps, Attribute, EntitySchema } from "../../models";
import { SheetToEntityMapping } from "./data-source-types";
import DSWReviewAndSave from "./DSWReviewAndSave";
import { SpaceBetween } from "@cloudscape-design/components";
import {
  createDataSource,
  headerMappingsToSave,
  reconstituteHeaderMappings,
  updateDataSource,
} from "./data-source-utils";
import { DataSource } from "../../models/DataSource";
import { NotificationContext } from "../../contexts/NotificationContext";
import DSWImportData from "./DSWImportData";
import { mappableEntitySchemas } from "../../utils/schema-utils";
import AdminApiClient from "../../api_clients/adminApiClient";

interface NavigationState {
  dataSource?: DataSource;
}

export interface EntitySchemaWithStatus extends EntitySchema {
  attributes: Array<AttributeWithCreationStatus>;
}

export interface AttributeWithCreationStatus extends Attribute {
  status: "SUGGESTION" | "PENDING_CREATION" | "CREATED";
  suggestion?: {
    type: "FILE_HEADERS" | "AI";
    sourceHeader: string;
  };
}

const DataSourceWizard = (props: AppChildProps) => {
  const REVIEW_AND_COMMIT_DATA_SOURCE_INDEX = 2;
  const navigate = useNavigate();
  const { addNotification } = React.useContext(NotificationContext);
  const location: Location<NavigationState> = useLocation();

  const [dataSourceId, setDataSourceId] = React.useState<string | undefined>();

  // State shared across steps
  const [sheetToEntityMappings, setSheetToEntityMappings] = React.useState<SheetToEntityMapping[]>([]);
  const [activeStepIndex, setActiveStepIndex] = React.useState(0);

  // State for step 1
  const [dataSourceName, setDataSourceName] = React.useState("");
  const [dataSourceDescription, setDataSourceDescription] = React.useState("");
  const [dataSourceFile, setDataSourceFile] = React.useState<File | undefined>();
  const [sheetLoadingState, setSheetLoadingState] = React.useState<WebWorkerState | undefined>();
  const [loadedDataSourceFilename, setLoadedDataSourceFilename] = React.useState<string | undefined>();

  // State for step 2
  const [selectedEntityName, setSelectedEntityName] = React.useState<string | undefined>(undefined);
  const [selectedSheetEntityNames, setSelectedSheetEntityNames] = React.useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = React.useState<string | undefined>();

  // State for step 3
  const [isSaving, setIsSaving] = React.useState<boolean>(false);

  const handleCancel = () => {
    navigate("/admin/wave-planning/");
  };

  const [schemas, setSchemas] = React.useState<Record<string, EntitySchemaWithStatus>>(() => {
    const mappableSchemas = mappableEntitySchemas(props.schemas);
    const schemasWithStatus: Record<string, EntitySchemaWithStatus> = {};

    // Iterate through each schema
    Object.keys(mappableSchemas).forEach((schemaKey) => {
      const schema = mappableSchemas[schemaKey];

      // Create a new schema with status-enabled attributes
      schemasWithStatus[schemaKey] = {
        ...schema,
        attributes: schema.attributes.map((attribute) => ({
          ...attribute,
          status: "CREATED",
        })),
      };
    });

    return schemasWithStatus;
  });

  const savePendingSchemaAttributes = async (): Promise<Record<string, EntitySchemaWithStatus>> => {
    const apiAdmin = new AdminApiClient();
    const updatedSchemas = { ...schemas };
    const attributesToAdd: Array<{ schemaKey: string; attribute: Attribute }> = [];

    // Identify PENDING_CREATION attributes and prepare for backend calls
    Object.keys(updatedSchemas).forEach((schemaKey) => {
      const schema = updatedSchemas[schemaKey];

      const pendingAttributes = schema.attributes.filter((attr) => attr.status === "PENDING_CREATION");

      if (pendingAttributes.length > 0) {
        // Add each PENDING_CREATION attribute to the list for backend creation
        pendingAttributes.forEach((attribute) => {
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          const { status, suggestion, ...attributeForApi } = attribute;
          attributesToAdd.push({
            schemaKey,
            attribute: attributeForApi,
          });
        });

        updatedSchemas[schemaKey] = {
          ...schema,
          attributes: schema.attributes.map((attribute) => ({
            ...attribute,
            status: attribute.status === "PENDING_CREATION" ? "CREATED" : attribute.status,
          })),
        };
      }
    });

    // Second pass: make backend calls to add new attributes
    if (attributesToAdd.length > 0) {
      try {
        // Add each PENDING attribute to its schema using postSchemaAttr sequentially
        // Don't do in parallel - the backend loses updates if you do so
        for (const { schemaKey, attribute } of attributesToAdd) {
          await apiAdmin.postSchemaAttr(schemaKey, attribute);
        }

        // Update local state only after successful backend updates
        setSchemas(updatedSchemas);

        // Show success notification
        addNotification({
          type: "success",
          dismissible: true,
          header: "Schema attributes saved",
          content: `Successfully added ${attributesToAdd.length} AI-recommended attribute(s) to schema(s).`,
        });
      } catch (error) {
        console.error("Error saving schema attributes:", error);

        // Show error notification
        addNotification({
          type: "error",
          dismissible: true,
          header: "Error saving schema attributes",
          content: "Failed to save AI-recommended attributes to schemas.",
        });

        // Return original schemas on error
        return schemas;
      } finally {
        // Quietly reload schema so that the newly added attributes are visible
        props.reloadSchema(true);
      }
    }

    return updatedSchemas;
  };

  React.useEffect(() => {
    if (location.state?.dataSource) {
      const { data_source_id, data_source_name, data_source_description, header_mappings, file_name } =
        location.state.dataSource;
      if (!data_source_id) {
        return;
      }
      const reconstituedMappings = reconstituteHeaderMappings(header_mappings);

      setDataSourceId(data_source_id);
      setDataSourceName(data_source_name);
      setDataSourceDescription(data_source_description);
      setSheetToEntityMappings(reconstituedMappings);
      setLoadedDataSourceFilename(file_name);
    }
  }, [location]);

  const sheetToEntityUpdate = React.useCallback((sheetToEntityMapping: SheetToEntityMapping) => {
    setSheetToEntityMappings((prev) => {
      const index = prev.findIndex((item) => item.sheetName === sheetToEntityMapping.sheetName);
      if (index !== -1) {
        const updated = [...prev];
        if (
          !updated[index].entityNames.every((entity) => {
            return sheetToEntityMapping.entityNames.includes(entity);
          })
        ) {
          setSelectedEntityName(undefined);
          setSelectedSheet(undefined);
        }
        updated[index] = sheetToEntityMapping;
        return updated;
      }
      return prev;
    });
  }, []);

  const sheetToEntityMappingsUpdate = React.useCallback(
    (sheetToEntityMappings: SheetToEntityMapping[]) => {
      const selectedSheetFromMapping = sheetToEntityMappings.find((mapping) => {
        return mapping.sheetName === selectedSheet;
      });
      if (selectedSheetFromMapping?.isSelected === false) {
        setSelectedSheet(undefined);
        setSelectedEntityName(undefined);
      }
      setSheetToEntityMappings(sheetToEntityMappings);
    },
    [selectedSheet]
  );

  const unmappedEntityIdentifiers = React.useMemo(() => {
    const unmappedEntityIdentifiersMap = new Map<string, string[]>();
    for (const sheetToEntityMapping of sheetToEntityMappings) {
      if (sheetToEntityMapping.isSelected) {
        const { sheetName } = sheetToEntityMapping;
        for (const entityName of sheetToEntityMapping.entityNames) {
          const foundKey = sheetToEntityMapping.headers.some((header) => {
            return (
              header.entityAttributes.find((entityAttribute) => {
                return entityAttribute.attributeName === `${entityName === "application" ? "app" : entityName}_name`;
              }) !== undefined
            );
          });
          if (!foundKey) {
            if (unmappedEntityIdentifiersMap.has(sheetName)) {
              unmappedEntityIdentifiersMap.get(sheetName)?.push(entityName);
            } else {
              unmappedEntityIdentifiersMap.set(sheetName, [entityName]);
            }
          }
        }
      }
    }
    return unmappedEntityIdentifiersMap;
  }, [sheetToEntityMappings]);

  const dataSourceEntityRequestBody = (): DataSource => {
    return {
      data_source_id: dataSourceId,
      data_source_name: dataSourceName,
      data_source_description: dataSourceDescription,
      data_source_type: "File",
      file_name: dataSourceFile?.name ?? loadedDataSourceFilename ?? "unknown",
      header_mappings: headerMappingsToSave(sheetToEntityMappings),
    };
  };

  const saveDataSource = async () => {
    const entity = dataSourceEntityRequestBody();
    return entity.data_source_id === undefined ? await createDataSource(entity) : await updateDataSource(entity);
  };

  const isChooseEntitiesSelectorValid = (sheetToEntityMappings: SheetToEntityMapping[]) => {
    const selectedSheets = sheetToEntityMappings.filter((mapping) => {
      return mapping.isSelected;
    });
    return selectedSheets.length > 0 && selectedSheets.every((mapping) => mapping.entityNames.length > 0);
  };

  const isStepOneValid = () => {
    return (
      dataSourceName.length > 0 && isChooseEntitiesSelectorValid(sheetToEntityMappings) && dataSourceFile !== undefined
    );
  };

  /**
   * Checks that each sheet has a mapping to an entity identifier for each
   * entity it maps to.
   */
  const isStepTwoValid = () => {
    return unmappedEntityIdentifiers.size === 0;
  };

  return (
    <SpaceBetween size="m">
      <Wizard
        i18nStrings={{
          stepNumberLabel: (stepNumber) => `Step ${stepNumber}`,
          collapsedStepsLabel: (stepNumber, stepsCount) => `Step ${stepNumber} of ${stepsCount}`,
          navigationAriaLabel: "Steps",
          cancelButton: "Cancel",
          previousButton: "Previous",
          nextButton:
            activeStepIndex === REVIEW_AND_COMMIT_DATA_SOURCE_INDEX ? "Save Data Source and dry run import" : "Next",
        }}
        onNavigate={async ({ detail }) => {
          const { requestedStepIndex, reason } = detail;

          // Validate step 1 before proceeding
          if (activeStepIndex === 0 && requestedStepIndex >= 1 && !isStepOneValid()) {
            if (reason === "next") {
              addNotification({
                type: "warning",
                header: "Selection Required",
                content: "Please complete the form to continue",
                dismissible: true,
              });
            }
            return;
          }

          // Validate step 2 before proceeding
          if (activeStepIndex === 1 && requestedStepIndex >= 2 && !isStepTwoValid()) {
            if (reason === "next") {
              addNotification({
                type: "warning",
                header: "Selection Required",
                content: "Please map all entity identifiers before continuing",
                dismissible: true,
              });
            }
            return;
          }

          if (
            activeStepIndex === REVIEW_AND_COMMIT_DATA_SOURCE_INDEX &&
            requestedStepIndex > REVIEW_AND_COMMIT_DATA_SOURCE_INDEX
          ) {
            setIsSaving(true);
            try {
              await savePendingSchemaAttributes();
              const response = await saveDataSource();
              if (response?.dataSourceId) {
                setDataSourceId(response.dataSourceId);
              } else {
                const message = response?.error ?? "Unknown error occurred";
                addNotification({
                  type: "error",
                  header: "Error",
                  content: message,
                  dismissible: true,
                });
                return;
              }
            } finally {
              setIsSaving(false);
            }
          }

          setActiveStepIndex(requestedStepIndex);
        }}
        onCancel={handleCancel}
        isLoadingNextStep={isSaving}
        activeStepIndex={activeStepIndex}
        submitButtonText="Save Data Source and exit"
        onSubmit={() => navigate("/admin/wave-planning")}
        steps={[
          {
            title: "Configure data source",
            content: (
              <DSWConfigureDataSource
                dataSourceId={dataSourceId}
                name={dataSourceName}
                description={dataSourceDescription}
                file={dataSourceFile}
                loadedDataSourceFilename={loadedDataSourceFilename}
                sheetToEntityMappings={sheetToEntityMappings}
                sheetLoadingState={sheetLoadingState}
                schemas={schemas}
                onNameChange={setDataSourceName}
                onDescriptionChange={setDataSourceDescription}
                onFileChange={setDataSourceFile}
                onSheetToEntityMappingsChange={sheetToEntityMappingsUpdate}
                onSheetLoadingStateChange={setSheetLoadingState}
                onSheetToEntityMappingChanged={sheetToEntityUpdate}
                isChooseEntitiesSelectorValid={isChooseEntitiesSelectorValid}
              />
            ),
          },
          {
            title: "Manage header mapping",
            description:
              "Header mapping is an important step and can't be changed later. Please take a moment to validate the mappings.",
            content: (
              <DSWManageHeaderMappings
                sheetToEntityMappings={sheetToEntityMappings}
                selectedSheet={selectedSheet}
                selectedEntityName={selectedEntityName}
                selectedSheetEntityNames={selectedSheetEntityNames}
                schemas={schemas}
                unmappedEntityIdentifiers={unmappedEntityIdentifiers}
                onSelectedSheetChange={(sheetName) => {
                  setSelectedSheet(sheetName);
                  setSelectedEntityName(undefined);
                }}
                onSheetToEntityMappingChanged={sheetToEntityUpdate}
                onSelectedEntityNameChanged={setSelectedEntityName}
                onSelectedSheetEntityNamesChanged={(selectedSheetEntityNames) => {
                  setSelectedEntityName(undefined);
                  setSelectedSheetEntityNames(selectedSheetEntityNames);
                }}
                onSchemasChanged={setSchemas}
              />
            ),
          },
          {
            title: "Review and commit",
            description: "Review and commit the data source configuration",
            content: (
              <DSWReviewAndSave
                schemas={schemas}
                sheetToEntityMappings={sheetToEntityMappings}
                name={dataSourceName}
                description={dataSourceDescription}
              />
            ),
          },
          {
            title: "Import dry run",
            description:
              "View what a data import would have imported. Note this does not actually import any data into the system",
            content: (
              <DSWImportData
                schemas={schemas}
                sheetToEntityMappings={sheetToEntityMappings}
                dataSourceFile={dataSourceFile}
                reloadSchema={props.reloadSchema}
              />
            ),
          },
        ]}
      />
    </SpaceBetween>
  );
};

export default DataSourceWizard;
