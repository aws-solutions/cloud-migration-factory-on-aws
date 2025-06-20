// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState, useMemo } from "react";
import { FormField, Multiselect, SpaceBetween } from "@cloudscape-design/components";
import { useValueLists } from "../../actions/ValueListsHook";
import { getNestedValuePath } from "../../resources/main";

const GroupsAttribute = ({ attribute, value, isReadonly, returnErrorMessage, handleUserInput, displayHelpInfoLink }) => {
  const [localValue, setLocalValue] = useState(Array.isArray(value) ? value : []);
  const [currentErrorText, setCurrentErrorText] = useState(null);
  const [currentVLErrorText, setCurrentVLErrorText] = useState(null);

  const [{ isLoading: isLoadingVL, data: dataVL, error: dataError }, { update: updateVL, addValueListItem }] = useValueLists();

  // Memoize options to prevent unnecessary recalculations
  const localOptions = useMemo(() => {
    if (!attribute.listValueAPI || !dataVL[attribute.listValueAPI]) {
      return [];
    }

    const data = dataVL[attribute.listValueAPI];
    if (data.errorMessage) {
      setCurrentVLErrorText(data.errorMessage);
      // Ensure error is propagated to parent
      handleUserInput(attribute, localValue, data.errorMessage);
      return [];
    }

    return (data.values || [])
      .map((item) => {
        if (!item) return null;
        const value = attribute.type === "users" ? item.email : item;
        if (!value) return null;
        return {
          label: value,
          value: value
        };
      })
      .filter(Boolean);
  }, [attribute.listValueAPI, attribute.type, dataVL, attribute.name, localValue]);

  // Handle API errors
  useEffect(() => {
    if (dataError) {
      const errorMessage = dataError.message || "Failed to load data";
      setCurrentVLErrorText(errorMessage);
      handleUserInput(attribute, localValue, errorMessage);
    }
  }, [dataError, attribute.name, localValue]);

  const statusType = useMemo(() => {
    if (attribute.listValueAPI && isLoadingVL && currentVLErrorText) {
      return "error";
    } else if (attribute.listValueAPI && isLoadingVL) {
      return "loading";
    }
    return undefined;
  }, [attribute.listValueAPI, isLoadingVL, currentVLErrorText]);

  const placeholderText = useMemo(() => {
    if (!localValue || localValue.length === 0) {
      return "Select " + (attribute.description || attribute.name);
    }
    return localValue.length + " " + (attribute.description || attribute.name) + " selected";
  }, [localValue, attribute.description, attribute.name]);

  function handleUpdate(event) {
    if (!event.detail.selectedOptions) {
      return;
    }

    const selectedValues = event.detail.selectedOptions.map(option => option.value);

    // Convert the selected options into the appropriate format based on type
    const formattedValue = selectedValues.map(val => {
      if (!val) return null;

      if (attribute.type === "users") {
        return { email: val };
      } else if (attribute.type === "groups") {
        return { group_name: val };
      } else {
        return val;
      }
    }).filter(Boolean);

    setLocalValue(formattedValue);

    // Only check for required validation if the attribute is explicitly marked as required
    let validationError = null;
    if (attribute.required === true && (!formattedValue || formattedValue.length === 0)) {
      validationError = "You must specify a valid value";
    }

    // Get any additional validation errors from the parent component
    if (returnErrorMessage && typeof returnErrorMessage === 'function') {
      const customError = returnErrorMessage(attribute, formattedValue);
      if (customError) {
        validationError = customError;
      }
    }

    // Update error state based on validation result
    setCurrentErrorText(validationError);
    if (!validationError) {
      setCurrentVLErrorText(null);
    }
    
    handleUserInput(attribute, formattedValue, validationError);
  }

  // Load data only once when component mounts or when attribute changes
  useEffect(() => {
    if ((attribute.type === "groups" || attribute.type === "users") && attribute.listValueAPI) {
      addValueListItem(attribute.listValueAPI);
      updateVL();
    }
  }, [attribute.type, attribute.listValueAPI]);

  // Check for validation errors on mount and when value changes
  useEffect(() => {
    if (returnErrorMessage && typeof returnErrorMessage === 'function') {
      const error = returnErrorMessage(attribute, localValue);
      setCurrentErrorText(error);
    }
  }, [attribute, localValue, returnErrorMessage]);

  useEffect(() => {
    // Initialize or update localValue, ensuring it's always an array
    const newValue = Array.isArray(value) ? value : [];
    setLocalValue(newValue.filter(Boolean)); // Remove any null/undefined values
  }, [value]);

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
      errorText={currentErrorText || currentVLErrorText}
    >
      <Multiselect
        selectedOptions={
          !localValue || localValue.length === 0
            ? []
            : localValue.map((item) => {
                if (!item) return null;
                const value = attribute.type === "users" ? item.email : item.group_name;
                if (!value) return null;
                return {
                  label: value,
                  value: value
                };
              }).filter(Boolean)
        }
        onChange={handleUpdate}
        statusType={statusType}
        loadingText={`Loading ${attribute.type}...`}
        errortext={currentVLErrorText || undefined}
        options={localOptions}
        disabled={isReadonly}
        selectedAriaLabel="Selected"
        filteringType="auto"
        ariaLabel={attribute.name}
        placeholder={placeholderText}
      />
    </FormField>
  );
};

export default React.memo(GroupsAttribute);
