// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from "react";
import { Container, FormField, Header, SpaceBetween, TagEditor } from "@cloudscape-design/components";
import { validateTags } from "../../resources/main";

const TagAttribute = ({ attribute, tags, handleUserInput, displayHelpInfoLink }) => {
  const [localValue, setLocalValue] = useState(tags);
  const [localValueErrors, setLocalValueErrors] = useState(validateTags(attribute, []));

  function handleUpdate(detail) {
    setLocalValue(detail.tags);
    const validation = validateTags(attribute, detail.tags);
    if (validation) {
      handleUserInput(attribute, detail.tags, validation);
    } else if (!detail.valid) {
      handleUserInput(attribute, detail.tags, "invalid tags definition.");
    } else {
      handleUserInput(attribute, detail.tags, null);
    }
  }

  useEffect(() => {
    const validation = validateTags(attribute, tags);
    setLocalValueErrors(validation);
    if (validation) {
      handleUserInput(attribute, tags, validation, true);
    }

    if (tags) {
      let temptags = tags.map((item) => {
        return { ...item, existing: false };
      });

      setLocalValue(temptags);
    } else {
      setLocalValue([]);
    }
  }, [tags]);

  return (
    <Container
      key={attribute.name}
      header={
        <Header variant="h2" description={attribute.long_desc}>
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
        </Header>
      }
    >
      <FormField
        errorText={
          localValueErrors ? (
            <SpaceBetween direction="vertical" size="xs">
              {localValueErrors}
            </SpaceBetween>
          ) : null
        }
      >
        <TagEditor
          allowedCharacterPattern={attribute.validation_regex ? attribute.validation_regex : undefined}
          i18nStrings={{
            keyPlaceholder: "Enter key",
            valuePlaceholder: "Enter value",
            addButton: "Add new tag",
            removeButton: "Remove",
            undoButton: "Undo",
            undoPrompt: "This tag will be removed upon saving changes",
            loading: "Loading tags that are associated with this resource",
            keyHeader: "Key",
            valueHeader: "Value",
            optional: "optional",
            keySuggestion: "Custom tag key",
            valueSuggestion: "Custom tag value",
            emptyTags: "No tags associated with the resource.",
            tooManyKeysSuggestion: "You have more keys than can be displayed",
            tooManyValuesSuggestion: "You have more values than can be displayed",
            keysSuggestionLoading: "Loading tag keys",
            keysSuggestionError: "Tag keys could not be retrieved",
            valuesSuggestionLoading: "Loading tag values",
            valuesSuggestionError: "Tag values could not be retrieved",
            emptyKeyError: "You must specify a tag key",
            maxKeyCharLengthError: "The maximum number of characters you can use in a tag key is 128.",
            maxValueCharLengthError: "The maximum number of characters you can use in a tag value is 256.",
            duplicateKeyError: "You must specify a unique tag key.",
            invalidKeyError:
              "Invalid key. Keys can only contain alphanumeric characters, spaces and any of the following: _.:/=+@-",
            invalidValueError:
              "Invalid value. Values can only contain alphanumeric characters, spaces and any of the following: _.:/=+@-",
            awsPrefixError: "Cannot start with aws:",
            tagLimit: (availableTags) =>
              availableTags === 1
                ? "You can add up to 1 more tag."
                : "You can add up to " + availableTags + " more tags.",
            tagLimitReached: (tagLimit) =>
              tagLimit === 1
                ? "You have reached the limit of 1 tag."
                : "You have reached the limit of " + tagLimit + " tags.",
            tagLimitExceeded: (tagLimit) =>
              tagLimit === 1
                ? "You have exceeded the limit of 1 tag."
                : "You have exceeded the limit of " + tagLimit + " tags.",
            enteredKeyLabel: (key) => 'Use "' + key + '"',
            enteredValueLabel: (value) => 'Use "' + value + '"',
          }}
          tags={localValue}
          onChange={({ detail }) => handleUpdate(detail)}
        />
      </FormField>
    </Container>
  );
};

export default TagAttribute;
