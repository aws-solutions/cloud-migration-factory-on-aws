/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useState } from "react";
import {
  Alert,
  Checkbox,
  Container,
  FormField,
  Header,
  Input,
  Link,
  Multiselect,
  SpaceBetween,
  Tabs,
  Textarea,
} from "@cloudscape-design/components";

import { useMFApps } from "../../actions/ApplicationsHook";
import { useGetServers } from "../../actions/ServersHook";
import { useMFWaves } from "../../actions/WavesHook";
import { useAutomationScripts } from "../../actions/AutomationScriptsHook";
import { useGetPipelineTemplates } from "../../actions/PipelineTemplatesHook";
import { useGetPipelines } from "../../actions/PipelinesHook";
import { useGetPipelineTemplateTasks } from "../../actions/PipelineTemplateTasksHook";

import JsonAttribute from "./JsonAttribute";
import Audit from "./Audit";

import { capitalize, getNestedValuePath, validateValue } from "../../resources/main";

import { useCredentialManager } from "../../actions/CredentialManagerHook";
import { useAdminPermissions } from "../../actions/AdminPermissionsHook";
import {
  checkAttributeRequiredConditions,
  getRelationshipRecord,
  getRelationshipValue,
} from "../../resources/recordFunctions";
import { useGetDatabases } from "../../actions/DatabasesHook";
import MultiValueStringAttribute from "./MultiValueStringAttribute";
import TagAttribute from "./TagAttribute";
import ListAttribute from "./ListAttribute";
import RelationshipAttribute from "./RelationshipAttribute";
import GroupsAttribute from "./GroupsAttribute";
import DateAttribute from "./DateAttribute";
import EmbeddedEntityAttribute from "./EmbeddedEntityAttribute";
import PoliciesAttribute from "./PoliciesAttribute";
import CheckboxAttribute from "./CheckboxAttribute";
import { ToolsContext } from "../../contexts/ToolsContext";
import { Attribute, BaseData, EntitySchema } from "../../models/EntitySchema";
import { SchemaAccess, UserAccess } from "../../models/UserAccess";
import { OptionDefinition } from "../../utils/OptionDefinition.ts";

const constDefaultGroupName = "Details";

type AllAttributesParams = {
  schema: EntitySchema;
  handleUserInput: (
    arg0: {
      field: string;
      value: any;
      validationError?: any;
    }[]
  ) => void;
  handleUpdateValidationErrors: (arg0: any[]) => void;
  item: any;
  userAccess: UserAccess;
  schemas: Record<string, EntitySchema>;
  schemaName: string;
  hideAudit?: boolean;
};

