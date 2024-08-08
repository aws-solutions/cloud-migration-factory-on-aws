// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from "react";
import { FormField, SpaceBetween, Textarea } from "@awsui/components-react";

const MultiValueStringAttribute = ({
  attribute,
  value,
  isReadonly,
  errorText,
  handleUserInput,
  displayHelpInfoLink,
}) => {
  const [localValue, setLocalValue] = useState(value);
  const [currentErrorText, setCurrentErrorText] = useState(errorText);

  function handleUpdate(event) {
    setLocalValue(event.detail.value);
    handleUserInput(attribute, event.detail.value === "" ? [] : event.detail.value.split("\n"), currentErrorText);
  }

  useEffect(() => {
    setCurrentErrorText(errorText);
  }, [errorText]);

  return (
    <FormField
      key={attribute.name}
      label={
        attribute.description ? (
          <SpaceBetween direction="horizontal" size="xs">
            {attribute.description}
            {displayHelpInfoLink(attribute)}{" "}
          </SpaceBetween>
        ) : (
          <SpaceBetween direction="horizontal" size="xs">
            {attribute.name}
            {displayHelpInfoLink(attribute)}{" "}
          </SpaceBetween>
        )
      }
      description={attribute.long_desc}
      errorText={currentErrorText}
    >
      <Textarea
        onChange={(event) => handleUpdate(event)}
        value={localValue}
        disabled={isReadonly}
        ariaLabel={attribute.name}
      />
    </FormField>
  );
};

export default MultiValueStringAttribute;
