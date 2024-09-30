// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from "react";
import { DatePicker, FormField, SpaceBetween } from "@cloudscape-design/components";

const DateAttribute = ({ attribute, value, isReadonly, errorText, handleUserInput, displayHelpInfoLink }) => {
  const [localValue, setLocalValue] = useState(value);
  const [currentErrorText, setCurrentErrorText] = useState(errorText);

  function handleUpdate(event) {
    setLocalValue(event.detail.value);
    handleUserInput({ field: attribute.name, value: event.detail.value, validationError: currentErrorText });
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
            {displayHelpInfoLink ? displayHelpInfoLink(attribute) : undefined}{" "}
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
      <DatePicker
        onChange={(event) => handleUpdate(event)}
        value={localValue ? localValue : ""}
        openCalendarAriaLabel={(selectedDate) =>
          "Choose Date" + (selectedDate ? `, selected date is ${selectedDate}` : "")
        }
        nextMonthAriaLabel="Next month"
        placeholder="YYY/MM/DD"
        previousMonthAriaLabel="Previous month"
        todayAriaLabel="Today"
        disabled={isReadonly}
        ariaLabel={attribute.name}
      />
    </FormField>
  );
};

export default DateAttribute;
