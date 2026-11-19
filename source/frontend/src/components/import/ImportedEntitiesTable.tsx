import React from "react";
import {
  Box,
  Header,
  Pagination,
  SpaceBetween,
  Table,
  TableProps,
  TextFilter,
  Button,
  Badge,
} from "@cloudscape-design/components";
import { DeduplicatedEntity } from "../data-validation";
import { Attribute } from "../../models/EntitySchema";
import { useCollection } from "@cloudscape-design/collection-hooks";
import "./ImportedEntitiesTable.css";

export interface ImportedEntitiesTableProps {
  readonly entitiesToCreate: DeduplicatedEntity[];
  readonly entitiesToUpdate: DeduplicatedEntity[];
  readonly entityFilter?: string;
}

type TableItem = {
  id: string;
  uniqueKey: string;
  data: Record<string, unknown>;
  operation: "create" | "update";
  entityType: string;
};

interface TagObject {
  key: string;
  value: string;
}

/**
 * Component that displays imported entities in a table.
 */
const ImportedEntitiesTable: React.FC<ImportedEntitiesTableProps> = ({
  entitiesToCreate,
  entitiesToUpdate,
  entityFilter,
}) => {
  // Combine entities from both create and update operations with operation type
  const combinedEntities = React.useMemo(() => {
    const combined: Array<DeduplicatedEntity & { operation: "create" | "update" }> = [];

    // Add create entities with operation type
    entitiesToCreate.forEach((entity) => {
      combined.push({ ...entity, operation: "create" });
    });

    // Add update entities with operation type
    entitiesToUpdate.forEach((entity) => {
      combined.push({ ...entity, operation: "update" });
    });

    return combined;
  }, [entitiesToCreate, entitiesToUpdate]);

  // Group entities by entity name for filtering
  const groupedByType = React.useMemo(() => {
    const grouped: Record<string, Array<DeduplicatedEntity & { operation: "create" | "update" }>> = {};

    combinedEntities.forEach((entity) => {
      if (!grouped[entity.entityName]) {
        grouped[entity.entityName] = [];
      }
      grouped[entity.entityName].push(entity);
    });

    return grouped;
  }, [combinedEntities]);

  // Filter entities based on entityFilter
  const filteredEntities = React.useMemo(() => {
    if (!entityFilter) {
      // Return all entities from all types
      return Object.values(groupedByType).flat();
    }

    // Return only entities of the filtered type
    return groupedByType[entityFilter] || [];
  }, [groupedByType, entityFilter]);

  // Get the selected entity data from all filtered entities
  const selectedEntityData = React.useMemo(() => {
    if (filteredEntities.length === 0) {
      return [];
    }

    const items: TableItem[] = [];

    // Process all filtered entities, not just the first one
    filteredEntities.forEach((entity) => {
      Object.entries(entity.data || {}).forEach(([uniqueKey, record]) => {
        items.push({
          id: `${entity.entityName}-${uniqueKey}`, // Make ID unique across entity types
          uniqueKey,
          data: record as Record<string, unknown>,
          operation: entity.operation,
          entityType: entity.entityName,
        });
      });
    });

    return items;
  }, [filteredEntities]);

  // Get schema attributes - merge attributes from all filtered entities
  const schemaAttributes = React.useMemo((): Attribute[] => {
    if (filteredEntities.length === 0) {
      return [];
    }

    // If entityFilter is specified, all entities should have the same schema
    if (entityFilter) {
      return filteredEntities[0].schema.attributes;
    }

    // If no filter, merge unique attributes from all entity types
    const attributeMap = new Map<string, Attribute>();

    filteredEntities.forEach((entity) => {
      entity.schema.attributes.forEach((attr) => {
        if (!attributeMap.has(attr.name)) {
          attributeMap.set(attr.name, attr);
        }
      });
    });

    return Array.from(attributeMap.values());
  }, [filteredEntities, entityFilter]);

  // Check if there are many columns to show a scroll indicator
  const hasManyColumns = schemaAttributes.length > 5;

  // Generate column definitions based on schema attributes
  const columnDefinitions: TableProps.ColumnDefinition<TableItem>[] = React.useMemo(() => {
    const columns: TableProps.ColumnDefinition<TableItem>[] = [
      {
        id: "operation",
        header: "Operation",
        cell: (item: TableItem) => (
          <Badge color={item.operation === "create" ? "green" : "blue"}>
            {item.operation === "create" ? "Create" : "Update"}
          </Badge>
        ),
        sortingField: "operation",
        width: 100,
        minWidth: 100,
        maxWidth: 120,
      },
    ];

    // Add entity type column when showing mixed entity types (no filter applied)
    if (!entityFilter) {
      columns.push({
        id: "entityType",
        header: "Entity Type",
        cell: (item: TableItem) => item.entityType,
        sortingField: "entityType",
        width: 120,
        minWidth: 100,
        maxWidth: 150,
      });
    }

    columns.push({
      id: "uniqueKey",
      header: (
        <Box>
          Unique Key
          {hasManyColumns && (
            <Box color="text-status-info" fontSize="body-s">
              <i>← Scroll to see more →</i>
            </Box>
          )}
        </Box>
      ),
      cell: (item: TableItem) => item.uniqueKey,
      sortingField: "uniqueKey",
      width: 150,
      minWidth: 150,
      maxWidth: 300,
    });

    // Add columns for each attribute in the schema
    schemaAttributes.forEach((attr: Attribute) => {
      columns.push({
        id: attr.name,
        header: (
          <Box>
            {attr.name}
            {attr.required && <span className="required-field-indicator">*</span>}
          </Box>
        ),
        cell: (item: TableItem) => {
          const value = item.data[attr.name];
          if (value === undefined || value === null) {
            return "-";
          }
          if (Array.isArray(value)) {
            // Handle tag objects specially
            if (
              attr.type === "tag" &&
              value.length > 0 &&
              typeof value[0] === "object" &&
              value[0] !== null &&
              "key" in value[0]
            ) {
              return (value as TagObject[]).map((tag) => `${tag.key}=${tag.value}`).join("; ");
            }
            return value.join(", ");
          }
          if (typeof value === "object") {
            return JSON.stringify(value);
          }
          return String(value);
        },
        sortingField: attr.name,
        width: Math.max(attr.name.length * 10, 100),
        minWidth: 100,
        maxWidth: 300,
      });
    });

    return columns;
  }, [schemaAttributes, hasManyColumns, entityFilter]);

  // State for sorting
  const [sortingColumn, setSortingColumn] = React.useState<TableProps.SortingColumn<TableItem>>({
    sortingField: "operation",
  });
  const [sortingDescending, setSortingDescending] = React.useState(false);

  // Handle sorting change
  const handleSortingChange = (event: { detail: TableProps.SortingState<TableItem> }) => {
    const { sortingColumn, isDescending } = event.detail;
    setSortingColumn(sortingColumn || { sortingField: "operation" });
    setSortingDescending(isDescending || false);
  };

  // Sort items
  const sortedItems = React.useMemo(() => {
    if (!sortingColumn.sortingField) {
      return selectedEntityData;
    }

    return [...selectedEntityData].sort((a, b) => {
      let valueA, valueB;
      const sortingField = sortingColumn.sortingField as string;

      if (sortingField === "uniqueKey") {
        valueA = a.uniqueKey;
        valueB = b.uniqueKey;
      } else if (sortingField === "operation") {
        valueA = a.operation;
        valueB = b.operation;
      } else if (sortingField === "entityType") {
        valueA = a.entityType;
        valueB = b.entityType;
      } else {
        valueA = a.data[sortingField];
        valueB = b.data[sortingField];
      }

      // Handle undefined/null values
      if (valueA === undefined || valueA === null) valueA = "";
      if (valueB === undefined || valueB === null) valueB = "";

      // Convert to strings for comparison
      valueA = String(valueA);
      valueB = String(valueB);

      // Compare with numeric sorting support
      const result = valueA.localeCompare(valueB, undefined, { numeric: true, sensitivity: "base" });
      return sortingDescending ? -result : result;
    });
  }, [selectedEntityData, sortingColumn, sortingDescending]);

  const { items, actions, collectionProps, filteredItemsCount, filterProps, paginationProps } = useCollection(
    sortedItems,
    {
      filtering: {
        empty: (
          <Box textAlign="center" color="inherit">
            <b>No entities found</b>
            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
              No entities were found in the imported data.
            </Box>
          </Box>
        ),
        noMatch: (
          <Box textAlign="center" color="inherit">
            <b>No matches</b>
            <Box padding={{ bottom: "s" }} variant="p" color="inherit">
              No matching entities were found in the imported data.
            </Box>
            {<Button onClick={() => actions.setFiltering("")}>Clear filter</Button>}
          </Box>
        ),
      },
      pagination: { pageSize: 10 },
      selection: {},
    }
  );

  return (
    <SpaceBetween size="l">
      <SpaceBetween size="m">
        <div className="scrollable-table-container">
          <Table
            {...collectionProps}
            columnDefinitions={columnDefinitions}
            items={items}
            loadingText="Loading imported entities"
            wrapLines
            sortingColumn={sortingColumn}
            sortingDescending={sortingDescending}
            onSortingChange={handleSortingChange}
            stickyHeader={true}
            stickyColumns={{ first: 3, last: 0 }}
            resizableColumns={true}
            filter={
              <TextFilter
                {...filterProps}
                countText={filteredItemsCount === 1 ? `1 match` : `${filteredItemsCount} matches`}
                filteringAriaLabel="Filter entities"
                filteringPlaceholder={`Filter by any property`}
              />
            }
            header={
              <Header counter={`(${selectedEntityData.length})`}>
                Imported {entityFilter ? `${entityFilter} ` : ""}entities
              </Header>
            }
            pagination={<Pagination {...paginationProps} />}
          />
        </div>
      </SpaceBetween>
    </SpaceBetween>
  );
};

export default ImportedEntitiesTable;
