// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from "react";
import { Checkbox, SpaceBetween } from "@cloudscape-design/components";

// Attribute Display message content
const CheckboxAttribute = ({ attribute, value, isReadonly, handleUserInput, displayHelpInfoLink }) => {
  const [localValue, setLocalValue] = useState(value);

  function handleUpdate(attribute, value, validationError) {
    setLocalValue(value);
    handleUserInput(attribute, value, validationError);
  }

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  return (
    <Checkbox
      key={attribute.name}
      onChange={(event) => handleUpdate(attribute, event.detail.checked, null)}
      checked={localValue}
      disabled={isReadonly}
      ariaLabel={attribute.name}
    >
      {attribute.description ? (
        <SpaceBetween direction="horizontal" size="xs">
          {attribute.description}
          {displayHelpInfoLink(attribute)}{" "}
        </SpaceBetween>
      ) : (
        <SpaceBetween direction="horizontal" size="xs">
          {attribute.name}
          {displayHelpInfoLink(attribute)}{" "}
        </SpaceBetween>
      )}
    </Checkbox>
  );
};

export default CheckboxAttribute;
