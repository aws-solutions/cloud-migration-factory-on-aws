import React from "react";
import { Auth } from "@aws-amplify/auth";
import {
  Alert,
  Box,
  BoxProps,
  Button,
  ButtonDropdown,
  ColumnLayout,
  Container,
  ExpandableSection,
  Header,
  NonCancelableCustomEvent,
  Select,
  SelectProps,
  SpaceBetween,
  Table,
  TableProps,
  TextContent,
  TextFilter,
} from "@cloudscape-design/components";
import { useCollection } from "@cloudscape-design/collection-hooks";

import { EntitySchema, HeaderToEntityAttributeMapping, HeaderMappingResponse } from "../../models";
import { SheetToEntityMapping } from "./data-source-types";
import { entitySelectOptions, getLabelForEntityAttribute, sanitizeSchema } from "./data-source-utils";
import { createGenAiSocketsClient } from "../../api_clients/genAiSocketsClient";
import ToolsApiClient from "../../api_clients/toolsApiClient";
import { NotificationContext } from "../../contexts/NotificationContext";
import { capitalize } from "../../resources/main";
import { AttributeWithCreationStatus, EntitySchemaWithStatus } from "./DataSourceWizard";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const environment = (window as any).env;

const DISPLAY_STRING_MAX_LENGTH = 100;

const displayTextToExpandableControl = (text: string) => {
  const fullTextContent = (
    <TextContent>
      <i>{text}</i>
    </TextContent>
  );
  return text.length < DISPLAY_STRING_MAX_LENGTH ? (
    fullTextContent
  ) : (
    <ExpandableSection headerText={<Box>{text.substring(0, DISPLAY_STRING_MAX_LENGTH)}...</Box>}>
      {fullTextContent}
    </ExpandableSection>
  );
};

const headerMappingErrorContent = (errorMessage?: string) => {
  const message = `There was an error mapping headers: ${errorMessage ?? "Error unknown"}`;
  return displayTextToExpandableControl(message);
};

const unmappedEntitiesAlert = (
  unmappedEntityIdentifiers: Map<string, string[]>,
  schemas: Readonly<Record<string, EntitySchema>>
) => {
  const unmappedEntityItems: {
    sheetName: string;
    entities: string;
  }[] = unmappedEntityIdentifiers
    .keys()
    .toArray()
    .map((unmappedItem) => {
      const unmappedEntityFriendlyNames = (unmappedEntityIdentifiers.get(unmappedItem) ?? [])
        .map((name) => schemas[name]?.friendly_name ?? capitalize(name))
        .join(", ");
      return {
        sheetName: unmappedItem,
        entities: unmappedEntityFriendlyNames,
      };
    });
  return (
    <Alert
      type="error"
      header={
        <SpaceBetween size="xxs">
          <Box variant="h5" display="inline">
            Unmapped entity identifiers
          </Box>
          <Box display="inline">
            The following entities mapped to sheets are missing their identifier attribute mappings (marked with 🔑). To
            fix this, select each sheet and entity from the dropdown list and map their identifier attributes.
          </Box>
        </SpaceBetween>
      }
    >
      <Table
        items={unmappedEntityItems}
        sortingDisabled
        variant="embedded"
        columnDefinitions={[
          {
            header: "Sheet name",
            cell: (item) => item.sheetName,
          },
          {
            header: "Entities",
            cell: (item) => item.entities,
          },
        ]}
      />
    </Alert>
  );
};

/**
 * Compose request payload to include all headers and schemas of the mapped entities
 * For each schema, only attributes that have not already been mapped are included
 */
const makeRequestForHeaderMapping = async (
  sheetToEntityMapping: SheetToEntityMapping,
  mappableSchemas: Readonly<Record<string, EntitySchemaWithStatus>>,
  client: ReturnType<typeof createGenAiSocketsClient> | ToolsApiClient
): Promise<HeaderMappingResponse> => {
  const headers = sheetToEntityMapping.headers.map(({ name, previewValues }) => ({ name, previewValues }));

  // Build a set of mapped entity attributes as `entityName|attributeName`
  const mappedAttributeSet = new Set<string>(
    sheetToEntityMapping.headers.flatMap((header) =>
      header.entityAttributes.map((entityAttribute) => `${entityAttribute.entityName}|${entityAttribute.attributeName}`)
    )
  );

  const schemas = sheetToEntityMapping.entityNames.reduce<Record<string, Partial<EntitySchema>>>((acc, schemaName) => {
    const mappableSchema = mappableSchemas[schemaName];
    if (!mappableSchema) throw new Error(`Schema ${schemaName} not found`);
    // Given each entity schema, filter out those schema attributes that has been mapped
    // AND only include attributes with status "CREATED" to send to the backend
    const schema = sanitizeSchema(mappableSchema, (attr) => {
      const isNotMapped = !mappedAttributeSet.has(`${schemaName}|${attr.name}`);
      const isCreated = (attr as AttributeWithCreationStatus).status === "CREATED";
      return isNotMapped && isCreated;
    });
    acc[schemaName] = schema;
    return acc;
  }, {});

  // Use websocket client in public mode, toolsApiClient in private mode
  if (client instanceof ToolsApiClient) {
    return client.getHeaders(headers, schemas);
  } else {
    await client.connect();
    return client.mapHeadersSync({ headers, schemas });
  }
};

