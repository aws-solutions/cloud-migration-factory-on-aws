/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Container,
  ExpandableSection,
  FormField,
  Header,
  Input,
  Link,
  Modal,
  Multiselect,
  Select,
  SpaceBetween,
  Tabs,
  TagEditor,
} from "@cloudscape-design/components";
import { getNestedValuePath, setNestedValuePath } from "../resources/main";
import ToolHelpEdit from "./ToolHelpEdit";
import ToolHelp from "./ToolHelp";
import SchemaAttributeConditionsEdit from "./SchemaAttributeConditionsEdit";
import { EntitySchema } from "../models/EntitySchema";

type Props = {
  title: string;
  action: string;
  attribute: any;
  schemas: Record<string, EntitySchema>;
  activeSchemaName: string;
  closeModal: () => void;
  onConfirmation: (item: { name: string }, action: string) => Promise<void>;
};

const SchemaAttributeAmendModal = ({
  closeModal,
  onConfirmation,
  title,
  attribute,
  action,
  schemas,
  activeSchemaName,
}: Props) => {
  const [localAttr, setLocalAttr] = useState(attribute);
  const [testRegexStr, setTestRegexStr] = useState("");
  const [saving, setSaving] = useState(false);

  function handleUserInput(value: { field: any; value: any }) {
    let newAttr = Object.assign({}, localAttr);
    setNestedValuePath(newAttr, value.field, value.value);

    if (value.field === "rel_entity") {
      newAttr["rel_display_attribute"] = "";
      newAttr["rel_key"] = "";
    }

    setLocalAttr(newAttr);
  }

  function handleUserInputEditSchemaHelp(key: string, update: any) {
    let tempUpdate = Object.assign({}, localAttr);
    if (!tempUpdate.help_content) {
      tempUpdate["help_content"] = {};
    }
    tempUpdate["help_content"][key] = update;
    setLocalAttr(tempUpdate);
  }

  function handleUserInputEditSchemaConditions(key: any, update: any) {
    let tempUpdate = Object.assign({}, localAttr);

    setNestedValuePath(tempUpdate, key, update);
    setLocalAttr(tempUpdate);
  }

  function handleSave() {
    setSaving(true);
    onConfirmation(localAttr, action);
  }

  function returnValidationMessage(regex: any, value: string, errorMessage: any) {
    try {
      return !value.match(regex) ? errorMessage : undefined;
    } catch (e: any) {
      return "Error in validation regular expression format: " + e.message;
    }
  }

  function getErrorText(localAttr: { group_order: string }) {
    if (localAttr.group_order && isNaN(parseInt(localAttr.group_order))) {
      return "Must be a whole number.";
    } else {
      return undefined;
    }
  }

  const getRelationshipTagsField = () => {
    return (
      <FormField
        label="Relationship display select tags"
        description="Select the additional values that will be displayed as tags in the selections list."
        errorText={!localAttr.rel_display_attribute ? "You must select an attribute to be displayed." : null}
      >
        {!localAttr.system ? (
          <Multiselect
            //selectedOptions={localAttr.rel_additional_attributes ? {label: localAttr.rel_additional_attributes, value: localAttr.rel_entity} : null}
            selectedOptions={
              localAttr.rel_additional_attributes == null
                ? []
                : localAttr.rel_additional_attributes.map((item: any) => {
                    return { label: item, value: item };
                  })
            }
            //onChange={event => handleUserInput({field: 'rel_additional_attributes', value: event.detail.selectedOption.value})}
            onChange={(event) =>
              handleUserInput({
                field: "rel_additional_attributes",
                value:
                  event.detail.selectedOptions != null
                    ? event.detail.selectedOptions.map((valueItem) => valueItem.value)
                    : [],
              })
            }
            options={
              localAttr.rel_entity
                ? schemas[localAttr.rel_entity].attributes.map((item) => {
                    return { label: item.name, value: item.name };
                  })
                : []
            }
            selectedAriaLabel={"selected"}
            filteringType="auto"
          />
        ) : (
          <Input value={localAttr.rel_additional_attributes} readOnly />
        )}
      </FormField>
    );
  };

  const getRelationshipKeyField = () => {
    return (
      <FormField
        label="Relationship key"
        description=""
        errorText={!localAttr.rel_key ? "You must select an attribute to be the key." : null}
      >
        {!localAttr.system ? (
          <Select
            selectedOption={localAttr.rel_key ? { label: localAttr.rel_key, value: localAttr.rel_key } : null}
            onChange={(event) => handleUserInput({ field: "rel_key", value: event.detail.selectedOption.value })}
            options={
              localAttr.rel_entity
                ? schemas[localAttr.rel_entity].attributes.map((item) => {
                    return { label: item.name, value: item.name };
                  })
                : []
            }
            selectedAriaLabel={"selected"}
          />
        ) : (
          <Input value={localAttr.rel_key} readOnly />
        )}
      </FormField>
    );
  };

  const getRelationshipDisplayValueField = () => {
    return (
      <FormField
        label="Relationship display value"
        description=""
        errorText={!localAttr.rel_display_attribute ? "You must select an attribute to be displayed." : null}
      >
        {!localAttr.system ? (
          <Select
            selectedOption={
              localAttr.rel_display_attribute
                ? { label: localAttr.rel_display_attribute, value: localAttr.rel_entity }
                : null
            }
            onChange={(event) =>
              handleUserInput({ field: "rel_display_attribute", value: event.detail.selectedOption.value })
            }
            options={
              localAttr.rel_entity
                ? schemas[localAttr.rel_entity].attributes.map((item) => {
                    return { label: item.name, value: item.name };
                  })
                : []
            }
            selectedAriaLabel={"selected"}
          />
        ) : (
          <Input value={localAttr.rel_display_attribute} readOnly />
        )}
      </FormField>
    );
  };

  const getRelationshipSection = () => {
    return (
      <SpaceBetween size="l">
        <FormField label="Relationship entity" description="">
          {!localAttr.system ? (
            <Select
              selectedOption={
                localAttr.rel_entity ? { label: localAttr.rel_entity, value: localAttr.rel_entity } : null
              }
              onChange={(event) => {
                handleUserInput({ field: "rel_entity", value: event.detail.selectedOption.value });
              }}
              options={[
                { label: "application", value: "application" },
                { label: "server", value: "server" },
                { label: "wave", value: "wave" },
                { label: "database", value: "database" },
                { label: "secret", value: "secret" },
              ]}
              selectedAriaLabel={"selected"}
            />
          ) : (
            <Input value={localAttr.rel_entity} readOnly />
          )}
        </FormField>
        {getRelationshipKeyField()}
        {getRelationshipDisplayValueField()}
        {getRelationshipTagsField()}
        <FormField
          label="Value list"
          description="Optional - Comma delimited list of additional values that can be selected."
        >
          <Input
            value={localAttr.listvalue}
            onChange={(event) => handleUserInput({ field: "listvalue", value: event.detail.value })}
            readOnly={localAttr.system}
          />
        </FormField>
        <FormField
          label="Relationship filter attribute"
          description="Select an attribute that will be used to filter the available options."
        >
          {!localAttr.system ? (
            <Select
              selectedOption={
                localAttr.rel_filter_attribute_name
                  ? { label: localAttr.rel_filter_attribute_name, value: localAttr.rel_entity }
                  : null
              }
              onChange={(event) =>
                handleUserInput({ field: "rel_filter_attribute_name", value: event.detail.selectedOption.value })
              }
              options={
                localAttr.rel_entity
                  ? schemas[localAttr.rel_entity].attributes.map((item) => {
                      return { label: item.name, value: item.name };
                    })
                  : []
              }
              selectedAriaLabel={"selected"}
            />
          ) : (
            <Input value={localAttr.rel_display_attribute} readOnly />
          )}
        </FormField>
        <FormField label="Filter attribute" description="Select an attribute that will provide the filter value.">
          {!localAttr.system ? (
            <Select
              selectedOption={
                localAttr.source_filter_attribute_name
                  ? { label: localAttr.source_filter_attribute_name, value: localAttr.rel_entity }
                  : null
              }
              onChange={(event) =>
                handleUserInput({ field: "source_filter_attribute_name", value: event.detail.selectedOption.value })
              }
              options={schemas[activeSchemaName].attributes.map((item: { name: any }) => {
                return { label: item.name, value: item.name };
              })}
              selectedAriaLabel={"selected"}
            />
          ) : (
            <Input value={localAttr.rel_display_attribute} readOnly />
          )}
        </FormField>
      </SpaceBetween>
    );
  };

  return (
    <Modal
      onDismiss={closeModal}
      visible={true}
      closeAriaLabel="Close"
      size="medium"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={closeModal} variant="link">
              Cancel
            </Button>
            <Button onClick={handleSave} loading={saving} variant="primary">
              Save
            </Button>
          </SpaceBetween>
        </Box>
      }
      header={title}
    >
      <SpaceBetween size="l">
        <Alert visible={localAttr.system} type="warning">
          This is a system defined attribute, Programmatic name and Type cannot be altered.
        </Alert>
        <FormField label="Programmatic name" description="">
          <Input
            value={localAttr.name}
            onChange={(event) => handleUserInput({ field: "name", value: event.detail.value })}
            readOnly={localAttr.system ? localAttr.system : false}
          />
        </FormField>

        <FormField label="Display name" description="">
          <Input
            value={localAttr.description}
            onChange={(event) => handleUserInput({ field: "description", value: event.detail.value })}
          />
        </FormField>

        <FormField label="Long description" description="">
          <Input
            value={localAttr.long_desc}
            onChange={(event) => handleUserInput({ field: "long_desc", value: event.detail.value })}
          />
        </FormField>

        <FormField label="Type" description="">
          {!localAttr.system ? (
            <Select
              selectedOption={localAttr.type ? { label: localAttr.type, value: localAttr.type } : null}
              onChange={(event) => {
                handleUserInput({ field: "type", value: event.detail.selectedOption.value });
              }}
              options={[
                { label: "string", value: "string" },
                { label: "password", value: "password" },
                { label: "date", value: "date" },
                { label: "checkbox", value: "checkbox" },
                { label: "textarea", value: "textarea" },
                { label: "tag", value: "tag" },
                { label: "list", value: "list" },
                { label: "multivalue-string", value: "multivalue-string" },
                { label: "relationship", value: "relationship" },
                { label: "json", value: "json" },
              ]}
              selectedAriaLabel={"selected"}
            />
          ) : (
            <Input value={localAttr.type} readOnly />
          )}
        </FormField>

        {localAttr.type !== "relationship" ? undefined : getRelationshipSection()}

        {localAttr.type === "list" ? (
          <FormField label="Value list" description="Comma delimited list of options.">
            <Input
              value={localAttr.listvalue}
              onChange={(event) => handleUserInput({ field: "listvalue", value: event.detail.value })}
            />
          </FormField>
        ) : null}

        {localAttr.type === "list" || localAttr.type === "relationship" ? (
          <FormField label="Multi Select" description="Allow user to select multiple values.">
            <Checkbox
              onChange={(event) => handleUserInput({ field: "listMultiSelect", value: event.detail.checked })}
              checked={localAttr.listMultiSelect}
              disabled={!!localAttr.system}
            >
              {"Multiple selection possible"}
            </Checkbox>
          </FormField>
        ) : null}

        <FormField label="Required" description="">
          <Checkbox
            onChange={(event) => handleUserInput({ field: "required", value: event.detail.checked })}
            checked={localAttr.required}
            disabled={!!localAttr.system}
          >
            {"Attribute has to be populated"}
          </Checkbox>
        </FormField>

        <FormField label="Hidden" description="">
          <Checkbox
            onChange={(event) => handleUserInput({ field: "hidden", value: event.detail.checked })}
            checked={localAttr.hidden}
            disabled={!!localAttr.system}
          >
            {"Attribute will not be displayed on screen."}
          </Checkbox>
        </FormField>
        <ExpandableSection header="Conditional Hidden or Required">
          <SchemaAttributeConditionsEdit
            schemaAttributes={schemas[activeSchemaName].attributes}
            editingSchemaConditionsTemp={
              getNestedValuePath(localAttr, "conditions") ? getNestedValuePath(localAttr, "conditions") : {}
            }
            handleUserInputEditSchemaConditions={handleUserInputEditSchemaConditions}
            editDisabled={!!(localAttr.system && (localAttr.required || localAttr.hidden))}
          />
        </ExpandableSection>

        <ExpandableSection header="Info panel">
          <Tabs
            tabs={[
              {
                label: "Edit",
                id: "edit_info",
                content: (
                  <ToolHelpEdit
                    editingSchemaInfoHelpTemp={
                      getNestedValuePath(localAttr, "help_content") ? getNestedValuePath(localAttr, "help_content") : {}
                    }
                    handleUserInputEditSchemaHelp={handleUserInputEditSchemaHelp}
                  />
                ),
              },
              {
                label: "Preview",
                id: "preview_help",
                content: <ToolHelp helpContent={getNestedValuePath(localAttr, "help_content")} />,
              },
            ]}
          />
        </ExpandableSection>

        <ExpandableSection header="Advanced options">
          <SpaceBetween size="l">
            <Container
              className="custom-dashboard-container"
              header={
                <Header
                  variant="h2"
                  description="Define groups and order for attribute to help the users understand the context of the attribute and group similar attributes."
                >
                  Attribute Grouping & Positioning (optional)
                </Header>
              }
            >
              <FormField
                label="UI Group"
                description="Supply a group or container name for this attribute to be displayed in. If not provided Default will be used."
              >
                <Input
                  value={localAttr.group}
                  onChange={(event) => handleUserInput({ field: "group", value: event.detail.value })}
                />
              </FormField>
              <FormField
                label="Order in group"
                description="Provide the order in the group. if not provided the order will be alphabetical based on the display name."
                errorText={getErrorText(localAttr)}
              >
                <Input
                  value={localAttr.group_order}
                  onChange={(event) => handleUserInput({ field: "group_order", value: event.detail.value })}
                />
              </FormField>
            </Container>

            <Container
              className="custom-dashboard-container"
              header={
                <Header
                  variant="h2"
                  description="Define a regular expression which will be used to validate the content entered by a user."
                >
                  Input validation(optional)
                </Header>
              }
            >
              <SpaceBetween size="l">
                <FormField
                  label="Validation regular expresssion"
                  description={
                    <div>
                      A full description of this syntax and its constructs can be viewed in the Java documentation,
                      here:
                      <Link
                        external
                        externalIconAriaLabel="Opens regex specification in a new tab"
                        href="https://docs.oracle.com/javase/6/docs/api/java/util/regex/Pattern.html"
                      />
                    </div>
                  }
                >
                  <SpaceBetween size="l">
                    <Input
                      value={localAttr.validation_regex}
                      onChange={(event) => handleUserInput({ field: "validation_regex", value: event.detail.value })}
                    />
                  </SpaceBetween>
                </FormField>

                <FormField label="Validation help message" description="">
                  <Input
                    value={localAttr.validation_regex_msg}
                    onChange={(event) => handleUserInput({ field: "validation_regex_msg", value: event.detail.value })}
                  />
                </FormField>

                <Container
                  className="custom-dashboard-container"
                  header={
                    <Header
                      variant="h2"
                      description="Test the validation by entering text below, this will not be saved."
                    >
                      Validation simulator
                    </Header>
                  }
                >
                  <FormField
                    label="Test validation"
                    description="Enter text to verify the outcome of your regular expression."
                    errorText={returnValidationMessage(
                      localAttr.validation_regex,
                      testRegexStr,
                      localAttr.validation_regex_msg
                    )}
                  >
                    <Input value={testRegexStr} onChange={(event) => setTestRegexStr(event.detail.value)} />
                  </FormField>
                </Container>
              </SpaceBetween>
            </Container>

            {localAttr.type === "tag" ? (
              <Container
                header={
                  <Header variant="h2" description="Provide the tags that are required and validation.">
                    Tag validation (optional)
                  </Header>
                }
              >
                <TagEditor
                  allowedCharacterPattern=".*"
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
                  tags={localAttr.requiredTags ? localAttr.requiredTags : []}
                  onChange={({ detail }) => handleUserInput({ field: "requiredTags", value: detail.tags })}
                />
              </Container>
            ) : null}

            <Container
              header={
                <Header
                  variant="h2"
                  description="The data provided here will be output when the user requires examples of the data format during intake form loading and/or field input."
                >
                  Example data
                </Header>
              }
            >
              <FormField
                label="Intake form example data"
                description="Supply an example that will be shown to a user required to load data to this attribute."
              >
                <Input
                  value={localAttr.sample_data_intake}
                  onChange={(event) => handleUserInput({ field: "sample_data_intake", value: event.detail.value })}
                />
              </FormField>
              <FormField
                label="User Interface example data"
                description="Supply an example that will be shown to a user required to enter data to this attribute."
              >
                <Input
                  value={localAttr.sample_data_form}
                  onChange={(event) => handleUserInput({ field: "sample_data_form", value: event.detail.value })}
                />
              </FormField>
              <FormField
                label="API example data"
                description="Supply an example that will be shown to a user required to enter data to this attribute."
              >
                <Input
                  value={localAttr.sample_data_api}
                  onChange={(event) => handleUserInput({ field: "sample_data_api", value: event.detail.value })}
                />
              </FormField>
            </Container>
          </SpaceBetween>
        </ExpandableSection>
      </SpaceBetween>
    </Modal>
  );
};

export default SchemaAttributeAmendModal;
