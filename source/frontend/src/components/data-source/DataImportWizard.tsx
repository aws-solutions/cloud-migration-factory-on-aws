import * as React from "react";
import Wizard from "@cloudscape-design/components/wizard";
import { useNavigate } from "react-router-dom";
import { AppChildProps } from "../../models";
import {
  SpaceBetween,
  FileUpload,
  FileUploadProps,
  FormField,
  Container,
  Header,
  Box,
  TextContent,
  KeyValuePairs,
  NonCancelableCustomEvent,
} from "@cloudscape-design/components";
import { DataSource } from "../../models/DataSource";
import { NotificationContext } from "../../contexts/NotificationContext";
import DataSourcesTable from "./DataSourcesTable";
import DSWImportData, { ValidationResult } from "./DSWImportData";
import { SheetToEntityMapping } from "./data-source-types";
import ToolsApiClient from "../../api_clients/toolsApiClient";
import { apiActionErrorHandler } from "../../resources/recordFunctions";
import { mappableEntitySchemas } from "../../utils/schema-utils";

const DataImportWizard = (props: AppChildProps) => {
  const navigate = useNavigate();
  const { addNotification } = React.useContext(NotificationContext);

  const [selectedDataSource, setSelectedDataSource] = React.useState<DataSource | undefined>();
  const [activeStepIndex, setActiveStepIndex] = React.useState(0);
  const [isSaving, setIsSaving] = React.useState<boolean>(false);
  const [uploadedFile, setUploadedFile] = React.useState<File | undefined>();
  const [fileUploadError, setFileUploadError] = React.useState<string | undefined>();
  const [validationResult, setValidationResult] = React.useState<ValidationResult | undefined>(undefined);

  // Filter schemas for import process
  const schemas = React.useMemo(() => mappableEntitySchemas(props.schemas), [props.schemas]);

  // Memoize the validation result handler to prevent unnecessary re-renders
  const handleValidationResult = React.useCallback((result: ValidationResult) => {
    setValidationResult(result);
  }, []);

  // Convert data source header mappings to sheet-to-entity mappings
  const sheetToEntityMappings: SheetToEntityMapping[] = React.useMemo(() => {
    if (!selectedDataSource?.header_mappings) {
      return [];
    }

    return selectedDataSource.header_mappings.map((mapping) => ({
      ...mapping,
      entityNames: Array.from(
        new Set(mapping.headers.flatMap((header) => header.entityAttributes.map((attr) => attr.entityName)))
      ),
      isSelected: true,
    }));
  }, [selectedDataSource]);

  const handleCancel = () => {
    navigate("/wave-planning/data-import");
  };

  const handleDataSourceSelection = (selectedItems: DataSource[]) => {
    setSelectedDataSource(selectedItems.length > 0 ? selectedItems[0] : undefined);
  };

  const isStepOneValid = () => {
    return selectedDataSource !== undefined;
  };

  const isStepTwoValid = () => {
    return uploadedFile !== undefined;
  };

  const isStepThreeValid = () => {
    return (
      (validationResult?.entitiesToCreate?.length ?? 0) > 0 || (validationResult?.entitiesToUpdate?.length ?? 0) > 0
    );
  };

  const handleFileChange = (event: NonCancelableCustomEvent<FileUploadProps.ChangeDetail>) => {
    setFileUploadError(undefined);

    const {
      detail: { value },
    } = event;

    if (value.length > 1) {
      setFileUploadError("Only one file can be uploaded at a time");
      setUploadedFile(undefined);
      setValidationResult(undefined);
      return;
    }

    if (value.length === 0) {
      setUploadedFile(undefined);
      setValidationResult(undefined);
      return;
    }

    const file = value[0];

    // Validate file type based on data source configuration
    if (selectedDataSource?.file_name) {
      const expectedExtension = selectedDataSource.file_name.split(".").pop()?.toLowerCase();
      const fileExtension = file.name.split(".").pop()?.toLowerCase();

      if (expectedExtension && fileExtension && expectedExtension !== fileExtension) {
        setFileUploadError(`Expected ${expectedExtension.toUpperCase()} file, but got ${fileExtension.toUpperCase()}`);
        setUploadedFile(undefined);
        setValidationResult(undefined);
        return;
      }
    }

    setUploadedFile(file);
    // Reset validation result when file changes
    setValidationResult(undefined);
  };

  const handleSubmit = async () => {
    if (!selectedDataSource || !uploadedFile || !validationResult) {
      addNotification({
        type: "error",
        header: "Import Failed",
        content: "Missing required data for import. Please ensure all steps are completed.",
        dismissible: true,
      });
      return;
    }

    setIsSaving(true);

    try {
      const toolsApiClient = new ToolsApiClient();

      // Generate presigned URL
      const allEntities = [...validationResult.entitiesToCreate, ...validationResult.entitiesToUpdate];
      const createUploadJobResponse = await toolsApiClient.createUploadDataJob({
        updated_schemas: Array.from(new Set(allEntities.map((entity) => entity.entityName))),
        data_source_id: selectedDataSource.data_source_id ?? "-",
        filename: uploadedFile.name,
        file_size: uploadedFile.size,
        total_entities: allEntities.reduce((sum, entity) => sum + Object.keys(entity.data || {}).length, 0),
      });

      // Prepare the data payload from validation results
      const s3UploadRequest = {
        entities_to_create: validationResult.entitiesToCreate,
        entities_to_update: validationResult.entitiesToUpdate,
        issues: validationResult.issues,
      };

      // Upload the data to S3 (metadata is already included in presigned URL)
      await toolsApiClient.uploadJsonToPresignedUrl(
        createUploadJobResponse.presigned_url,
        s3UploadRequest,
        createUploadJobResponse.s3_object_metadata
      );

      // Show success notification
      addNotification({
        type: "success",
        header: "Import Started",
        content: `Data import has been initiated successfully. Upload ID: ${createUploadJobResponse.id}`,
        dismissible: true,
      });

      // Navigate back to data import page
      navigate("/wave-planning/data-import");
    } catch (error) {
      console.error("Import failed:", error);

      apiActionErrorHandler("Import", "data", error, addNotification);
    } finally {
      setIsSaving(false);
    }
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
          nextButton: "Next",
        }}
        onNavigate={({ detail }) => {
          const { requestedStepIndex, reason } = detail;

          // Validate current step before proceeding
          if (activeStepIndex === 0 && requestedStepIndex >= 1 && !isStepOneValid()) {
            if (reason === "next") {
              addNotification({
                type: "warning",
                header: "Selection Required",
                content: "Please select a data source to continue.",
                dismissible: true,
              });
            }
            return;
          }

          if (activeStepIndex === 1 && requestedStepIndex >= 2 && !isStepTwoValid()) {
            if (reason === "next") {
              addNotification({
                type: "warning",
                header: "File Required",
                content: "Please upload a data file to continue.",
                dismissible: true,
              });
            }
            return;
          }

          if (activeStepIndex === 2 && requestedStepIndex >= 3 && !isStepThreeValid()) {
            if (reason === "next") {
              addNotification({
                type: "warning",
                header: "Entities Required",
                content: "There must be at least one valid entity to proceed",
                dismissible: true,
              });
            }
            return;
          }

          setActiveStepIndex(requestedStepIndex);
        }}
        onCancel={handleCancel}
        onSubmit={handleSubmit}
        isLoadingNextStep={isSaving}
        activeStepIndex={activeStepIndex}
        submitButtonText="Import Data"
        steps={[
          {
            title: "Select data source",
            description:
              "Select the data source your data set maps to. This should have been created by your administrator",
            isOptional: false,
            content: (
              <DataSourcesTable
                schemas={schemas}
                editable={false}
                selectionType="single"
                onSelectionChange={handleDataSourceSelection}
                selectedDataSources={selectedDataSource ? [selectedDataSource] : undefined}
              />
            ),
          },
          {
            title: "Upload file",
            description: "Upload the data file that matches your selected data source configuration",
            content: (
              <SpaceBetween size="m">
                <Container header={<Header>Upload Data File</Header>}>
                  <FormField label="Data file" errorText={fileUploadError}>
                    <FileUpload
                      onChange={handleFileChange}
                      multiple={false}
                      value={uploadedFile ? [uploadedFile] : []}
                      i18nStrings={{
                        uploadButtonText: () => "Choose file",
                        dropzoneText: () => "Drop file to upload",
                        removeFileAriaLabel: () => "Remove file",
                        errorIconAriaLabel: "Error",
                        warningIconAriaLabel: "Warning",
                        limitShowFewer: "Show fewer files",
                        limitShowMore: "Show more files",
                      }}
                      showFileLastModified
                      showFileSize
                      showFileThumbnail
                      tokenLimit={1}
                      constraintText={
                        selectedDataSource?.file_name
                          ? `The file format must match your selected data source configuration. Expected format: ${selectedDataSource.file_name.split(".").pop()?.toUpperCase()}`
                          : ".xlsx, .xls or .csv files"
                      }
                      accept={".xlsx,.xls,.csv"}
                    />
                  </FormField>
                </Container>
              </SpaceBetween>
            ),
          },
          {
            title: "Review data",
            description: "Review data to be imported and any validation errors before importing",
            content: (
              <DSWImportData
                schemas={schemas}
                sheetToEntityMappings={sheetToEntityMappings}
                dataSourceFile={uploadedFile}
                onValidationResult={handleValidationResult}
                reloadSchema={props.reloadSchema}
              />
            ),
          },
          {
            title: "Import data",
            description: "Review your selections and start the data import process",
            content: (
              <SpaceBetween size="m">
                <Container header={<Header>Data Source Configuration</Header>}>
                  {selectedDataSource && (
                    <KeyValuePairs
                      columns={2}
                      items={[
                        {
                          label: "Data Source",
                          value: selectedDataSource.data_source_name,
                        },
                        {
                          label: "Description",
                          value: selectedDataSource.data_source_description ?? "-",
                        },
                        {
                          label: "File Template",
                          value: selectedDataSource.file_name,
                        },
                        {
                          label: "Header Mappings",
                          value: `${selectedDataSource.header_mappings?.length || 0} configured`,
                        },
                      ]}
                    />
                  )}
                </Container>

                <Container header={<Header>Upload Details</Header>}>
                  {uploadedFile && (
                    <KeyValuePairs
                      columns={2}
                      items={[
                        {
                          label: "File Name",
                          value: uploadedFile.name,
                        },
                        {
                          label: "File Size",
                          value: `${(uploadedFile.size / 1024 / 1024).toFixed(2)} MB`,
                        },
                        {
                          label: "Entities to be imported",
                          value: `${
                            validationResult
                              ? [...validationResult.entitiesToCreate, ...validationResult.entitiesToUpdate].reduce(
                                  (sum, entity) => sum + Object.keys(entity.data || {}).length,
                                  0
                                )
                              : 0
                          }`,
                        },
                        {
                          label: "File Type",
                          value: uploadedFile.name.split(".").pop()?.toUpperCase() || "Unknown",
                        },
                      ]}
                    />
                  )}
                </Container>

                <Container header={<Header>Import Process</Header>}>
                  <Box>
                    <TextContent>
                      <p>Clicking &quot;Import Data&quot; will:</p>
                      <ul>
                        <li>Upload your file to the system</li>
                        <li>Process the data according to the selected data source configuration</li>
                        <li>Import the validated data into the system</li>
                      </ul>
                      <p>
                        <strong>Note:</strong> This process may take several minutes depending on the file size.
                      </p>
                    </TextContent>
                  </Box>
                </Container>
              </SpaceBetween>
            ),
          },
        ]}
      />
    </SpaceBetween>
  );
};

export default DataImportWizard;
