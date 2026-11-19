import React, { useEffect, useState } from "react";
import {
  Box,
  Container,
  FileUpload,
  FileUploadProps,
  FormField,
  Header,
  Input,
  Multiselect,
  NonCancelableCustomEvent,
  SelectProps,
  SpaceBetween,
  Spinner,
  Table,
  TableProps,
  Textarea,
  TextContent,
} from "@cloudscape-design/components";
import { useWorker, WebWorkerState } from "../../actions/WorkerHook";
import { EntitySchema, HeaderToEntityAttributeMapping } from "../../models";
import { SheetData, SheetToEntityMapping } from "./data-source-types";
import { NotificationContext } from "../../contexts/NotificationContext";
import getSheetHeaderWorker from "./get-sheet-header-data-worker?worker&url";
import { entitySelectOptions } from "./data-source-utils";

export interface DSWConfigureDataSourceProps {
  readonly dataSourceId?: string;
  readonly name: string;
  readonly description: string;
  readonly file?: File;
  readonly loadedDataSourceFilename?: string;
  readonly sheetToEntityMappings: SheetToEntityMapping[];
  readonly sheetLoadingState?: WebWorkerState;
  readonly schemas: Record<string, EntitySchema>;
  readonly onNameChange: (name: string) => void;
  readonly onDescriptionChange: (description: string) => void;
  readonly onFileChange: (file?: File) => void;
  readonly onSheetToEntityMappingsChange: (SheetToEntityMappings: SheetToEntityMapping[]) => void;
  readonly onSheetLoadingStateChange: (sheetLoadingState?: WebWorkerState) => void;
  readonly onSheetToEntityMappingChanged: (sheetToEntityMapping: SheetToEntityMapping) => void;
  readonly isChooseEntitiesSelectorValid: (sheetToEntityMappings: SheetToEntityMapping[]) => boolean;
}

/**
 * Data source import wizard step one control.
 */