export interface DSWManageHeaderMappingsProps {
  readonly sheetToEntityMappings: SheetToEntityMapping[];
  readonly selectedSheet?: string;
  readonly selectedEntityName?: string;
  readonly selectedSheetEntityNames: string[];
  readonly schemas: Record<string, EntitySchemaWithStatus>;
  readonly unmappedEntityIdentifiers: Map<string, string[]>;
  readonly onSelectedSheetChange: (sheetName?: string) => void;
  readonly onSheetToEntityMappingChanged: (sheetToEntityMapping: SheetToEntityMapping) => void;
  readonly onSelectedEntityNameChanged: (selectedEntityName?: string) => void;
  readonly onSelectedSheetEntityNamesChanged: (selectedSheetEntityNames: string[]) => void;
  readonly onSchemasChanged: (schemas: Record<string, EntitySchemaWithStatus>) => void;
}

/**
 * Data source import wizard step two control.
 */
const DSWManageHeaderMappings = (props: DSWManageHeaderMappingsProps) => {
  const {
    sheetToEntityMappings,
    selectedSheet,
    selectedEntityName,
    selectedSheetEntityNames,
    schemas,
    unmappedEntityIdentifiers,
    onSelectedSheetChange,
    onSheetToEntityMappingChanged,
    onSelectedEntityNameChanged,
    onSelectedSheetEntityNamesChanged,
    onSchemasChanged,
  } = props;

  const { addNotification } = React.useContext(NotificationContext);
  const [isRequestingHeaders, setIsRequestingHeaders] = React.useState(false);

  const setFlashBarErrorMessage = React.useCallback(
    (message: string | React.ReactNode) => {
      addNotification({
        type: "error",
        header: "Error",
        content: message,
        dismissible: true,
      });
    },
    [addNotification]
  );

  const updateAttributeStatus = React.useCallback(
    (
      schemas: Record<string, EntitySchemaWithStatus>,
      entityName: string,
      attributeName: string,
      fromStatus: AttributeWithCreationStatus["status"],
      toStatus: AttributeWithCreationStatus["status"]
    ): { updatedSchemas: Record<string, EntitySchemaWithStatus>; changed: boolean } => {
      const newSchemas = { ...schemas };
      const schema = newSchemas[entityName];

      if (schema) {
        const attributeInSchema = schema.attributes.find((attr) => attr.name === attributeName);
        if (attributeInSchema && attributeInSchema.status === fromStatus) {
          attributeInSchema.status = toStatus;
          return { updatedSchemas: newSchemas, changed: true };
        }
      }

      return { updatedSchemas: newSchemas, changed: false };
    },
    []
  );

  const clientRef = React.useRef<ReturnType<typeof createGenAiSocketsClient> | null>(null);
  const toolsApiClientRef = React.useRef<ToolsApiClient | null>(null);

  React.useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.disconnect();
        clientRef.current = null;
      }
    };
  }, []);

  // Initialize FILE_HEADERS suggestions for all entities and headers
  React.useEffect(() => {
    const updatedSchemas = { ...schemas };
    let schemaChanged = false;

    // Process all sheet to entity mappings to create FILE_HEADERS suggestions
    for (const sheetToEntityMapping of sheetToEntityMappings) {
      if (!sheetToEntityMapping.isSelected) continue;

      for (const entityName of sheetToEntityMapping.entityNames) {
        const currentSchema = updatedSchemas[entityName] || schemas[entityName];
        if (!currentSchema) continue;

        // Process file headers to create direct attribute suggestions
        for (const header of sheetToEntityMapping.headers) {
          // Skip headers without names
          if (!header.name) continue;

          // Create attribute name by replacing spaces with underscores
          const attributeName = header.name.replace(/\s+/g, "_");

          // Check if an attribute with this name already exists
          const existingAttribute = currentSchema.attributes.find((attr) => attr.name === attributeName);

          if (!existingAttribute) {
            // Add the file header-based attribute to the schema
            const newAttribute: AttributeWithCreationStatus = {
              name: attributeName,
              description: header.name,
              type: "string",
              status: "SUGGESTION",
              system: false,
              long_desc: "Attribute auto-generated during data source creation",
              suggestion: {
                type: "FILE_HEADERS",
                sourceHeader: header.name,
              },
            };

            // Update the schema to include the new attribute
            updatedSchemas[entityName] = {
              ...currentSchema,
              attributes: [...currentSchema.attributes, newAttribute],
            };
            schemaChanged = true;
          }
        }
      }
    }

    // Apply schema changes if any FILE_HEADERS suggestions were added
    if (schemaChanged) {
      onSchemasChanged(updatedSchemas);
    }
  }, [sheetToEntityMappings, schemas, onSchemasChanged]);

  const getClient = React.useCallback(async () => {
    // Only create websocket client if API_GENAISocket is available (public mode)
    if (environment.API_GENAISocket) {
      if (!clientRef.current) {
        if (!environment.API_REGION) {
          throw new Error("Missing required environment variable: API_REGION");
        }

        const session = await Auth.currentSession();
        const idToken = session.getIdToken().getJwtToken();
        clientRef.current = createGenAiSocketsClient({
          apiUrl:
            "wss://" + environment.API_GENAISocket + ".execute-api." + environment.API_REGION + ".amazonaws.com/prod",
          authToken: idToken,
          debug: false,
        });
      }
      return clientRef.current;
    } else {
      // Initialize toolsApiClient for private mode
      toolsApiClientRef.current = new ToolsApiClient();
      return toolsApiClientRef.current;
    }
  }, []);

  const onSelectedSheetChangedInternal = React.useCallback(
    (sheetName?: string) => {
      const selectedMapping = sheetToEntityMappings.find((mapping) => {
        return mapping.sheetName === sheetName;
      });

      const selectedMappingEntities = selectedMapping?.entityNames ?? [];
      onSelectedSheetEntityNamesChanged(selectedMappingEntities);
      onSelectedSheetChange(sheetName);
    },
    [onSelectedSheetChange, onSelectedSheetEntityNamesChanged, sheetToEntityMappings]
  );

  const getAttributeForSelectedEntityFromHeader = React.useCallback(
    (header: HeaderToEntityAttributeMapping) => {
      return header.entityAttributes.find((attribute) => {
        return attribute.entityName === selectedEntityName;
      });
    },
    [selectedEntityName]
  );

  const selectedEntityAttributes = React.useMemo(() => {
    if (!selectedEntityName) {
      return [];
    }
    const selectedEntity = schemas[selectedEntityName];
    return selectedEntity !== undefined
      ? selectedEntity.attributes.sort((a1, a2) => {
          return a1.name.localeCompare(a2.name);
        })
      : [];
  }, [schemas, selectedEntityName]);

  const selectedSheetHeaders = React.useMemo(() => {
    if (!selectedSheet) {
      return [];
    }
    const sheetToEntityMapping = sheetToEntityMappings.find((mapping) => {
      return mapping.sheetName === selectedSheet;
    });
    return sheetToEntityMapping?.headers ?? [];
  }, [selectedSheet, sheetToEntityMappings]);

  const onHeaderSelectionChange = React.useCallback(
    (event: NonCancelableCustomEvent<TableProps.SelectionChangeDetail<HeaderToEntityAttributeMapping>>) => {
      if (!selectedSheet || !selectedEntityName) {
        return;
      }

      let updatedSchemas = { ...schemas };
      let schemaChanged = false;
      const updatedItems: HeaderToEntityAttributeMapping[] = [];

      selectedSheetHeaders.forEach((header) => {
        const isSelected =
          event.detail.selectedItems.find((selectedItem) => {
            return selectedItem.name === header.name;
          }) !== undefined;

        let updatedEntityAttributes = [...header.entityAttributes];

        if (!isSelected) {
          // if a header was deselected, remove the attribute of the currently
          // selected entity it is mapped to
          const indexOfItemToRemove = header.entityAttributes.findIndex((entityAttribute) => {
            return entityAttribute.entityName === selectedEntityName;
          });
          if (indexOfItemToRemove !== -1) {
            const removedAttribute = header.entityAttributes[indexOfItemToRemove];

            // If this was an AI-generated attribute, change its status back to SUGGESTION
            if (removedAttribute.attributeName) {
              const { updatedSchemas: newSchemas, changed } = updateAttributeStatus(
                updatedSchemas,
                selectedEntityName,
                removedAttribute.attributeName,
                "PENDING_CREATION",
                "SUGGESTION"
              );
              updatedSchemas = newSchemas;
              schemaChanged = schemaChanged || changed;
            }

            updatedEntityAttributes = header.entityAttributes.filter((_, i) => i !== indexOfItemToRemove);
          }
        }

        if (isSelected && getAttributeForSelectedEntityFromHeader(header) === undefined) {
          // if the checkbox is checked add an entry to the attributes
          // but don't set what the attribute is, this will result in
          // "Select and option" being displayed.
          updatedEntityAttributes = [
            ...updatedEntityAttributes,
            {
              entityName: selectedEntityName,
              attributeName: "",
            },
          ];
        }

        updatedItems.push({
          name: header.name,
          entityAttributes: updatedEntityAttributes,
        });
      });

      // Update schemas if any AI-generated attribute status changed
      if (schemaChanged) {
        onSchemasChanged(updatedSchemas);
      }

      const sheetToEntityMapping: SheetToEntityMapping = {
        sheetName: selectedSheet,
        headers: updatedItems,
        entityNames: selectedSheetEntityNames,
        isSelected: true,
      };

      onSheetToEntityMappingChanged(sheetToEntityMapping);
    },
    [
      selectedSheet,
      selectedEntityName,
      selectedSheetHeaders,
      schemas,
      updateAttributeStatus,
      onSchemasChanged,
      selectedSheetEntityNames,
      onSheetToEntityMappingChanged,
      getAttributeForSelectedEntityFromHeader,
    ]
  );

  const unmappedHeaders = React.useMemo(() => {
    if (!selectedSheet || !selectedEntityName) {
      return [];
    }
    const sheetToEntityMapping = sheetToEntityMappings.find((mapping) => {
      return mapping.sheetName === selectedSheet;
    });
    const headers = sheetToEntityMapping?.headers.filter((header) => header.entityAttributes.length === 0) ?? [];
    return headers.map((header) => header.name).sort();
  }, [selectedEntityName, selectedSheet, sheetToEntityMappings]);

  const unmappedHeaderControl = React.useMemo(() => {
    if (unmappedHeaders.length === 0) {
      return <></>;
    }
    return (
      <Alert type="info" header={"Headers with no matching entity attribute"}>
        If there is not an entity attribute that aligns with your supplied headers please contact your system CMF
        administrator to have these added to the relevant entity. Unmapped headers are:
        {displayTextToExpandableControl(unmappedHeaders.join(","))}
      </Alert>
    );
  }, [unmappedHeaders]);

  const generatedAttributesControl = React.useMemo(() => {
    const hasAiGeneratedAttributes = Object.values(schemas).some((schema) =>
      schema.attributes.some((attr) => attr.status === "PENDING_CREATION" && attr.suggestion?.type === "AI")
    );

    const hasFileHeaderSuggestions = Object.values(schemas).some((schema) =>
      schema.attributes.some((attr) => attr.status === "SUGGESTION" && attr.suggestion?.type === "FILE_HEADERS")
    );

    if (hasAiGeneratedAttributes || hasFileHeaderSuggestions) {
      return (
        <Alert type="info" header="Attribute Suggestions Available">
          {hasAiGeneratedAttributes && hasFileHeaderSuggestions && (
            <>
              Some entities have suggested attributes marked with 🤖 (NEW) when AI-recommended and (NEW) when derived
              from your input file headers. Any selected attributes will be automatically added to the relevant schemas
              when you create this data source.
            </>
          )}
          {hasAiGeneratedAttributes && !hasFileHeaderSuggestions && (
            <>
              Some entities have AI-recommended attributes marked with 🤖 (NEW). These recommendations were generated
              based on your input file headers. Any selected attributes will be automatically added to the relevant
              schemas when you create this data source.
            </>
          )}
          {hasFileHeaderSuggestions && !hasAiGeneratedAttributes && (
            <>
              Some entities have suggested attributes marked with (NEW). These recommendations were generated based on
              your input file headers. Any selected attributes will be automatically added to the relevant schemas when
              you create this data source.
            </>
          )}
        </Alert>
      );
    }
    return <></>;
  }, [schemas]);

  const getSelectedEntityAssignedAttributes = React.useCallback(() => {
    const headers = selectedSheetHeaders;
    const entityAttributes = headers.reduce((accumulator: string[], header: HeaderToEntityAttributeMapping) => {
      const entityAttribute = getAttributeForSelectedEntityFromHeader(header);
      if (entityAttribute) {
        accumulator.push(entityAttribute.attributeName);
      }
      return accumulator;
    }, []);
    return entityAttributes;
  }, [getAttributeForSelectedEntityFromHeader, selectedSheetHeaders]);

  const { items, collectionProps, filterProps, filteredItemsCount } = useCollection(selectedSheetHeaders, {
    filtering: {
      empty: "No headers found with provided filtering",
      noMatch: "No headers match the filters",
      filteringFunction: (item, filteringText) => {
        const filteringTextLowerCase = filteringText.toLowerCase();
        if (!item.name) {
          return false;
        }
        return item.name.toLowerCase().includes(filteringTextLowerCase);
      },
    },
    sorting: {
      defaultState: {
        sortingColumn: { sortingField: "name" },
        isDescending: false,
      },
    },
    selection: {
      keepSelection: true,
    },
  });

  const onSelectedEntityAttributeChange = (
    changeEvent: NonCancelableCustomEvent<SelectProps.ChangeDetail> | undefined,
    item: HeaderToEntityAttributeMapping
  ) => {
    const selectedEntityAttribute = changeEvent?.detail.selectedOption;
    if (!selectedEntityName || !selectedSheet) {
      return;
    }

    const index = item.entityAttributes.findIndex((entityAttribute) => {
      return entityAttribute.entityName === selectedEntityName;
    });

    let updatedSchemas = { ...schemas };
    let schemaChanged = false;
    let updatedEntityAttributes: typeof item.entityAttributes;

    if (!selectedEntityAttribute || !selectedEntityAttribute.value) {
      // Clear the selection by removing the entity attribute
      if (index !== -1) {
        const removedAttribute = item.entityAttributes[index];
        updatedEntityAttributes = item.entityAttributes.filter((_, i) => i !== index);
        // If this was an AI-generated attribute, change its status back to SUGGESTION
        const { updatedSchemas: newSchemas, changed } = updateAttributeStatus(
          updatedSchemas,
          selectedEntityName,
          removedAttribute.attributeName,
          "PENDING_CREATION",
          "SUGGESTION"
        );
        updatedSchemas = newSchemas;
        schemaChanged = schemaChanged || changed;
      } else {
        updatedEntityAttributes = [...item.entityAttributes];
      }
    } else {
      // Set or update the selection
      const newAttribute = {
        entityName: selectedEntityName,
        attributeName: selectedEntityAttribute.value,
      };

      if (index === -1) {
        updatedEntityAttributes = [...item.entityAttributes, newAttribute];
      } else {
        // If the old attribute is a AI-generated, change its status to SUGGESTION
        const oldItem = item.entityAttributes[index];
        const { updatedSchemas: newSchemas, changed } = updateAttributeStatus(
          updatedSchemas,
          selectedEntityName,
          oldItem.attributeName,
          "PENDING_CREATION",
          "SUGGESTION"
        );
        updatedSchemas = newSchemas;
        schemaChanged = schemaChanged || changed;
        updatedEntityAttributes = item.entityAttributes.map((attr, i) => (i === index ? newAttribute : attr));
      }

      // Check if this is a file header suggestion that doesn't exist in the schema yet
      const attributeExists = selectedEntityAttributes.some((attr) => attr.name === selectedEntityAttribute.value);

      if (!attributeExists) {
        // This is a new file header suggestion - add it to the schema
        const currentSchema = updatedSchemas[selectedEntityName] || schemas[selectedEntityName];
        if (currentSchema) {
          const newAttribute: AttributeWithCreationStatus = {
            name: selectedEntityAttribute.value,
            description: `Attribute derived from file header: ${item.name}`,
            type: "string",
            status: "PENDING_CREATION",
            system: false,
            long_desc: "Attribute suggested from file header name",
            suggestion: {
              type: "FILE_HEADERS",
              sourceHeader: item.name || "",
            },
          };

          updatedSchemas[selectedEntityName] = {
            ...currentSchema,
            attributes: [...currentSchema.attributes, newAttribute],
          };
          schemaChanged = true;
        }
      } else {
        // If this is an AI-generated attribute, change its status to PENDING
        const { updatedSchemas: finalSchemas, changed: finalChanged } = updateAttributeStatus(
          updatedSchemas,
          selectedEntityName,
          selectedEntityAttribute.value,
          "SUGGESTION",
          "PENDING_CREATION"
        );
        updatedSchemas = finalSchemas;
        schemaChanged = schemaChanged || finalChanged;
      }
    }

    // Update schemas if any AI-generated attribute status changed
    if (schemaChanged) {
      onSchemasChanged(updatedSchemas);
    }

    // Create a new item object with updated entityAttributes
    const updatedItem = {
      ...item,
      entityAttributes: updatedEntityAttributes,
    };

    // Update the headers array with the new item
    const updatedHeaders = selectedSheetHeaders.map((header) => (header.name === item.name ? updatedItem : header));

    const sheetToEntityMapping: SheetToEntityMapping = {
      sheetName: selectedSheet,
      headers: updatedHeaders,
      entityNames: selectedSheetEntityNames,
      isSelected: true,
    };

    onSheetToEntityMappingChanged(sheetToEntityMapping);
  };

  const onSelectAllFileHeaders = React.useCallback(() => {
    if (!selectedSheet || !selectedEntityName) {
      return;
    }

    // Find headers that have corresponding FILE_HEADERS suggestions available
    // AND are not already highlighted (don't have an entity attribute mapping)
    const headersWithFileHeaderSuggestions = selectedSheetHeaders.filter((header) => {
      if (!header.name) return false;

      // Check if this header is already highlighted (has an entity attribute mapping)
      const isAlreadyHighlighted = getAttributeForSelectedEntityFromHeader(header) !== undefined;
      if (isAlreadyHighlighted) return false;

      // Create attribute name by replacing spaces with underscores (same logic as initialization)
      const suggestedAttributeName = header.name.replace(/\s+/g, "_");

      // Check if this attribute exists in the schema with FILE_HEADERS suggestion type
      return selectedEntityAttributes.some(
        (attr) =>
          attr.name === suggestedAttributeName &&
          (attr.status === "PENDING_CREATION" || attr.status === "SUGGESTION") &&
          attr.suggestion?.type === "FILE_HEADERS" &&
          attr.suggestion?.sourceHeader === header.name
      );
    });

    if (headersWithFileHeaderSuggestions.length === 0) {
      addNotification({
        type: "info",
        content: "No new suggestions available for the current entity.",
        dismissible: true,
      });
      return;
    }

    let updatedSchemas = { ...schemas };
    let schemaChanged = false;

    // Create updated headers with both selection and attribute assignment
    const updatedHeaders = selectedSheetHeaders.map((header) => {
      const isFileHeaderSuggestion = headersWithFileHeaderSuggestions.some((h) => h.name === header.name);

      if (isFileHeaderSuggestion && header.name) {
        // Create attribute name by replacing spaces with underscores
        const suggestedAttributeName = header.name.replace(/\s+/g, "_");

        // Find the FILE_HEADERS suggestion attribute for this header
        const fileHeaderAttribute = selectedEntityAttributes.find(
          (attr) =>
            attr.name === suggestedAttributeName &&
            (attr.status === "PENDING_CREATION" || attr.status === "SUGGESTION") &&
            attr.suggestion?.type === "FILE_HEADERS" &&
            attr.suggestion?.sourceHeader === header.name
        );

        if (fileHeaderAttribute) {
          // Update attribute status to PENDING_CREATION if it was SUGGESTION
          if (fileHeaderAttribute.status === "SUGGESTION") {
            const { updatedSchemas: newSchemas, changed } = updateAttributeStatus(
              updatedSchemas,
              selectedEntityName,
              fileHeaderAttribute.name,
              "SUGGESTION",
              "PENDING_CREATION"
            );
            updatedSchemas = newSchemas;
            schemaChanged = schemaChanged || changed;
          }

          // Check if this header already has an entity attribute for the selected entity
          const existingAttributeIndex = header.entityAttributes.findIndex(
            (attr) => attr.entityName === selectedEntityName
          );

          const updatedEntityAttributes = [...header.entityAttributes];

          if (existingAttributeIndex !== -1) {
            // Update existing entity attribute
            updatedEntityAttributes[existingAttributeIndex] = {
              entityName: selectedEntityName,
              attributeName: fileHeaderAttribute.name,
            };
          } else {
            // Add new entity attribute
            updatedEntityAttributes.push({
              entityName: selectedEntityName,
              attributeName: fileHeaderAttribute.name,
            });
          }

          return {
            ...header,
            entityAttributes: updatedEntityAttributes,
          };
        }
      }

      return header;
    });

    // Update schemas if any attribute status changed
    if (schemaChanged) {
      onSchemasChanged(updatedSchemas);
    }

    // Update the sheet to entity mapping with the new headers
    const sheetToEntityMapping: SheetToEntityMapping = {
      sheetName: selectedSheet,
      headers: updatedHeaders,
      entityNames: selectedSheetEntityNames,
      isSelected: true,
    };

    onSheetToEntityMappingChanged(sheetToEntityMapping);

    addNotification({
      type: "success",
      content: `Selected and assigned ${headersWithFileHeaderSuggestions.length} header(s) to their corresponding attribute(s).`,
      dismissible: true,
    });
  }, [
    selectedSheet,
    selectedEntityName,
    selectedSheetHeaders,
    selectedEntityAttributes,
    selectedSheetEntityNames,
    schemas,
    updateAttributeStatus,
    onSchemasChanged,
    onSheetToEntityMappingChanged,
    addNotification,
    getAttributeForSelectedEntityFromHeader,
  ]);

  const onAutoMap = React.useCallback(async () => {
    setIsRequestingHeaders(true);

    const sheetToEntityMapping = sheetToEntityMappings.find((m) => m.sheetName === selectedSheet);
    if (!sheetToEntityMapping) {
      setFlashBarErrorMessage(headerMappingErrorContent(`No sheet to entity mapping for sheet '${selectedSheet}'`));
      setIsRequestingHeaders(false);
      return;
    }

    try {
      const client = await getClient();
      const result = await makeRequestForHeaderMapping(sheetToEntityMapping, schemas, client);

      // Build a set of mapped entity attributes as `entityName|attributeName`
      const mappedAttributeSet = new Set<string>(
        sheetToEntityMapping.headers.flatMap((header) =>
          header.entityAttributes.map(
            (entityAttribute) => `${entityAttribute.entityName}|${entityAttribute.attributeName}`
          )
        )
      );
      // Build a set of mapped headers as `entityName|headerName`
      const mappedHeaderSet = new Set<string>(
        sheetToEntityMapping.headers.flatMap((header) =>
          header.entityAttributes.map((entityAttribute) => `${entityAttribute.entityName}|${header.name}`)
        )
      );
      const mappedEntities = new Set<string>();
      const recommendationsAdded = new Set<string>();
      const updatedSchemas = { ...schemas };
      let schemasChanged = false;

      const updatedHeaders = [...sheetToEntityMapping.headers];

      for (const [key, { mappings, recommendations }] of Object.entries(result)) {
        if (!sheetToEntityMapping.entityNames.includes(key)) {
          console.warn(`Ignored auto mapping result for non-existing entity ${key}`);
          continue;
        }
        if (!Array.isArray(mappings)) {
          console.warn(`Ignored invalid auto mapping result for ${key}`, mappings);
          continue;
        }

        // Process mappings
        for (const mapping of mappings) {
          const sourceHeaderIndex = updatedHeaders.findIndex((header) => header.name === mapping.source_header);
          if (sourceHeaderIndex === -1) {
            console.warn(`Ignored auto mapping result for non-existing header ${mapping.source_header}`);
            continue;
          }
          const sourceHeader = updatedHeaders[sourceHeaderIndex];
          const headerMappingKey = `${key}|${sourceHeader.name}`;
          const attributeMappingKey = `${key}|${mapping.target_header}`;
          if (mappedHeaderSet.has(headerMappingKey)) {
            console.warn(`Ignored auto mapping result for already mapped header ${headerMappingKey}`);
            continue;
          }
          if (mappedAttributeSet.has(attributeMappingKey)) {
            console.warn(`Ignored auto mapping result for already mapped attribute ${attributeMappingKey}`);
            continue;
          }
          // Create a new header object with updated entityAttributes
          const updatedHeader = {
            ...sourceHeader,
            entityAttributes: [
              ...sourceHeader.entityAttributes,
              {
                entityName: key,
                attributeName: mapping.target_header,
              },
            ],
          };

          updatedHeaders[sourceHeaderIndex] = updatedHeader;
          mappedAttributeSet.add(attributeMappingKey);
          mappedHeaderSet.add(headerMappingKey);
          mappedEntities.add(schemas[key]?.friendly_name ?? capitalize(key));
        }

        // Process recommendations and add them to schema with SUGGESTION status
        for (const recommendation of recommendations) {
          // Use the potentially already-updated schema, not the original
          const currentSchema = updatedSchemas[key] || schemas[key];
          if (currentSchema) {
            // Check if the recommended attribute already exists
            const existingAttribute = currentSchema.attributes.find(
              (attr) => attr.name === recommendation.recommended_header
            );

            // Find any FILE_HEADERS suggestion based on the same source header
            const fileHeaderAttributeForSameSource = currentSchema.attributes.find(
              (attr) =>
                attr.suggestion?.type === "FILE_HEADERS" &&
                attr.suggestion?.sourceHeader === recommendation.source_header
            );

            const newAttribute: AttributeWithCreationStatus = {
              name: recommendation.recommended_header,
              description: recommendation.recommended_title,
              type: "string",
              status: "PENDING_CREATION",
              system: false,
              long_desc: "Attribute auto-generated during data source creation",
              suggestion: {
                type: "AI",
                sourceHeader: recommendation.source_header,
              },
            };

            if (fileHeaderAttributeForSameSource) {
              // Replace the FILE_HEADERS suggestion with the AI recommendation
              const updatedAttributes = currentSchema.attributes
                .filter((attr) => attr !== fileHeaderAttributeForSameSource)
                .concat(newAttribute);

              updatedSchemas[key] = {
                ...currentSchema,
                attributes: updatedAttributes,
              };

              recommendationsAdded.add(`${key}:${recommendation.recommended_header}`);
              schemasChanged = true;
            } else if (!existingAttribute) {
              // Add new AI recommendation if no existing attribute with the same name
              updatedSchemas[key] = {
                ...currentSchema,
                attributes: [...currentSchema.attributes, newAttribute],
              };

              recommendationsAdded.add(`${key}:${recommendation.recommended_header}`);
              schemasChanged = true;
            }
          }
        }

        // Process recommendations into mappings
        for (const recommendation of recommendations) {
          const sourceHeaderIndex = updatedHeaders.findIndex((header) => header.name === recommendation.source_header);
          if (sourceHeaderIndex === -1) {
            console.warn(`Ignored auto mapping recommendation for non-existing header ${recommendation.source_header}`);
            continue;
          }
          const sourceHeader = updatedHeaders[sourceHeaderIndex];
          const headerMappingKey = `${key}|${sourceHeader.name}`;
          const attributeMappingKey = `${key}|${recommendation.recommended_header}`;
          if (mappedHeaderSet.has(headerMappingKey)) {
            console.warn(`Ignored auto mapping recommendation for already mapped header ${headerMappingKey}`);
            continue;
          }
          if (mappedAttributeSet.has(attributeMappingKey)) {
            console.warn(`Ignored auto mapping recommendation for already mapped attribute ${attributeMappingKey}`);
            continue;
          }
          // Create a new header object with updated entityAttributes
          const updatedHeader = {
            ...sourceHeader,
            entityAttributes: [
              ...sourceHeader.entityAttributes,
              {
                entityName: key,
                attributeName: recommendation.recommended_header,
              },
            ],
          };

          updatedHeaders[sourceHeaderIndex] = updatedHeader;
          mappedAttributeSet.add(attributeMappingKey);
          mappedHeaderSet.add(headerMappingKey);
          mappedEntities.add(schemas[key]?.friendly_name ?? capitalize(key));
        }
      }

      // Apply schema changes once after processing all entities
      if (schemasChanged) {
        onSchemasChanged(updatedSchemas);
      }

      if (mappedEntities.size) {
        // Create a new sheetToEntityMapping with updated headers
        const updatedSheetToEntityMapping: SheetToEntityMapping = {
          ...sheetToEntityMapping,
          headers: updatedHeaders,
        };
        onSheetToEntityMappingChanged(updatedSheetToEntityMapping);
        // Auto select the first one if entity not selected
        if (!selectedEntityName) onSelectedEntityNameChanged(Object.keys(result)[0]);

        let successMessage = `Auto mapped headers to ${mappedEntities.values().toArray().join(", ")}.`;
        if (recommendationsAdded.size > 0) {
          successMessage += ` Added ${recommendationsAdded.size} AI recommendations. `;
        }

        addNotification({
          type: "success",
          content: successMessage,
          dismissible: true,
        });
      } else {
        addNotification({
          type: "info",
          content: "Auto mapping cannot map any headers.",
          dismissible: true,
        });
      }
    } catch (error) {
      const message = (error as Error).message;
      setFlashBarErrorMessage(headerMappingErrorContent(message));
    } finally {
      setIsRequestingHeaders(false);
    }
  }, [
    sheetToEntityMappings,
    selectedSheet,
    setFlashBarErrorMessage,
    getClient,
    schemas,
    onSheetToEntityMappingChanged,
    selectedEntityName,
    onSelectedEntityNameChanged,
    addNotification,
    onSchemasChanged,
  ]);

  const entityOptions: SelectProps.Option[] = React.useMemo(() => {
    const baseOptions = entitySelectOptions(schemas, selectedSheetEntityNames);
    return baseOptions.map((option) => ({
      ...option,
      label: schemas[option.value]?.attributes.some(
        (attr) => (attr.status === "PENDING_CREATION" || attr.status === "SUGGESTION") && attr.suggestion?.type === "AI"
      )
        ? `${option.label} 🤖`
        : option.label,
    }));
  }, [schemas, selectedSheetEntityNames]);

  const getEntityAttributeOptionsForHeader = React.useCallback(
    (currentHeader: HeaderToEntityAttributeMapping) => {
      const currentlySelectedAttribute = getAttributeForSelectedEntityFromHeader(currentHeader);
      const assignedAttributes = getSelectedEntityAssignedAttributes();

      return [
        { label: "-- Clear selection --", value: "" },
        // ...fileHeaderSuggestions,
        ...selectedEntityAttributes
          .filter((attribute) => {
            // Only show suggestions that match the current header's source
            const isGeneratedAttribute = attribute.status === "PENDING_CREATION" || attribute.status === "SUGGESTION";
            if (isGeneratedAttribute && attribute.suggestion) {
              // For AI suggestions, only show if the source_header matches the current header
              if (attribute.suggestion.type === "AI") {
                return attribute.suggestion.sourceHeader === currentHeader.name;
              }
              // For FILE_HEADERS suggestions, only show if the source_header matches the current header
              if (attribute.suggestion.type === "FILE_HEADERS") {
                return attribute.suggestion.sourceHeader === currentHeader.name;
              }
            }
            // Always show non-generated attributes (existing schema attributes)
            return !isGeneratedAttribute;
          })
          .map((attribute) => {
            const label = getLabelForEntityAttribute(attribute, selectedEntityName);
            const isAssignedToOtherHeader =
              assignedAttributes.includes(attribute.name) &&
              currentlySelectedAttribute?.attributeName !== attribute.name;

            const isGeneratedAttribute = attribute.status === "PENDING_CREATION" || attribute.status === "SUGGESTION";
            const isAiGeneratedAttribute = isGeneratedAttribute && attribute.suggestion?.type === "AI";
            const isFileHeaderGeneratedAttribute =
              isGeneratedAttribute && attribute.suggestion?.type === "FILE_HEADERS";

            let description: string | undefined;
            if (isAssignedToOtherHeader) {
              description = "Assigned to another header";
            } else if (attribute.description) {
              description = attribute.description;
            }

            let optionLabel = label;
            if (isAiGeneratedAttribute) {
              optionLabel += " 🤖 (NEW)";
            } else if (isFileHeaderGeneratedAttribute) {
              optionLabel += " (NEW)";
            }

            return {
              label: optionLabel,
              value: attribute.name,
              disabled: isAssignedToOtherHeader,
              description,
            };
          }),
      ];
    },
    [
      getSelectedEntityAssignedAttributes,
      selectedEntityAttributes,
      selectedEntityName,
      getAttributeForSelectedEntityFromHeader,
    ]
  );

  const getEntityAttributeSelectedOption = React.useCallback(
    (header: HeaderToEntityAttributeMapping) => {
      const attribute = getAttributeForSelectedEntityFromHeader(header);
      const options = getEntityAttributeOptionsForHeader(header);
      return options.find((o) => o.value === attribute?.attributeName) ?? null;
    },
    [getEntityAttributeOptionsForHeader, getAttributeForSelectedEntityFromHeader]
  );

  return (
    <SpaceBetween size="m">
      <Container header={<Header variant="h2">Sheet and entity to map</Header>}>
        <SpaceBetween size="s">
          {unmappedEntityIdentifiers.size > 0 && unmappedEntitiesAlert(unmappedEntityIdentifiers, schemas)}
          <ColumnLayout columns={2}>
            <Select
              placeholder="Choose a sheet"
              selectedOption={selectedSheet ? { label: selectedSheet, value: selectedSheet } : null}
              onChange={(event) => onSelectedSheetChangedInternal(event.detail.selectedOption.value)}
              options={sheetToEntityMappings
                .filter((mapping) => {
                  return mapping.isSelected;
                })
                .map((mapping) => {
                  const { sheetName } = mapping;
                  return { label: sheetName, value: sheetName };
                })}
            />
            {selectedSheet && environment.GENAI_SUPPORTED === "true" && (
              <Box textAlign="right">
                <Button iconName="gen-ai" loadingText="Thinking..." onClick={onAutoMap} loading={isRequestingHeaders}>
                  Auto map headers
                </Button>
              </Box>
            )}
          </ColumnLayout>
        </SpaceBetween>
      </Container>
      {selectedSheet && (
        <SpaceBetween size="m">
          <Table
            isItemDisabled={() => {
              return isRequestingHeaders;
            }}
            header={
              <ColumnLayout columns={2}>
                <Header variant="h2">Headers</Header>
                {selectedEntityName && (
                  <Box textAlign="right">
                    <ButtonDropdown
                      items={[
                        {
                          id: "select-all-file-header-suggestions",
                          text: "Select all file header suggestions",
                          iconName: "suggestions",
                        },
                      ]}
                      variant="icon"
                      ariaLabel="Actions menu"
                      onItemClick={({ detail }) => {
                        if (detail.id === "select-all-file-header-suggestions") {
                          onSelectAllFileHeaders();
                        }
                      }}
                    />
                  </Box>
                )}
              </ColumnLayout>
            }
            {...collectionProps}
            items={items}
            selectionType="multi"
            trackBy="name"
            selectedItems={selectedSheetHeaders.filter((header) => {
              return getAttributeForSelectedEntityFromHeader(header) !== undefined;
            })}
            onSelectionChange={onHeaderSelectionChange}
            filter={
              <ColumnLayout columns={2}>
                <TextFilter
                  {...filterProps}
                  filteringPlaceholder="Find header"
                  countText={`${filteredItemsCount} ${filteredItemsCount === 1 ? "match" : "matches"}`}
                />
                <Select
                  placeholder="Choose an entity"
                  onChange={(event) => onSelectedEntityNameChanged(event.detail.selectedOption.value)}
                  options={entityOptions}
                  selectedOption={entityOptions.find((o) => o.value === selectedEntityName) ?? null}
                />
              </ColumnLayout>
            }
            columnDefinitions={[
              {
                id: "name",
                header: "File header",
                sortingField: "name",
                cell: (item) => {
                  const isDisabled = getAttributeForSelectedEntityFromHeader(item) === undefined;
                  const fontWeight: BoxProps.FontWeight = isDisabled ? "light" : "normal";
                  return <Box fontWeight={fontWeight}>{item.name}</Box>;
                },
              },
              {
                header: "Entity attribute",
                cell: (item) => {
                  if (selectedEntityName) {
                    const isInvalid =
                      item.entityAttributes.find((attribute) => {
                        return attribute.entityName === selectedEntityName && attribute.attributeName === "";
                      }) !== undefined;
                    return (
                      <Select
                        disabled={isRequestingHeaders}
                        expandToViewport
                        invalid={isInvalid}
                        placeholder="Choose an option"
                        selectedOption={getEntityAttributeSelectedOption(item)}
                        onChange={(changeEvent) => {
                          onSelectedEntityAttributeChange(changeEvent, item);
                        }}
                        options={getEntityAttributeOptionsForHeader(item)}
                      />
                    );
                  } else {
                    return <Box>-</Box>;
                  }
                },
              },
            ]}
          />
          {unmappedHeaderControl}
          {generatedAttributesControl}
        </SpaceBetween>
      )}
    </SpaceBetween>
  );
};

export default DSWManageHeaderMappings;
