import React from "react";
import { Container, Header, Select, SelectProps } from "@cloudscape-design/components";
import { EntitySchema } from "../../models";
import { entitySelectOptions } from "./data-source-utils";

export interface EntitySelectionProps {
  readonly schemas: Record<string, EntitySchema>;
  readonly entities: string[];
  readonly selectedEntity?: string;
  readonly onEntitySelectionChange?: (entity: string | undefined) => void;
}

/**
 * Component for selecting entity types from a dropdown.
 * Used to filter validation results by entity type.
 */
const EntitySelection: React.FC<EntitySelectionProps> = ({
  schemas,
  entities,
  selectedEntity,
  onEntitySelectionChange,
}) => {
  const entityOptions: SelectProps.Option[] = React.useMemo(
    () => entitySelectOptions(schemas, entities),
    [schemas, entities]
  );

  return (
    <Container
      header={
        <Header variant="h2" description="Select an entity type to view its data and validation results">
          Entity selection
        </Header>
      }
    >
      <Select
        selectedOption={entityOptions.find((o) => o.value === selectedEntity) ?? null}
        onChange={(event) => onEntitySelectionChange?.(event.detail.selectedOption.value)}
        options={entityOptions}
        placeholder="Select an entity type"
        empty="No entity types available"
      />
    </Container>
  );
};

export default EntitySelection;