const DSWConfigureDataSource = (props: DSWConfigureDataSourceProps) => {
  const {
    dataSourceId,
    name,
    description,
    file,
    loadedDataSourceFilename,
    sheetToEntityMappings,
    sheetLoadingState,
    schemas,
    onNameChange,
    onDescriptionChange,
    onFileChange,
    onSheetToEntityMappingsChange,
    onSheetLoadingStateChange,
    onSheetToEntityMappingChanged,
    isChooseEntitiesSelectorValid,
  } = props;

  const { addNotification } = React.useContext(NotificationContext);

  const [headersWorker, controller] = useWorker<File, SheetData[]>(new URL(getSheetHeaderWorker, import.meta.url));

  const [fileError, setFileError] = useState<string | undefined>();
  const [dataSourceError, setDataSourceError] = useState<string | undefined>();

  React.useEffect(() => {
    setFileError(!file ? "You must upload a valid file for the data source." : undefined);
  }, [file]);

  React.useEffect(() => {
    setDataSourceError(
      !isChooseEntitiesSelectorValid(sheetToEntityMappings)
        ? "At least one sheet must be mapped to an entity."
        : undefined
    );
  }, [sheetToEntityMappings, isChooseEntitiesSelectorValid]);

  const displayUpdateDatasourceWarningNotification = React.useCallback(
    (
      removedSheets: SheetToEntityMapping[],
      removedHeaders: {
        sheetName: string;
        headers: HeaderToEntityAttributeMapping[];
      }[]
    ) => {
      const removedSheetsString = removedSheets.map((sheet) => sheet.sheetName).join(", ");
      const removedHeadersString = removedHeaders
        .map((sheet) => {
          return `${sheet.sheetName}: ${sheet.headers.map((header) => header.name).join(", ")}`;
        })
        .join(", ");
      addNotification({
        type: "warning",
        header: "Warning",
        content: (
          <Box>
            <SpaceBetween size="xs">
              <Box>
                The updated data source has these previously mapped items removed, continuing will lose previous
                mappings.
              </Box>
              <SpaceBetween size="xxxs">
                <Box variant="h5">Sheets</Box>
                <Box>{removedSheetsString}</Box>
              </SpaceBetween>
              <SpaceBetween size="xxxs">
                <Box variant="h5">Headers</Box>
                <Box>{removedHeadersString}</Box>
              </SpaceBetween>
            </SpaceBetween>
          </Box>
        ),
        dismissible: true,
      });
    },
    [addNotification]
  );

  const sheetsLoaded = React.useCallback(
    (result: SheetData[]) => {
      const existingSheetToEntityMappings = dataSourceId === undefined ? [] : structuredClone(sheetToEntityMappings);
      const removedHeaders: {
        sheetName: string;
        headers: HeaderToEntityAttributeMapping[];
      }[] = [];
      const newSheetToEntityMapping: SheetToEntityMapping[] = (result as SheetData[]).map((sheetData) => {
        const entityNames: string[] = [];
        const headers: HeaderToEntityAttributeMapping[] = sheetData.headers.map((header) => {
          return {
            ...header,
            entityAttributes: [],
          };
        });
        let isSelected = false;

        const existingMappingIndex = existingSheetToEntityMappings.findIndex((mapping) => {
          return mapping.sheetName === sheetData.name;
        });

        if (existingMappingIndex !== -1) {
          // this is the scenario if we're editing an exisiting data source and need
          // to merge in the previously loaded mappings into the newly loaded data source
          const existingMapping = existingSheetToEntityMappings[existingMappingIndex];
          entityNames.push(...existingMapping.entityNames);
          isSelected = existingMapping.isSelected;
          // merge headers
          headers.forEach((newHeader) => {
            const existingHeaderIndex = existingMapping.headers.findIndex((existingHeader) => {
              return existingHeader.name === newHeader.name;
            });

            if (existingHeaderIndex !== -1) {
              newHeader.entityAttributes.push(...existingMapping.headers[existingHeaderIndex].entityAttributes);
              existingMapping.headers.splice(existingHeaderIndex, 1);
            }
          });

          if (existingMapping.headers.length > 0) {
            removedHeaders.push({
              sheetName: existingMapping.sheetName,
              headers: existingMapping.headers,
            });
          }
          existingSheetToEntityMappings.splice(existingMappingIndex, 1);
        }

        return {
          sheetName: sheetData.name,
          headers,
          entityNames,
          isSelected,
        };
      });

      if (existingSheetToEntityMappings.length > 0 || removedHeaders.length > 0) {
        displayUpdateDatasourceWarningNotification(existingSheetToEntityMappings, removedHeaders);
      }

      onSheetToEntityMappingsChange(newSheetToEntityMapping);
    },
    [dataSourceId, displayUpdateDatasourceWarningNotification, onSheetToEntityMappingsChange, sheetToEntityMappings]
  );

  const handleFileChange = async (event: NonCancelableCustomEvent<FileUploadProps.ChangeDetail>) => {
    setFileError(undefined);

    const {
      detail: { value },
    } = event;
    if (value.length > 1) {
      setFileError("Only one file can be uploaded at a time");
      onFileChange(undefined);
      return;
    }

    if (value.length === 0 && dataSourceId === undefined) {
      setFileError(undefined);
      onFileChange(undefined);
      onSheetLoadingStateChange(undefined);
      onSheetToEntityMappingsChange([]);
      return;
    }
    onFileChange(value[0]);

    try {
      const headers = await headersWorker(value[0]);
      sheetsLoaded(headers);
    } catch (error) {
      setFileError(`Error reading file:${(error as Error).message}`);
      onSheetLoadingStateChange(undefined);
      onSheetToEntityMappingsChange([]);
    }
  };

  useEffect(() => {
    onSheetLoadingStateChange(controller.state);
  }, [controller.state, onSheetLoadingStateChange]);

  const onSheetSelectionChange = React.useCallback(
    (event: NonCancelableCustomEvent<TableProps.SelectionChangeDetail<SheetToEntityMapping>>) => {
      const updatedItems: SheetToEntityMapping[] = sheetToEntityMappings.map((mapping) => ({
        sheetName: mapping.sheetName,
        headers: mapping.headers,
        entityNames: mapping.entityNames,
        isSelected: !!event.detail.selectedItems.find((selectedItem) => selectedItem.sheetName === mapping.sheetName),
      }));
      onSheetToEntityMappingsChange(updatedItems);
    },
    [onSheetToEntityMappingsChange, sheetToEntityMappings]
  );
  const multiSelectEntityOptions: SelectProps.Option[] = React.useMemo(() => entitySelectOptions(schemas), [schemas]);

  // dataSourceId being present indicates we've loaded an existing data source
  const showChooseEntities =
    sheetLoadingState === "working" || sheetLoadingState === "complete" || sheetToEntityMappings.length > 0;

  return (
    <SpaceBetween size="m">
      <Container header={<Header>General settings</Header>}>
        <FormField
          label={"Name"}
          errorText={name.length === 0 ? "You must provide a name for the data source." : undefined}
        >
          <Input value={name} onChange={(event) => onNameChange(event.detail.value)} />
        </FormField>
        <FormField label={"Description"}>
          <Textarea value={description} onChange={(event) => onDescriptionChange(event.detail.value)} />
        </FormField>
      </Container>
      <Container header={<Header>Upload data source</Header>}>
        <FormField
          errorText={fileError}
          description={
            <Box>For more information on type of files and supported data attributes, please refer to FAQ</Box>
          }
        >
          <SpaceBetween size="s">
            {loadedDataSourceFilename && (
              <Box>
                <TextContent>
                  <i>
                    Previously imported from file <b>{loadedDataSourceFilename}</b>
                  </i>
                </TextContent>
              </Box>
            )}
            <FileUpload
              onChange={handleFileChange}
              multiple={false}
              value={file ? [file] : []}
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
              constraintText=".xlsx, .xls or .csv files"
              accept=".xlsx,.xls,.csv"
            />
          </SpaceBetween>
        </FormField>
      </Container>
      {showChooseEntities && (
        <Container header={<Header>Choose entities</Header>}>
          {sheetLoadingState === "working" && (
            <Box textAlign={"center"}>
              <Spinner />
            </Box>
          )}
          {(sheetLoadingState === "complete" || sheetToEntityMappings.length > 0) && (
            <SpaceBetween size={"s"}>
              <Table
                selectionType="multi"
                selectedItems={sheetToEntityMappings.filter((mapping) => mapping.isSelected)}
                onSelectionChange={onSheetSelectionChange}
                items={sheetToEntityMappings.sort((a, b) => a.sheetName.localeCompare(b.sheetName))}
                columnDefinitions={[
                  {
                    header: "Sheet name",
                    cell: (item) => <Box fontWeight={item.isSelected ? "normal" : "light"}>{item.sheetName}</Box>,
                  },
                  {
                    header: "Mapped entities",
                    width: 350,
                    cell: (item) => (
                      <Multiselect
                        disabled={!item.isSelected}
                        expandToViewport
                        inlineTokens
                        invalid={item.isSelected && item.entityNames.length === 0}
                        options={multiSelectEntityOptions}
                        onChange={(event) => {
                          const entityNames = event.detail.selectedOptions.map((option) => option.value as string);
                          onSheetToEntityMappingChanged({
                            sheetName: item.sheetName,
                            entityNames,
                            // Clean up the attribute mappings whose entities are no longer selected
                            headers: item.headers.map(({ name, previewValues, entityAttributes }) => ({
                              name,
                              previewValues,
                              entityAttributes: entityAttributes.filter((ea) => entityNames.includes(ea.entityName)),
                            })),
                            isSelected: item.isSelected,
                          });
                        }}
                        selectedOptions={multiSelectEntityOptions.filter((o) =>
                          item.entityNames.includes(o.value ?? "")
                        )}
                      />
                    ),
                  },
                ]}
              />
              {dataSourceError && <FormField errorText={dataSourceError}></FormField>}
            </SpaceBetween>
          )}
        </Container>
      )}
    </SpaceBetween>
  );
};

export default DSWConfigureDataSource;
