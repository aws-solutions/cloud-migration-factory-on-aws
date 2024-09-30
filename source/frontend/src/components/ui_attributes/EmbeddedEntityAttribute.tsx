// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from "react";
import { SpaceBetween, Container, Header } from "@cloudscape-design/components";
import AllAttributes from "./AllAttributes";

const EmbeddedEntityAttribute = ({
  schemas,
  parentSchemaType,
  parentSchemaName,
  parentUserAccess,
  embeddedEntitySchema,
  attribute,
  embeddedItem,
  handleUserInput,
  handleUpdateValidationErrors,
}) => {
  const [localSchemas, setLocalSchemas] = useState(schemas);
  const [localEmbeddedEntitySchema, setLocalEmbeddedEntitySchema] = useState([]);

  async function handleUpdate(update) {
    handleUserInput(update);
  }

  useEffect(() => {
    setLocalSchemas(schemas);
  }, [schemas]);

  useEffect(() => {
    if (embeddedEntitySchema?.status === "loaded" && embeddedEntitySchema?.value != null) {
      let updatedEmbeddedAttributes = embeddedEntitySchema.value.map((item) => {
        //prepend the embedded_entity name to all attribute names in order to store them under a single key.
        let appendedName = attribute.name + "." + item.name;
        if (item.__orig_name) {
          //Item has already been updated name.
          return item;
        } else {
          //Store original name of item.
          item.__orig_name = item.name;
          item.name = appendedName;
          // item.group = item.group ? item.group : attribute.description;
          return item;
        }
      });
      setLocalEmbeddedEntitySchema({ schema_type: parentSchemaType, attributes: updatedEmbeddedAttributes });
    } else {
      setLocalEmbeddedEntitySchema([]);
    }
  }, [embeddedEntitySchema]);

  return (
    <SpaceBetween size="xxxs" key={attribute.name}>
      <Container key={attribute.name} header={<Header variant="h2">{attribute.description}</Header>}>
        <AllAttributes
          schema={localEmbeddedEntitySchema ? localEmbeddedEntitySchema : undefined}
          schemaName={parentSchemaName}
          userAccess={parentUserAccess}
          schemas={localSchemas}
          hideAudit={true}
          item={embeddedItem}
          handleUserInput={handleUpdate}
          handleUpdateValidationErrors={handleUpdateValidationErrors}
        />
      </Container>
    </SpaceBetween>
  );
};

export default EmbeddedEntityAttribute;
