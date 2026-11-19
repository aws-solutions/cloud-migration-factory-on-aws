import UserApiClient from "../../api_clients/userApiClient";
import { Attribute, EntitySchema } from "../../models";
import { DataSource, SheetAndMappedHeaders } from "../../models/DataSource";
import { capitalize } from "../../resources/main";
import { parsePUTResponseErrors, UNEXPECTED_ERROR } from "../../resources/recordFunctions";
import { isCustomSchema } from "../../utils/schema-utils";
import { SheetToEntityMapping } from "./data-source-types";

const userApiClient = new UserApiClient();

export const entitySelectOptions = (
  mappableSchemas: Readonly<Record<string, EntitySchema>>,
  selectedEntities?: string[]
) =>
  Object.entries(mappableSchemas)
    .map(([schemaName, schema]) => ({
      // Use key of schemas instead of schema.schema_name, i.e. 'application' instead of 'app'
      // As 'application' is used as the value of the option for the entity select dropdown
      // in data source mapping
      value: schemaName,
      label: schema.friendly_name ?? capitalize(schema.schema_name),
      tags: isCustomSchema(schema) ? ["Custom"] : [],
    }))
    .filter((option) => (selectedEntities ? selectedEntities?.includes(option.value) : true))
    .sort((a, b) => a.label.localeCompare(b.label));

export const getLabelForEntityAttribute = (attribute: Attribute, entity?: string) => {
  const entityName = entity === "application" ? "app" : entity;
  // If relationship attribute
  if (attribute.rel_display_attribute) {
    // Return the related display attribute if not multi-select, otherwise return plural
    return attribute.listMultiSelect ? `${attribute.rel_display_attribute}s` : attribute.rel_display_attribute;
  } else {
    // Append key symbol for entity name attribute
    return attribute.name === `${entityName}_name` ? `${attribute.name} 🔑` : attribute.name;
  }
};

export const headerMappingsToSave = (sheetToEntityMappings: SheetToEntityMapping[]) => {
  const sheetsWithMappings = sheetToEntityMappings.filter((mapping) => {
    return mapping.isSelected;
  });

  return sheetsWithMappings.map((mapping) => {
    const { sheetName, headers } = mapping;
    const headerDataToSave = headers
      .filter((header) => {
        return header.entityAttributes.length > 0;
      })
      .map((header) => {
        const { name, entityAttributes } = header;
        return {
          name,
          entityAttributes,
        };
      });
    return {
      sheetName,
      headers: headerDataToSave,
    };
  });
};

export const reconstituteHeaderMappings = (headerMappings: SheetAndMappedHeaders[]) => {
  return headerMappings.map((mapping) => {
    const entityNames = new Set<string>();
    mapping.headers.forEach((header) => {
      header.entityAttributes.forEach((entityAttribute) => {
        entityNames.add(entityAttribute.entityName);
      });
    });
    return {
      isSelected: true,
      entityNames: entityNames.keys().toArray(),
      ...mapping,
    };
  });
};

export const createDataSource = async (entity: DataSource) => {
  try {
    const response = await userApiClient.createDataSource(entity);
    const { newItems, errors } = response;
    if (errors) {
      const message = parsePUTResponseErrors(errors).join(",") || UNEXPECTED_ERROR;
      return {
        error: message,
      };
    }
    if (newItems && newItems.length === 1 && newItems[0].data_source_id) {
      return {
        dataSourceId: newItems[0].data_source_id,
      };
    } else {
      return {
        error: "Returned payload had invalid data",
      };
    }
  } catch (e) {
    return {
      error: e instanceof Error ? e.message : UNEXPECTED_ERROR,
    };
  }
};

export const updateDataSource = async (entity: DataSource) => {
  try {
    const { data_source_id } = entity;
    const response = await userApiClient.updateDataSource(entity);
    const { ResponseMetadata, errors } = response;
    if (errors) {
      const message = parsePUTResponseErrors(errors).join(",") || UNEXPECTED_ERROR;
      return {
        error: message,
      };
    }
    if (!ResponseMetadata) {
      return {
        error: UNEXPECTED_ERROR,
      };
    }
    if (ResponseMetadata.HTTPStatusCode === 200) {
      return {
        dataSourceId: data_source_id,
      };
    } else {
      return {
        error: `Request failed with status code '${ResponseMetadata.HTTPStatusCode}'`,
      };
    }
  } catch (e) {
    return {
      error: e instanceof Error ? e.message : UNEXPECTED_ERROR,
    };
  }
};

/**
 * Sanitizes an EntitySchema by extracting only essential properties of schema itself and the attributes
 * Apparently some attribute metadata (e.g. rel_entity, validation_regex) will confuse the LLM
 * @param schema - The EntitySchema to sanitize
 * @param predicate - Optional filter function for attributes. Defaults to including all attributes.
 * @returns A sanitized schema object containing only friendly_name, description, help_content, and filtered attributes
 */
export const sanitizeSchema = (
  schema: EntitySchema,
  predicate: (value: Attribute, index: number, array: Attribute[]) => boolean = () => true
) => {
  const { friendly_name, description, help_content } = schema;
  return {
    friendly_name,
    description,
    help_content,
    attributes: schema.attributes
      .filter(predicate)
      .map(({ type, name, description, help_content, listvalue, long_desc }) => ({
        type,
        name,
        description,
        help_content,
        listvalue,
        long_desc,
      })),
  };
};
