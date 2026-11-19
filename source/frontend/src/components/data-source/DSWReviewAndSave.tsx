import React from "react";
import {
  Alert,
  Box,
  Button,
  ColumnLayout,
  Container,
  FormField,
  Header,
  Popover,
  Select,
  SpaceBetween,
  Table,
} from "@cloudscape-design/components";
import { SheetToEntityMapping } from "./data-source-types";
import { getLabelForEntityAttribute } from "./data-source-utils";
import { EntityAttribute } from "../../models";
import { capitalize } from "../../resources/main";
import { EntitySchemaWithStatus } from "./DataSourceWizard";

export interface DSWReviewAndSaveProps {
  readonly schemas: Record<string, EntitySchemaWithStatus>;
  readonly sheetToEntityMappings: SheetToEntityMapping[];
  readonly name: string;
  readonly description: string;
}

/**
 * Data source import wizard step three control.
 */
const DSWReviewAndSave = (props: DSWReviewAndSaveProps) => {
  const { sheetToEntityMappings, name, description, schemas } = props;

  const [selectedSheetName, setSelectedSheetName] = React.useState<string | undefined>();

  const generatedAttributesControl = React.useMemo(() => {
    const hasAiGeneratedAttributes = Object.values(schemas).some((schema) =>
      schema.attributes.some((attr) => attr.status === "PENDING_CREATION" && attr.suggestion?.type === "AI")
    );
    const hasFileHeaderGeneratedAttributes = Object.values(schemas).some((schema) =>
      schema.attributes.some((attr) => attr.status === "PENDING_CREATION" && attr.suggestion?.type === "FILE_HEADERS")
    );

    if (hasAiGeneratedAttributes && hasFileHeaderGeneratedAttributes) {
      return (
        <Alert type="info" header="AI Recommendations Added">
          Some of the mapped attributes have been recommended based upon your input file headers and AI. These
          attributes do not currently exist in the schema. They will be automatically added to the relevant schemas if
          you proceed past this step.
        </Alert>
      );
    } else if (hasAiGeneratedAttributes) {
      return (
        <Alert type="info" header="AI Recommendations Added">
          Some of the mapped attributes have been recommended by AI based upon your input file headers. These attributes
          do not currently exist in the schema. They will be automatically added to the relevant schemas if you proceed
          past this step.
        </Alert>
      );
    } else if (hasFileHeaderGeneratedAttributes) {
      return (
        <Alert type="info" header="Recommendations Added">
          Some of the mapped attributes have been recommended based upon your input file headers. These attributes do
          not currently exist in the schema. They will be automatically added to the relevant schemas if you proceed
          past this step.
        </Alert>
      );
    }
    return <></>;
  }, [schemas]);

  const selectedSheets = React.useMemo(() => {
    return sheetToEntityMappings
      .filter((sheetToEntityMapping) => {
        return sheetToEntityMapping.isSelected;
      })
      .map((sheetToEntityMapping) => {
        const mappedHeaders = sheetToEntityMapping.headers.filter((header) => {
          return header.entityAttributes.length > 0;
        });
        const schemas = new Set<string>();
        mappedHeaders.forEach((header) => {
          header.entityAttributes.forEach((entityAttribute) => {
            schemas.add(entityAttribute.entityName);
          });
        });
        return {
          sheetName: sheetToEntityMapping.sheetName,
          mappedHeaders,
          schemas: [...schemas].sort(),
        };
      });
  }, [sheetToEntityMappings]);

  React.useEffect(() => {
    if (selectedSheets.length > 0 && !selectedSheetName) {
      setSelectedSheetName(selectedSheets[0].sheetName);
    }
  }, [selectedSheets, selectedSheetName]);

  const selectedSheetHeaders = React.useMemo(() => {
    return (
      selectedSheets
        .find((sheet) => {
          return sheet.sheetName === selectedSheetName;
        })
        ?.mappedHeaders.sort((h1, h2) => {
          if (h1.name === undefined && h2.name === undefined) return 0;
          if (h1.name === undefined) return 1;
          if (h2.name === undefined) return -1;
          return h1.name.localeCompare(h2.name);
        }) ?? []
    );
  }, [selectedSheetName, selectedSheets]);

  const onSelectedSheetChanged = (sheetName?: string) => {
    setSelectedSheetName(sheetName);
  };

  const columns = React.useMemo(() => {
    const selectedSheet = selectedSheets.find((sheet) => sheet.sheetName === selectedSheetName);

    if (!selectedSheet) {
      return [];
    }

    return selectedSheet.schemas.map((schemaName) => {
      const entitySchema = props.schemas[schemaName];
      return {
        id: schemaName,
        header: entitySchema?.friendly_name ?? capitalize(schemaName),
        cell: (item: { name: string; entityAttributes: EntityAttribute[] }) => {
          const mappedEntityAttribute = item.entityAttributes.find(
            (entityAttribute) => entityAttribute.entityName === schemaName
          );
          const schemaAttribute = entitySchema?.attributes.find(
            (attr) => attr.name === mappedEntityAttribute?.attributeName
          );

          if (schemaAttribute?.status === "PENDING_CREATION" && schemaAttribute.suggestion?.type === "AI") {
            return (
              <Box>
                {getLabelForEntityAttribute(schemaAttribute, mappedEntityAttribute?.entityName)}
                <Popover
                  size="small"
                  position="top"
                  triggerType="custom"
                  dismissButton={true}
                  content={
                    <Box>
                      <SpaceBetween size="xs">
                        <Box variant="strong">AI-Generated Attribute</Box>
                        <Box>
                          This is an auto-generated attribute that was created by AI recommendations. Please review and
                          validate this attribute before proceeding.
                        </Box>
                      </SpaceBetween>
                    </Box>
                  }
                >
                  <Button iconName="status-warning" variant="icon"></Button>
                </Popover>
              </Box>
            );
          } else if (
            schemaAttribute?.status === "PENDING_CREATION" &&
            schemaAttribute.suggestion?.type === "FILE_HEADERS"
          ) {
            return (
              <Box>
                {getLabelForEntityAttribute(schemaAttribute, mappedEntityAttribute?.entityName)}
                <Popover
                  size="small"
                  position="top"
                  triggerType="custom"
                  dismissButton={true}
                  content={
                    <Box>
                      <SpaceBetween size="xs">
                        <Box variant="strong">Generated Attribute</Box>
                        <Box>
                          This is an auto-generated attribute that was created based upon your file headers. Please
                          review and validate this attribute before proceeding.
                        </Box>
                      </SpaceBetween>
                    </Box>
                  }
                >
                  <Button iconName="status-warning" variant="icon"></Button>
                </Popover>
              </Box>
            );
          } else if (schemaAttribute) {
            return <Box>{getLabelForEntityAttribute(schemaAttribute, mappedEntityAttribute?.entityName)}</Box>;
          } else {
            return null;
          }
        },
      };
    });
  }, [props.schemas, selectedSheetName, selectedSheets]);

  return (
    <SpaceBetween size="m">
      <Container header={<Header variant="h2">General settings</Header>}>
        <FormField label={"Name"}>{name}</FormField>
        {description && <FormField label={"Description"}>{description}</FormField>}
      </Container>
      <Container header={<Header variant="h2">Sheet to review</Header>}>
        <Select
          placeholder="Choose a sheet"
          selectedOption={selectedSheetName ? { label: selectedSheetName, value: selectedSheetName } : null}
          onChange={(event) => onSelectedSheetChanged(event.detail.selectedOption.value)}
          options={selectedSheets.map((mapping) => {
            const { sheetName } = mapping;
            return { label: sheetName, value: sheetName };
          })}
        />
      </Container>
      <Table
        header={
          <ColumnLayout columns={2}>
            <Header variant="h2">Headers</Header>
          </ColumnLayout>
        }
        items={selectedSheetHeaders}
        columnDefinitions={[
          {
            id: "name",
            header: "File header",
            sortingField: "name",
            cell: (item) => {
              return <Box>{item.name}</Box>;
            },
          },
          ...columns,
        ]}
      />
      {generatedAttributesControl}
    </SpaceBetween>
  );
};

export default DSWReviewAndSave;