// Renders all attributes belonging to the schema when an entity is being created or edited
const AllAttributes = (props: AllAttributesParams) => {
  const { setHelpPanelContent } = useContext(ToolsContext);

  //Load all related data into the UI for all relationships to work correctly.
  // ATTN: this is not optimal currently as all data is pulled back, needs update in future to make APIs return related data for a item.
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }] = useMFWaves();
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }] = useGetServers();
  const [{ isLoading: isLoadingScripts, data: dataScripts, error: errorScripts }] = useAutomationScripts();
  const [{ isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets }] = useCredentialManager();
  const [{ isLoading: isLoadingDatabases, data: dataDatabases, error: errorDatabases }] = useGetDatabases();
  const [{ isLoading: permissionsIsLoading, data: permissionsData }] = useAdminPermissions();
  const [{ isLoading: isLoadingPipelines, data: dataPipelines, error: errorPipelines }] = useGetPipelines();
  const [{ isLoading: isLoadingPipelineTemplates, data: dataPipelineTemplates, error: errorPipelineTemplates }] =
    useGetPipelineTemplates();
  const [
    { isLoading: isLoadingPipelineTemplateTasks, data: dataPipelineTemplateTasks, error: errorPipelineTemplateTasks },
  ] = useGetPipelineTemplateTasks();

  const allData: BaseData = {
    secret: { data: dataSecrets, isLoading: isLoadingSecrets, error: errorSecrets },
    script: { data: dataScripts, isLoading: isLoadingScripts, error: errorScripts },
    database: { data: dataDatabases, isLoading: isLoadingDatabases, error: errorDatabases },
    server: { data: dataServers, isLoading: isLoadingServers, error: errorServers },
    application: { data: dataApps, isLoading: isLoadingApps, error: errorApps },
    wave: { data: dataWaves, isLoading: isLoadingWaves, error: errorWaves },
    pipeline: { data: dataPipelines, isLoading: isLoadingPipelines, error: errorPipelines },
    pipeline_template: {
      data: dataPipelineTemplates,
      isLoading: isLoadingPipelineTemplates,
      error: errorPipelineTemplates,
    },
    pipeline_template_task: {
      data: dataPipelineTemplateTasks,
      isLoading: isLoadingPipelineTemplateTasks,
      error: errorPipelineTemplateTasks,
    },
  };

  const [formValidationErrors, setFormValidationErrors] = useState<any[]>([]);
  const [showadvancedpolicy, setShowadvancedpolicy] = useState(false);

  function getFilterAttributes(attribute: Attribute): Attribute[] {
    let attributes_with_rel_filter = props.schema.attributes.filter((attributeFilter) => {
      //this attribute's value is used to filter another select if true.
      return attribute.name === attributeFilter.source_filter_attribute_name;
    });

    // Get nested filter attributes based on attributes located.
    for (const attributeFilter of attributes_with_rel_filter) {
      attributes_with_rel_filter.push(...getFilterAttributes(attributeFilter));
    }

    return attributes_with_rel_filter;
  }

  async function handleUserInput(attribute: Attribute, value: any, validationError: any) {
    let attributes_with_rel_filter = getFilterAttributes(attribute);

    let attributes_with_embedded_filter = props.schema.attributes.filter((attributeFilter) => {
      //this attribute's value is used to filter another embedded attribute if true.
      return attribute.name === attributeFilter.lookup && attributeFilter.type === "embedded_entity";
    });

    let values: {
      field: string;
      value: any[] | string | {};
      validationError: any;
    }[] = [
      {
        field: attribute.name,
        value: value,
        validationError: validationError,
      },
    ];

    // As filter value has been changed, set all child attribute values to empty.
    for (const attributeFilter of attributes_with_rel_filter) {
      values.push({
        field: attributeFilter.name,
        value: attributeFilter?.listMultiSelect ? [] : "",
        validationError: null,
      });
    }

    // Remove any values that have been set for the embedded attribute values as the embedded attribute has changed.
    for (const attributeFilter of attributes_with_embedded_filter) {
      values.push({
        field: attributeFilter.name,
        value: {},
        validationError: null,
      });
    }

    props.handleUserInput(values);
  }

  function getFilterData(entityData: any[], attribute: Attribute, currentRecord: any) {
    return entityData.filter((item) => {
      const rel_value = getNestedValuePath(item, attribute.rel_filter_attribute_name!);
      const source_value = getNestedValuePath(currentRecord, attribute.source_filter_attribute_name!);

      if (Array.isArray(source_value)) {
        return source_value?.includes(rel_value);
      } else {
        return source_value === rel_value;
      }
    });
  }

  function getSelectOptions(entityData: any[], isLoading: boolean, attribute: Attribute, currentRecord: any) {
    if (isLoading) return [];

    let dataFiltered = entityData;
    if ("rel_filter_attribute_name" in attribute && "source_filter_attribute_name" in attribute) {
      dataFiltered = getFilterData(entityData, attribute, currentRecord);
    }

    return dataFiltered.map((item) => {
      let tags = [];
      if (attribute.rel_additional_attributes) {
        for (const add_attr of attribute.rel_additional_attributes) {
          if (add_attr in item) {
            tags.push(getNestedValuePath(item, add_attr));
          }
        }
      }
      return {
        label: getNestedValuePath(item, attribute.rel_display_attribute!),
        value: getNestedValuePath(item, attribute.rel_key!),
        tags: tags,
      };
    });
  }

  //Function :   Used to retrieve the options for a select UI component from the related records.
  function getRelationshipSelect(attribute: Attribute, currentRecord: any) {
    //Get fixed option values for attribute if they have been defined in the 'listvalue' key of the attribute.
    let options = [];
    let listFull = [];

    //Add select all option to all multiselect component options.
    if (attribute.listMultiSelect) {
      options.push({ label: "All", value: "__system_all" });
    }

    if ("listvalue" in attribute) {
      options = attribute.listvalue?.split(",") || [];
      options = options.map((item) => {
        return { label: item, value: item };
      });
    }

    //Get related records list, based on entity.
    switch (attribute.rel_entity) {
      case "application":
        listFull = getSelectOptions(dataApps, isLoadingApps, attribute, currentRecord);
        break;
      case "wave":
        listFull = getSelectOptions(dataWaves, isLoadingWaves, attribute, currentRecord);
        break;
      case "server":
        listFull = getSelectOptions(dataServers, isLoadingServers, attribute, currentRecord);
        break;
      case "database":
        listFull = getSelectOptions(dataDatabases, isLoadingDatabases, attribute, currentRecord);
        break;
      case "script":
        listFull = getSelectOptions(dataScripts, isLoadingScripts, attribute, currentRecord);
        break;
      case "secret":
        listFull = getSelectOptions(dataSecrets, isLoadingSecrets, attribute, currentRecord);
        break;
      case "policy":
        listFull = getSelectOptions(permissionsData.policies, permissionsIsLoading, attribute, currentRecord);
        break;
      case "pipeline":
        listFull = getSelectOptions(dataPipelines, isLoadingPipelines, attribute, currentRecord);
        break;
      case "pipeline_template":
        listFull = getSelectOptions(
          allData.pipeline_template?.data || dataPipelineTemplates,
          isLoadingPipelineTemplates,
          attribute,
          currentRecord
        );
        break;
      case "pipeline_template_task":
        listFull = getSelectOptions(
          dataPipelineTemplateTasks,
          isLoadingPipelineTemplateTasks,
          attribute,
          currentRecord
        );
        break;
      default:
        return [];
    }

    //Prepend fixed options if used.
    listFull = options.concat(listFull);

    //Deduplicate the list of applications.
    let listDeduped = [];

    for (let listItem of listFull) {
      let found = undefined;
      found = listDeduped.find((itemNew) => {
        return itemNew.value === listItem.value;
      });

      if (!found) {
        if (listItem.value !== undefined) {
          listDeduped.push(listItem);
        }
      }
    }

    //Return fully populated list.
    return listFull;
  }

  function updateFormErrorsDisplayedToUser(attribute: Attribute, errorMsg: any) {
    let existingValidationError = formValidationErrors.filter(function (item) {
      return item.name === attribute.name;
    });

    //Error present raise attribute as error.
    if (existingValidationError.length === 0 && errorMsg !== null) {
      let newValidationErrors = formValidationErrors;
      newValidationErrors.push(attribute);
      setFormValidationErrors(newValidationErrors);
      if (props.handleUpdateValidationErrors) {
        props.handleUpdateValidationErrors(newValidationErrors);
      }
    } else if (existingValidationError.length === 1 && errorMsg === null) {
      //Attribute was in error state before update.
      clearAttributeFormError(attribute.name);
    }
  }

  function getAttributeValue(attribute: Attribute) {
    const value = getNestedValuePath(props.item, attribute.name);

    if (value) {
      return value;
    } else if (attribute.listMultiSelect) {
      return [];
    } else {
      return "";
    }
  }

  function isAttributeValueRequired(attribute: Attribute, item: any) {
    let requiredConditional = false;

    if (attribute.conditions) {
      //Evaluate if this attribute has to have a value provided based on conditions of other attribute values.
      requiredConditional = !!checkAttributeRequiredConditions(item, attribute.conditions).required;
    }
    return attribute.required || requiredConditional;
  }

  function isValueSet(value: string | any[] | null | undefined) {
    return !(value?.length === 0 || value === "" || value === undefined || value === null);
  }

  function getErrorMessageMultiValueString(attribute: Attribute, value: any) {
    for (const item of value) {
      const errorMsg = validateValue(item, attribute);
      if (errorMsg !== null) {
        return errorMsg;
      }
    }

    return null;
  }

  function getErrorMessageMultiRelationship(attribute: Attribute, value: any) {
    let errorMsg = null;

    if (attribute.listMultiSelect) {
      for (const itemValue of value) {
        const validationError = validateValue(itemValue, attribute);
        if (validationError === null && itemValue && !attribute?.listvalue?.includes(itemValue)) {
          const relatedRecord = getRelationshipRecord(attribute, allData, [itemValue]);
          if (relatedRecord === null || relatedRecord.length === 0) {
            errorMsg = "Related record not found based on value provided, please check your selections.";
            break;
          }
        }
      }
    }

    return errorMsg;
  }

  function getErrorMessageRelationship(attribute: Attribute, value: string) {
    let errorMsg;
    if (attribute.listMultiSelect) {
      errorMsg = getErrorMessageMultiRelationship(attribute, value);
    } else {
      errorMsg = validateValue(value, attribute);

      if (value && !attribute?.listvalue?.includes(value)) {
        let relatedRecord = getRelationshipRecord(attribute, allData, value);
        if (relatedRecord === null) {
          errorMsg = "Related record not found based on value provided, please check your selection.";
        }
      }
      return errorMsg;
    }

    return errorMsg;
  }

  function getErrorMessageList(attribute: Attribute, value: any) {
    if (attribute.listMultiSelect) {
      for (const valueItem of value) {
        // ATTN: what is this supposed to do? the loop always returns on the first item
        return validateValue(valueItem, attribute);
      }
    } else {
      return validateValue(value, attribute);
    }
  }

  function getErrorMessageJson(attribute: Attribute, value: string) {
    if (value && typeof value !== "object") {
      try {
        JSON.parse(value);
      } catch (objError) {
        if (objError instanceof SyntaxError) {
          return "Invalid JSON: " + objError.message;
        }
      }
    }
    return null;
  }

  function returnErrorMessage(attribute: Attribute) {
    let errorMsg: string | null | undefined;

    let value = getAttributeValue(attribute);

    if (isAttributeValueRequired(attribute, props.item) && !isValueSet(value)) {
      errorMsg = "You must specify a valid value.";
    } else {
      // Value is set inputs will be validated.
      switch (attribute.type) {
        case "multivalue-string": {
          errorMsg = getErrorMessageMultiValueString(attribute, value);
          break;
        }
        case "relationship": {
          errorMsg = getErrorMessageRelationship(attribute, value);
          break;
        }
        case "json": {
          errorMsg = getErrorMessageJson(attribute, value);
          break;
        }
        case "list": {
          errorMsg = getErrorMessageList(attribute, value);
          break;
        }
        default:
          errorMsg = validateValue(value, attribute);
      }
    }

    updateFormErrorsDisplayedToUser(attribute, errorMsg);

    return errorMsg;
  }

  function handleAccessChange(updatedData: boolean, schemaName: any, currentAccess: any, typeChanged: string) {
    const schemaNameTransform = schemaName === "app" ? "application" : schemaName;

    let schemaAccess = currentAccess.filter((schema: { schema_name: any }) => {
      return schema.schema_name === schemaNameTransform;
    });

    if (schemaAccess.length > 0) {
      schemaAccess[0][typeChanged] = updatedData;

      props.handleUserInput([{ field: "entity_access", value: currentAccess, validationError: null }]);
    } else {
      //Create schema access object.
      let newSchemaAccess: SchemaAccess = {
        schema_name: schemaNameTransform,
      };

      newSchemaAccess[typeChanged] = updatedData;

      currentAccess.push(newSchemaAccess);
      props.handleUserInput([{ field: "entity_access", value: currentAccess, validationError: null }]);
    }
  }

  function addPolicyTab(tabsArray: {}[], schema: EntitySchema) {
    let schemaPolicyTab = {};
    //Add tab for this schema type as not present.
    let tabName = "";
    switch (schema.schema_type) {
      case "user":
        tabName = "Metadata Permissions";
        break;
      case "automation":
        tabName = "Automation Action Permissions";
        break;
      case "system":
        tabName = "Advanced Permissions";
        break;
      default:
        tabName = schema.schema_type;
    }

    schemaPolicyTab = {
      label: capitalize(tabName),
      id: schema.schema_type,
      content: [],
    };
    tabsArray.push(schemaPolicyTab);

    return schemaPolicyTab;
  }

  function getPolicyTab(tabsArray: any[], schema: EntitySchema) {
    let schemaPolicyTab = tabsArray.find((tab) => {
      return tab.id === schema.schema_type;
    });

    if (!schemaPolicyTab) {
      schemaPolicyTab = addPolicyTab(tabsArray, schema);
    }

    return schemaPolicyTab;
  }

  function getPolicyPlaceHolderText(policy: any, schemaName: string, numberSelected: string | number) {
    // policy ? numItemsSelected == 0 ? "Select " + ' editable ' + schemaName + ' attributes' : numItemsSelected + ' editable ' + schemaName + ' attributes' + ' selected' : "Select " + ' editable ' + schemaName + ' attributes'
    if (policy) {
      if (numberSelected === 0) {
        return "Select editable " + schemaName + " attributes";
      } else {
        return numberSelected + " editable " + schemaName + " attributes" + " selected";
      }
    } else {
      return "Select editable " + schemaName + " attributes";
    }
  }

  function getSchemaAccessPolicy(policy: any[], schemaName: string) {
    const schemaNames = [schemaName];
    if (schemaName === "application") schemaNames.push("app");
    else if (schemaName === "app") schemaNames.push("application");

    let schemaAccess: any = {};

    schemaAccess = policy.filter((schema) => {
      return schemaNames.includes(schema.schema_name);
    });

    if (schemaAccess.length === 1) {
      schemaAccess = schemaAccess[0];
    } else {
      schemaAccess = {};
    }

    return schemaAccess;
  }

  function getSelectedAttributes(schemaAccess: Record<string, any>) {
    if (schemaAccess["attributes"]) {
      return schemaAccess["attributes"].map((valueItem: any) => {
        return { label: valueItem.attr_name, value: valueItem.attr_name };
      });
    } else {
      return [];
    }
  }

  function getSchemaDisplayName(schema: EntitySchema) {
    if (schema?.friendly_name) {
      return schema.friendly_name;
    }

    return capitalize(schema.schema_name);
  }

  function addSchemaAccessPolicyEditor(
    schema: EntitySchema,
    policy: any,
    schemaAccessPolicy: {
      create: boolean;
      read: boolean;
      update: boolean;
      delete: boolean;
    },
    selectedAttributes: OptionDefinition[],
    availableAttributes: any
  ) {
    return (
      <Container
        header={
          <Header variant="h2" description="Schema access permissions.">
            {getSchemaDisplayName(schema)}
          </Header>
        }
      >
        <SpaceBetween size="l">
          <FormField
            label={"Record level access permissions"}
            description={
              "Allow access to create, read, update and/or delete operations for " + getSchemaDisplayName(schema) + "s."
            }
          >
            <SpaceBetween direction="horizontal" size="l">
              <Checkbox
                checked={schemaAccessPolicy.create}
                onChange={(event) => handleAccessChange(event.detail.checked, schema.schema_name, policy, "create")}
              >
                Create
              </Checkbox>
              <Checkbox
                checked={schemaAccessPolicy.read}
                onChange={(event) => handleAccessChange(event.detail.checked, schema.schema_name, policy, "read")}
              >
                Read
              </Checkbox>
              <Checkbox
                checked={schemaAccessPolicy.update}
                onChange={(event) => handleAccessChange(event.detail.checked, schema.schema_name, policy, "update")}
              >
                Update
              </Checkbox>
              <Checkbox
                checked={schemaAccessPolicy.delete}
                onChange={(event) => handleAccessChange(event.detail.checked, schema.schema_name, policy, "delete")}
              >
                Delete
              </Checkbox>
            </SpaceBetween>
          </FormField>
          {schemaAccessPolicy.create || schemaAccessPolicy.update ? (
            <FormField
              label={"Attribute level access"}
              description={"Select the attributes that will be allowed based on record level access above."}
            >
              <Multiselect
                selectedOptions={selectedAttributes}
                onChange={(event) => {
                  const updatedData = event.detail.selectedOptions.find((valueItem) => {
                    return valueItem.value === "__system_all";
                  }) // if All selected by user then override other selections and add all items.
                    ? availableAttributes
                        .filter((valueItem: { value: string }) => {
                          return valueItem.value !== "__system_all";
                        }) // remove __system_all from the list as only used to select all.
                        .map((valueItem: { value: any }) => {
                          return { attr_type: schema.schema_name, attr_name: valueItem.value };
                        }) // get all values to store in record, without labels and tags.
                    : event.detail.selectedOptions.map((valueItem) => {
                        return { attr_type: schema.schema_name, attr_name: valueItem.value };
                      });
                  return handleAccessChange(updatedData, schema.schema_name, policy, "attributes");
                }}
                loadingText={""}
                statusType={undefined}
                options={availableAttributes}
                selectedAriaLabel={"selected"}
                filteringType="auto"
                placeholder={getPolicyPlaceHolderText(policy, schema.schema_name, selectedAttributes.length)}
              />
            </FormField>
          ) : undefined}
        </SpaceBetween>
      </Container>
    );
  }

  function addAutomationAccessEditor(
    schema: EntitySchema,
    policy: any,
    schemaAccessPolicy: {
      create: boolean;
    }
  ) {
    return (
      <Container
        header={
          <Header variant="h2" description={schema.description ? schema.description : "Automation access permissions."}>
            {getSchemaDisplayName(schema)}
          </Header>
        }
      >
        <SpaceBetween size="l">
          <FormField label={"Access to submit automation jobs"} description={"Allow access to submit automation jobs."}>
            <SpaceBetween direction="horizontal" size="l">
              <Checkbox
                checked={schemaAccessPolicy.create}
                onChange={(event) => handleAccessChange(event.detail.checked, schema.schema_name, policy, "create")}
              >
                Submit
              </Checkbox>
            </SpaceBetween>
          </FormField>
        </SpaceBetween>
      </Container>
    );
  }

  function getSelectableAttributes(schema: EntitySchema, isMultiSelect?: boolean) {
    let availableAttributes = [];

    if (isMultiSelect) {
      availableAttributes.push({ label: "All", value: "__system_all" });
    }

    if (schema.attributes) {
      availableAttributes = availableAttributes.concat(
        schema.attributes.map((schemaAttribute) => {
          return { label: schemaAttribute.description, value: schemaAttribute.name };
        })
      ); //Add all attributes from schema to options.
    }

    return availableAttributes;
  }

  function getPolicy(schemas: Record<string, EntitySchema>, attribute: Attribute, currentPolicy: any[], index: number) {
    let policyUITabs: any[] = [];

    for (const schemaName in schemas) {
      //Do not display edit for the following schemas as this will be made available in future releases.

      if (schemas[schemaName].schema_type === "system" && !showadvancedpolicy) {
        continue;
      }
      let availableAttributes = getSelectableAttributes(schemas[schemaName], attribute.listMultiSelect);

      if (!currentPolicy) {
        ///No access settings, could be a new record/currentPolicy, provide default access settings.
        currentPolicy = [];
        props.handleUserInput([{ field: "entity_access", value: currentPolicy, validationError: null }]);
      }

      let schemaAccessPolicy = getSchemaAccessPolicy(currentPolicy, schemaName);

      let selectedAttributes = getSelectedAttributes(schemaAccessPolicy);

      let tabSchemaType = getPolicyTab(policyUITabs, schemas[schemaName]);

      if (schemas[schemaName].schema_type !== "automation") {
        tabSchemaType.content.push(
          addSchemaAccessPolicyEditor(
            schemas[schemaName],
            currentPolicy,
            schemaAccessPolicy,
            selectedAttributes,
            availableAttributes
          )
        );
      } else if (schemas[schemaName].schema_type === "automation" && schemas[schemaName]?.actions?.length) {
        tabSchemaType.content.push(addAutomationAccessEditor(schemas[schemaName], currentPolicy, schemaAccessPolicy));
      }
    }

    return (
      <SpaceBetween size="l" key={`policy-tabs-${index}`}>
        <Tabs
          tabs={policyUITabs}
          // variant="container"
        />
        <Checkbox checked={showadvancedpolicy} onChange={(event) => setShowadvancedpolicy(event.detail.checked)}>
          Show Advanced Permissions
        </Checkbox>
      </SpaceBetween>
    );
  }

  //If attribute passed has a help_content key then the info link will be displayed.
  function displayHelpInfoLink(attribute: Attribute) {
    if (attribute.help_content) {
      return (
        <Link variant="info" key={"help-link"} onFollow={() => setHelpPanelContent(attribute.help_content, false)}>
          Info
        </Link>
      );
    } else {
      return undefined;
    }
  }

  function compareGroupOrder(a: Attribute, b: Attribute) {
    if (a.group_order && b.group_order) {
      if (a.group_order === b.group_order) {
        return 0;
      } else {
        return parseInt(a.group_order) < parseInt(b.group_order) ? -1 : 1;
      }
    } else if (!a.group_order && b.group_order) {
      return 1;
    } else if (a.group_order && !b.group_order) {
      return -1;
    }
    return undefined;
  }

  function compareAttrDescription(
    a: {
      description: string;
    },
    b: {
      description: any;
    }
  ) {
    if (a.description && b.description) {
      return a.description.localeCompare(b.description);
    } else if (!a.description && b.description) {
      return -1;
    } else if (a.description && !b.description) {
      return 1;
    }

    return undefined;
  }

  function compareAttributes(a: Attribute, b: Attribute) {
    //Ensure that attributes with an order defined get priority.
    const groupOrder = compareGroupOrder(a, b);
    if (groupOrder !== undefined) {
      return groupOrder;
    }

    const descriptionOrder = compareAttrDescription(a, b);
    if (descriptionOrder !== undefined) {
      return descriptionOrder;
    }

    return 0;
  }

  // Verify that the current access policy allows update to the attribute.
  function isReadOnly(schema: EntitySchema, userAccess: UserAccess, attribute: Attribute) {
    const schemaName = schema?.schema_name === "app" ? "application" : schema?.schema_name;

    if (
      !userAccess[schemaName] ||
      (userAccess[schemaName].create && (attribute.required || schema.schema_type === "automation"))
    ) {
      //Any required attributes will be available if the user has the create permission.
      return false;
    } else {
      for (const attr_access of userAccess[schemaName].attributes ?? []) {
        if (
          attr_access.attr_name === attribute.name &&
          (userAccess[schemaName].create || userAccess[schemaName].update)
        ) {
          return false;
        }
      }
    }

    //Default response is true.
    return true;
  }

  function clearAttributeFormError(attributeName: string) {
    let newValidationErrors = formValidationErrors.filter((item) => {
      return item.name !== attributeName;
    });
    if (newValidationErrors.length > 0) {
      setFormValidationErrors(newValidationErrors);
      if (props.handleUpdateValidationErrors) {
        props.handleUpdateValidationErrors(newValidationErrors);
      }
    } else {
      //Last error removed.
      setFormValidationErrors([]);
      if (props.handleUpdateValidationErrors) {
        props.handleUpdateValidationErrors([]);
      }
    }
  }

  function getDisplayLabel(attribute: Attribute) {
    const text = attribute.description || attribute.name;
    return (
      <SpaceBetween direction="horizontal" size="xs">
        <span key={"text"}>{text}</span>
        {displayHelpInfoLink(attribute)}
      </SpaceBetween>
    );
  }

  function getDisplayValue(attribute: Attribute, item: any, emptyValue = "") {
    const attributeValue = getNestedValuePath(item, attribute.name);

    if (attributeValue) {
      return attributeValue;
    } else {
      return emptyValue;
    }
  }

  function isAttributeHidden(attribute: Attribute, item: any) {
    const checkConditions = checkAttributeRequiredConditions(item, attribute.conditions);

    return (
      (!attribute.hidden && !attribute.hiddenCreate && checkConditions.hidden === null) ||
      checkConditions.hidden === false
    );
  }

  function buildAttributeUI(attributes: Attribute[]) {
    attributes = attributes.sort(compareAttributes);

    return attributes.map((attribute, index) => {
      if (isAttributeHidden(attribute, props.item)) {
        let validationError: any = null;

        //Check if user has update rights to attribute.
        let attributeReadOnly = isReadOnly(props.schema, props.userAccess, attribute);
        const displayKey = "item-" + index;

        switch (attribute.type) {
          case "checkbox":
            return (
              <CheckboxAttribute
                key={displayKey}
                attribute={attribute}
                isReadonly={attributeReadOnly}
                value={getNestedValuePath(props.item, attribute.name)}
                handleUserInput={handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "multivalue-string":
            validationError = returnErrorMessage(attribute);
            return (
              <MultiValueStringAttribute
                key={displayKey}
                attribute={attribute}
                isReadonly={attributeReadOnly}
                value={
                  getNestedValuePath(props.item, attribute.name)
                    ? getNestedValuePath(props.item, attribute.name).join("\n")
                    : ""
                }
                errorText={validationError}
                handleUserInput={handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "textarea":
            validationError = returnErrorMessage(attribute);
            return (
              <FormField
                key={displayKey}
                label={getDisplayLabel(attribute)}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <Textarea
                  onChange={(event) =>
                    props.handleUserInput([
                      { field: attribute.name, value: event.detail.value, validationError: validationError },
                    ])
                  }
                  value={getNestedValuePath(props.item, attribute.name)}
                  disabled={attributeReadOnly}
                />
              </FormField>
            );
          case "json":
            validationError = returnErrorMessage(attribute);
            return (
              <JsonAttribute
                key={displayKey}
                attribute={attribute}
                item={getNestedValuePath(props.item, attribute.name)}
                handleUserInput={props.handleUserInput}
                errorText={validationError}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "tag":
            return (
              <TagAttribute
                key={displayKey}
                attribute={attribute}
                tags={getNestedValuePath(props.item, attribute.name)}
                handleUserInput={props.handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "list":
            return (
              <ListAttribute
                key={displayKey}
                attribute={attribute}
                isReadonly={attributeReadOnly}
                value={getNestedValuePath(props.item, attribute.name)}
                errorText={returnErrorMessage(attribute)}
                handleUserInput={handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "relationship":
            return (
              <RelationshipAttribute
                key={displayKey}
                schemas={props.schemas}
                attribute={attribute}
                isReadonly={attributeReadOnly}
                value={getRelationshipValue(attribute, allData, getNestedValuePath(props.item, attribute.name))}
                record={getRelationshipRecord(attribute, allData, getNestedValuePath(props.item, attribute.name))}
                errorText={returnErrorMessage(attribute)}
                options={getRelationshipSelect(attribute, props.item)}
                handleUserInput={handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "policy": {
            validationError = returnErrorMessage(attribute);
            let value = getNestedValuePath(props.item, attribute.name);

            return getPolicy(props.schemas, attribute, value, index);
          }
          case "groups":
            return (
              <GroupsAttribute
                key={displayKey}
                attribute={attribute}
                isReadonly={attributeReadOnly}
                value={getNestedValuePath(props.item, attribute.name)}
                errorText={returnErrorMessage(attribute)}
                handleUserInput={props.handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "policies":
            return (
              <PoliciesAttribute
                key={displayKey}
                attribute={attribute}
                isReadonly={attributeReadOnly}
                options={getRelationshipSelect(attribute, props.item)}
                value={getNestedValuePath(props.item, attribute.name)}
                errorText={returnErrorMessage(attribute)}
                handleUserInput={handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "embedded_entity":
            let embedded_entity_schema = getRelationshipValue(
              attribute,
              allData,
              getNestedValuePath(props.item, attribute.lookup!)
            );

            /**
             * Override embedded_entity for pipeline since it is a double lookup
             */
            if (props.schemaName === "pipeline") {
              let template_tasks = allData.pipeline_template_task?.data.filter((ptt) => {
                return ptt.pipeline_template_id === props.item.pipeline_template_id;
              });

              if (!template_tasks) {
                return null;
              }

              let embedded_task_arg_schemas = template_tasks?.map((templateTask) => {
                return allData.script?.data.find((t) => {
                  return t.package_uuid === templateTask.task_id;
                });
              });

              let missing_scripts = [];

              for (let script_idx = 0; script_idx < template_tasks.length; script_idx++) {
                if (!embedded_task_arg_schemas[script_idx]) {
                  missing_scripts.push(template_tasks[script_idx]);
                }
              }

              if (template_tasks && missing_scripts.length > 0) {
                return (
                  <Alert
                    statusIconAriaLabel="Error"
                    type="error"
                    header="Could not locate the following scripts attached to the pipeline template selected."
                  >
                    {missing_scripts.map((task) => {
                      return <p>{task.task_id}</p>;
                    })}
                  </Alert>
                );
              }

              let embedded_task_arg_schemas_attributes = embedded_task_arg_schemas?.flatMap((task: any) =>
                getRelationshipValue(attribute, allData, getNestedValuePath({ task }, attribute.lookup))
              );

              // De-duping duplicate embedded entity values across pipeline template tasks
              const embedded_entity_values = embedded_task_arg_schemas_attributes
                ?.flatMap((schema) => schema.value)
                .filter(Boolean);
              const embedded_entity_value_names = embedded_entity_values?.map(
                (entity_value) => entity_value.__orig_name || entity_value.name
              );
              embedded_entity_schema = {
                status: "loaded",
                value: embedded_entity_values?.filter((value, index) => {
                  const val_name = value.__orig_name || value.name;
                  return embedded_entity_value_names?.indexOf(val_name) == index;
                }),
              };
            }

            return (
              <EmbeddedEntityAttribute
                key={displayKey}
                schemas={props.schemas}
                parentSchemaType={props.schema.schema_type}
                parentSchemaName={props.schemaName}
                parentUserAccess={props.userAccess}
                embeddedEntitySchema={embedded_entity_schema}
                embeddedItem={props.item}
                handleUpdateValidationErrors={props.handleUpdateValidationErrors}
                attribute={attribute}
                handleUserInput={props.handleUserInput}
              />
            );
          case "date":
            return (
              <DateAttribute
                key={displayKey}
                attribute={attribute}
                isReadonly={attributeReadOnly}
                value={getNestedValuePath(props.item, attribute.name)}
                errorText={returnErrorMessage(attribute)}
                handleUserInput={props.handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
            );
          case "password":
            validationError = returnErrorMessage(attribute);
            return (
              <FormField
                key={displayKey}
                label={getDisplayLabel(attribute)}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <Input
                  value={getDisplayValue(attribute, props.item)}
                  onChange={(event) =>
                    props.handleUserInput([
                      { field: attribute.name, value: event.detail.value, validationError: validationError },
                    ])
                  }
                  type="password"
                  disabled={attributeReadOnly}
                />
              </FormField>
            );
          default:
            validationError = returnErrorMessage(attribute);
            return (
              <FormField
                key={displayKey}
                label={getDisplayLabel(attribute)}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <Input
                  value={getDisplayValue(attribute, props.item)}
                  onChange={(event) => handleUserInput(attribute, event.detail.value, validationError)}
                  disabled={attributeReadOnly}
                  ariaLabel={attribute.name}
                />
              </FormField>
            );
        }
      } else {
        //Attribute is hidden, check that no errors exist for this hidden attribute, could be that a condition has hidden it.

        let existingValidationError = formValidationErrors.filter(function (item) {
          return item.name === attribute.name;
        });

        if (existingValidationError.length === 1) {
          //Error present remove as attribute no longer visible.
          clearAttributeFormError(attribute.name);
        }
      }
      return null;
    });
  }

  function compareGroupsByName(a: any, b: any) {
    //Always have default group first in UI.
    if (a.name === constDefaultGroupName) {
      return -1;
    }

    if (a.name && b.name) {
      return a.name.localeCompare(b.name);
    } else if (!a.name && b.name) {
      return -1;
    } else if (a.name && !b.name) {
      return 1;
    }
  }

  function addAttributeToGroup(attribute: Attribute, groups: any[], groupName: string) {
    let existingGroup = groups.find((o) => o.name === groupName);
    if (!existingGroup) {
      groups.push({ name: groupName, attributes: [attribute] });
    } else {
      existingGroup.attributes.push(attribute);
    }
  }

  function buildAttributeGroups(schema: any) {
    let groups: any[] = [];

    for (const attribute of schema) {
      if (attribute.group) {
        addAttributeToGroup(attribute, groups, attribute.group);
      } else {
        addAttributeToGroup(attribute, groups, constDefaultGroupName);
      }
    }

    groups = groups.sort(compareGroupsByName);

    return groups;
  }

  function buildFinalUI(schema: EntitySchema) {
    if (!schema.attributes) {
      return [];
    }
    let groupedAttrs = buildAttributeGroups(schema.attributes);

    //Create containers for each group of attributes.
    let allContainers = groupedAttrs.map((item, index) => {
      let group = buildAttributeUI(item.attributes);
      let allNull = true;

      for (const attr of group) {
        if (attr) allNull = false;
      }
      //Only show group container if at least one attribute is visible.
      if (!allNull) {
        return (
          <Container key={item.name} header={<Header variant="h2">{item.name}</Header>}>
            <SpaceBetween size="l">{group}</SpaceBetween>
          </Container>
        );
      } else {
        return null;
      }
    });

    if (!props.hideAudit) {
      allContainers.push(
        <Container key={allContainers.length + 1} header={<Header variant="h2">Audit</Header>}>
          <Audit item={props.item} />
        </Container>
      );
    }

    return allContainers;
  }

  return <SpaceBetween size="l">{props.schema ? buildFinalUI(props.schema) : undefined}</SpaceBetween>;
};

export default AllAttributes;
