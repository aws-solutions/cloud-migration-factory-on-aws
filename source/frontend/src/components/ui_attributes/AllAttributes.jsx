/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
  FormField,
  Input,
  Checkbox,
  Textarea,
  Multiselect,
  Container,
  Header,
  SpaceBetween,
  Link,
  Tabs
} from '@awsui/components-react';

import { useMFApps } from "../../actions/ApplicationsHook";
import { useGetServers } from "../../actions/ServersHook.js";
import { useMFWaves } from "../../actions/WavesHook.js";
import {useAutomationScripts} from "../../actions/AutomationScriptsHook";

import JsonAttribute from "./JsonAttribute.jsx";
import Audit from "./Audit";

import {
  validateValue,
  getNestedValuePath, capitalize
} from '../../resources/main.js'

import {useCredentialManager} from "../../actions/CredentialManagerHook";
import {useAdminPermissions} from "../../actions/AdminPermissionsHook";
import {
  checkAttributeRequiredConditions,
  getRelationshipRecord,
  getRelationshipValue
} from "../../resources/recordFunctions";
import {useGetDatabases} from "../../actions/DatabasesHook";
import MultiValueStringAttribute from "./MultiValueStringAttribute";
import TagAttribute from "./TagAttribute";
import ListAttribute from "./ListAttribute";
import RelationshipAttribute from "./RelationshipAttribute";
import GroupsAttribute from "./GroupsAttribute";
import DateAttribute from "./DateAttribute";
import EmbeddedEntityAttribute from "./EmbeddedEntityAttribute";
import PoliciesAttribute from "./PoliciesAttribute";
import CheckboxAttribute from "./CheckboxAttribute";

const constDefaultContainerName = 'Details';

const AllAttributes = (props) =>
{
  //Load all related data into the UI for all relationships to work correctly.
  // TODO this is not optimal currently as all data is pulled back, needs update in future to make APIs return related data for a item.
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }] = useMFWaves();
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }] = useGetServers();
  const [{ isLoading: isLoadingScripts, data: dataScripts, error: errorScripts } ] = useAutomationScripts();
  const [{ isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets }] = useCredentialManager();
  const [{ isLoading: isLoadingDatabases, data: dataDatabases, error: errorDatabases }] = useGetDatabases()
  const [{ isLoading: permissionsIsLoading, data: permissionsData}] = useAdminPermissions();

  const allData = {secret: {data: dataSecrets, isLoading: isLoadingSecrets, error: errorSecrets},script: {data: dataScripts, isLoading: isLoadingScripts, error: errorScripts},database: {data: dataDatabases, isLoading: isLoadingDatabases, error: errorDatabases}, server: {data: dataServers, isLoading: isLoadingServers, error: errorServers}, application: {data: dataApps, isLoading: isLoadingApps, error: errorApps}, wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}};

  const [formValidationErrors, setFormValidationErrors] = useState([]);
  const [showadvancedpolicy, setShowadvancedpolicy] = useState(false);

  async function handleUserInput(attribute, value, validationError){

    let attributes_with_rel_filter = props.schema.attributes.filter(attributeFilter => {
      //this attribute's value is used to filter another select if true.
      return (attribute.name === attributeFilter.source_filter_attribute_name)
    });

    let values = [];

    values.push({
      field: attribute.name,
      value: value,
      validationError: validationError
    });

    for (const attributeFilter of attributes_with_rel_filter){
      values.push({
        field: attributeFilter.name,
        value: []
      });
    }

    await props.handleUserInput(values);

  }

  function getSelectOptions(entityData, isLoading, attribute, currentRecord) {

    if (isLoading)
      return [];

    let dataFiltered = entityData;
    if ('rel_filter_attribute_name' in attribute && 'source_filter_attribute_name' in attribute){
      dataFiltered = entityData.filter((item) => {
                                        const rel_value =  getNestedValuePath(item, attribute.rel_filter_attribute_name);
                                        const source_value = getNestedValuePath(currentRecord, attribute.source_filter_attribute_name);
                                        return (rel_value === source_value)
                                      });
    }

    return dataFiltered.map((item) => {
                            let tags = [];
                            if('rel_additional_attributes' in attribute) {
                              for (const add_attr of attribute.rel_additional_attributes) {
                                if (add_attr in item){
                                  tags.push(getNestedValuePath(item, add_attr));
                                }
                              }
                            }
                            return (
                              { label: getNestedValuePath(item, attribute.rel_display_attribute), value: getNestedValuePath(item, attribute.rel_key), tags: tags }
                            )
                          });
  }

  //Function :   Used to retrieve the options for a select UI component from the related records.
  function getRelationshipSelect (attribute, currentRecord) {

    //Get fixed option values for attribute if they have been defined in the 'listvalue' key of the attribute.
    let options = [];
    let listFull = [];

    //Add select all option to all multiselect component options.
    if (attribute.listMultiSelect) {
      options.push({label: 'All', value: '__system_all'})
    }

    if ('listvalue' in attribute) {
      options = attribute.listvalue.split(',');
      options = options.map((item) => {
        return (
          { label: item, value: item}
        )
      });
    }

    //Get related records list, based on entity.
    switch (attribute.rel_entity) {
      case 'application':
        listFull = getSelectOptions(dataApps,isLoadingApps,attribute,currentRecord);
        break;
      case 'wave':
        listFull = getSelectOptions(dataWaves,isLoadingWaves,attribute,currentRecord);
        break;
      case 'server':
        listFull = getSelectOptions(dataServers,isLoadingServers,attribute,currentRecord);
        break;
      case 'script':
        listFull = getSelectOptions(dataScripts,isLoadingScripts,attribute,currentRecord);
        break;
      case 'secret':
        listFull = getSelectOptions(dataSecrets,isLoadingSecrets,attribute,currentRecord);
        break;
      case 'policy':
        listFull = getSelectOptions(permissionsData.policies,permissionsIsLoading,attribute,currentRecord);
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
      found = listDeduped.find(itemNew => {
        return (itemNew.value === listItem.value)
      });

      if (!found) {
        if (listItem.value !== undefined){
          listDeduped.push(listItem);
        }
      }
    }

    //Return fully populated list.
    return listDeduped;

  }

  function updateFormErrorsDisplayedToUser (attribute, errorMsg){
    let existingValidationError = formValidationErrors.filter(function (item) {
      return item.name === attribute.name;
    });

    //Error present raise attribute as error.
    if (existingValidationError.length === 0 && errorMsg !== null){
      let newValidationErrors = formValidationErrors;
      newValidationErrors.push(attribute);
      setFormValidationErrors(newValidationErrors);
      if(props.handleUpdateValidationErrors){
        props.handleUpdateValidationErrors(newValidationErrors);
      }
    } else if (existingValidationError.length === 1 && errorMsg === null){
      //Attribute was in error state before update.
      clearAttributeFormError(attribute.name);
    }
  }

  function getAttributeValue(attribute){

    const value = getNestedValuePath(props.item, attribute.name);

    if (value){
      return value;
    } else if (attribute.listMultiSelect){
      return [];
    } else {
      return '';
    }
  }

  function returnErrorMessage (attribute) {

    let errorMsg = null;
    let requiredConditional = false;

    if (attribute.conditions) {
      //Evaluate if this attribute has to have a value provided based on conditions of other attribute values.
      requiredConditional = checkAttributeRequiredConditions(props.item, attribute.conditions).required
    }

    let value = getAttributeValue(attribute);

    if ((attribute.required || requiredConditional) && (value.length === 0 || value === '' || value === undefined || value === null)) {
      errorMsg = 'You must specify a valid value.';
    } else {
      // Value is set inputs will be validated.
      switch (attribute.type) {
        case 'multivalue-string': {

          for (const item of value) {
            errorMsg = validateValue(item, attribute)
          }
          break;
        }
        case 'relationship': {
          //TODO Multiselect error display support needed.
          if (!attribute.listMultiSelect) {
            errorMsg = validateValue(value, attribute)

            if (value && !attribute?.listvalue?.includes(value)){
              let relatedRecord = getRelationshipRecord(allData, attribute, value);
              if (relatedRecord === null) {
                errorMsg = 'Related record not found based on value provided, please select an item.';
              }
            }
          }
          break;
        }
        case 'json': {

          if (getNestedValuePath(props.item, attribute.name)) {
            try {
              JSON.parse(value);
            } catch (objError) {
              if (objError instanceof SyntaxError) {
                errorMsg = "Invalid JSON: " + objError.message;
              }
            }
          }
          break;
        }
        case 'list': {

          if (attribute.listMultiSelect) {
            for (const valueItem of value) {
              errorMsg = validateValue(valueItem, attribute)
            }
          } else {
            errorMsg = validateValue(getNestedValuePath(props.item, attribute.name), attribute)
          }

          break;
        }
        default:
          errorMsg = validateValue(value, attribute)
      }

    }

    updateFormErrorsDisplayedToUser(attribute, errorMsg)

    return errorMsg;

  }

  function HandleAccessChange(updatedData, schemaName, currentAccess, typeChanged){

    let schemaAccess = currentAccess.filter(schema => {
      return schema.schema_name === schemaName
    });

    if (schemaAccess.length > 0 ){
      schemaAccess[0][typeChanged] = updatedData;

      props.handleUserInput({field: 'entity_access', value: currentAccess, validationError: null})
    } else {
      //Create schema access object.
      let newSchemaAccess = {
        "schema_name": schemaName
      };

      newSchemaAccess[typeChanged] = updatedData;

      currentAccess.push(newSchemaAccess);
      props.handleUserInput({field: 'entity_access', value: currentAccess, validationError: null})
    }
  }

  function getTabArrayItem(tabsArray, id){

    let foundTab = tabsArray.find(tab => {return tab.id === id})

    return foundTab ? foundTab : null
  }

  function getPolicyPlaceHolderText(policy, schemaName, numberSelected){
    // policy ? numItemsSelected == 0 ? "Select " + ' editable ' + schemaName + ' attributes' : numItemsSelected + ' editable ' + schemaName + ' attributes' + ' selected' : "Select " + ' editable ' + schemaName + ' attributes'
    if (policy) {
      if (numberSelected === 0) {
        return 'Select editable ' + schemaName + ' attributes';
      } else {
        return numberSelected + ' editable ' + schemaName + ' attributes' + ' selected'
      }
    }else {
      return 'Select editable ' + schemaName + ' attributes'
    }
  }

  function getPolicy(schemas, attribute, policy){
    let policyUITabs = [];

    for (const schemaName in schemas){
      //Do not display edit for the following schemas as this will be made available in future releases.

      if (schemas[schemaName].schema_type === 'system' && !showadvancedpolicy) {
        continue
      }
      let options = []

      if (attribute.listMultiSelect) {
        options.push({label: 'All', value: '__system_all'})
      }

      if (schemas[schemaName].attributes) {
        options = options.concat(schemas[schemaName].attributes.map(schemaAttribute => {
          return {label: schemaAttribute.description, value: schemaAttribute.name}
        })); //Add all attributes from schema to options.
      }

      let schemaAccess = [];

      if (!policy) {
        ///No access settings, could be a new record/policy, provide default access settings.
        policy = []
        props.handleUserInput({field: 'entity_access', value: policy, validationError: null})
      }

      schemaAccess = policy.filter(schema => {
        return schema.schema_name === schemaName
      });

      if (schemaAccess.length === 1) {
        schemaAccess = schemaAccess[0]


      } else {
        schemaAccess = {}
      }

      let numItemsSelected = 0;
      let selectedAttributes = [];

      if (schemaAccess['attributes']) {
        numItemsSelected = schemaAccess['attributes'].length;
        selectedAttributes = schemaAccess['attributes'].map(valueItem => {
          return {label: valueItem.attr_name, value: valueItem.attr_name}
        });
      }

      let tabSchemaType = getTabArrayItem(policyUITabs, schemas[schemaName].schema_type);

      if (tabSchemaType === null){
        //Add tab for this schema type as not present.
        let tabName = '';
        switch (schemas[schemaName].schema_type) {
          case 'user':
            tabName = 'Metadata Permissions';
            break;
          case 'automation':
            tabName = 'Automation Action Permissions';
            break;
          case 'system':
            tabName = 'Advanced Permissions';
            break;
          default:
            tabName = schemas[schemaName].schema_type;
        }

        tabSchemaType = {
          label: capitalize(tabName),
          id: schemas[schemaName].schema_type,
          content: []
        }
        policyUITabs.push(tabSchemaType);
      }

      if (schemas[schemaName].schema_type !== 'automation') {

        tabSchemaType.content.push(
          <Container
            header={<Header variant="h2" description="Schema access permissions.">{schemas[schemaName].friendly_name ? schemas[schemaName].friendly_name : capitalize(schemaName)}</Header>}>
            <SpaceBetween size="l">
              <FormField
                label={'Record level access permissions'}
                description={'Allow access to create, read, update and/or delete operations for ' + schemaName + 's.'}
              >
                <SpaceBetween direction="horizontal" size="l">
                  <Checkbox
                    checked={schemaAccess.create}
                    onChange={event => (
                      HandleAccessChange(event.detail.checked, schemaName, policy, 'create'))}
                  >
                    Create
                  </Checkbox>
                  <Checkbox
                    checked={schemaAccess.read}
                    onChange={event => (
                      HandleAccessChange(event.detail.checked, schemaName, policy, 'read'))}
                  >
                    Read
                  </Checkbox>
                  <Checkbox
                    checked={schemaAccess.update}
                    onChange={event => (
                      HandleAccessChange(event.detail.checked, schemaName, policy, 'update'))}
                  >
                    Update
                  </Checkbox>
                  <Checkbox
                    checked={schemaAccess.delete}
                    onChange={event => (
                      HandleAccessChange(event.detail.checked, schemaName, policy, 'delete'))}
                  >
                    Delete
                  </Checkbox>
                </SpaceBetween>
              </FormField>
              {
                schemaAccess.create || schemaAccess.update
                  ?
                  <FormField
                    label={'Attribute level access'}
                    description={'Select the attributes that will be allowed based on record level access above.'}
                  >
                    <Multiselect
                      selectedOptions={numItemsSelected === 0 ? [] : selectedAttributes}
                      onChange={event => HandleAccessChange(
                        event.detail.selectedOptions.find(valueItem => {
                          return valueItem.value === '__system_all'
                        }) // if All selected by user then override other selections and add all items.
                          ?
                          options.filter(valueItem => {
                            return valueItem.value !== '__system_all'
                          })  // remove __system_all from the list as only used to select all.
                            .map(valueItem => {
                              return {attr_type: schemaName, attr_name: valueItem.value}
                            }) // get all values to store in record, without labels and tags.
                          :
                          event.detail.selectedOptions.map(valueItem => {
                            return {attr_type: schemaName, attr_name: valueItem.value}
                          })
                        , schemaName
                        , policy
                        , 'attributes'
                      )}
                      loadingText={""}
                      statusType={undefined}
                      options={options}
                      selectedAriaLabel={'selected'}
                      filteringType="auto"
                      placeholder={getPolicyPlaceHolderText(policy, schemaName,numItemsSelected)}
                    />
                  </FormField>
                  :
                  undefined
              }
            </SpaceBetween>
          </Container>
        )
      } else if (schemas[schemaName].schema_type === 'automation' && schemas[schemaName].actions.length > 0){
        tabSchemaType.content.push(
          <Container
            header={<Header variant="h2" description={schemas[schemaName].description ? schemas[schemaName].description : 'Automation access permissions.'}>{schemas[schemaName].friendly_name ? schemas[schemaName].friendly_name : capitalize(schemaName)}</Header>}>
            <SpaceBetween size="l">
              <FormField
                label={'Access to submit automation jobs'}
                description={'Allow access to submit automation jobs.'}
              >
                <SpaceBetween direction="horizontal" size="l">
                  <Checkbox
                    checked={schemaAccess.create}
                    onChange={event => (
                      HandleAccessChange(event.detail.checked, schemaName, policy, 'create'))}
                  >
                    Submit
                  </Checkbox>
                </SpaceBetween>
              </FormField>
            </SpaceBetween>
          </Container>
        )
      }
    }

    return <SpaceBetween size="l">
      <Tabs
        tabs={policyUITabs}
        // variant="container"
      />
      <Checkbox
        checked={showadvancedpolicy}
        onChange={event => (
          setShowadvancedpolicy(event.detail.checked))}
      >
        Show Advanced Permissions
      </Checkbox>
    </SpaceBetween>;

  }

  //If attribute passed has a help_content key then the info link will be displayed.
  function displayHelpInfoLink(attribute){

    if (attribute.help_content){
      return <Link variant="info" onFollow={() => props.setHelpPanelContent(attribute.help_content, false)}>Info</Link>
    } else {
      return undefined;
    }
  }

  function sortAttributes(attributes) {
    return attributes.sort(function (a, b) {
      //Ensure that attributes with an order defined get priority.
      if(a.group_order && b.group_order) {
        if (a.group_order === b.group_order){
          return 0;
        } else {
          return parseInt(a.group_order) < parseInt(b.group_order) ? -1 : 1;
        }
      } else if (!a.group_order && b.group_order) {
        return 1;
      } else if (a.group_order && !b.group_order) {
        return -1;
      }

      if (a.description && b.description){
        return a.description.localeCompare(b.description);
      }
      else if (!a.description && b.description){
        return -1;
      }
      else if (a.description && !b.description) {
        return 1;
      }
    });
  }

  // Verify that the current access policy allows update to the attribute.
  function isReadOnly(schema, userAccess, attribute){
    if ((!userAccess[schema.schema_name]) || (userAccess[schema.schema_name].create && (attribute.required || schema.schema_type === 'automation'))) {
      //Any required attributes will be available if the user has the create permission.
      return false
    } else {
      for (const attr_access of userAccess[schema.schema_name].attributes) {
        if (attr_access.attr_name === attribute.name && (userAccess[schema.schema_name].create || userAccess[schema.schema_name].update)) {
          return false
        }
      }
    }

    //Default response is true.
    return true;
  }

  function clearAttributeFormError(attributeName) {
    let newValidationErrors = formValidationErrors.filter(item => {
      return item.name !== attributeName;
    });
    if (newValidationErrors.length > 0){
      setFormValidationErrors(newValidationErrors);
      if (props.handleUpdateValidationErrors) {
        props.handleUpdateValidationErrors(newValidationErrors);
      }
    } else {
      //Last error removed.
      setFormValidationErrors([]);
      if(props.handleUpdateValidationErrors){
        props.handleUpdateValidationErrors([]);
      }

    }
  }

  function buildAttributeUI(attributes){

    attributes = sortAttributes(attributes)

    return attributes.map((attribute) => {
      const checkConditions = checkAttributeRequiredConditions(props.item, attribute.conditions);

      if ((!attribute.hidden && checkConditions.hidden === null) || (checkConditions.hidden === false)) {
        let validationError = null;

        //Check if user has update rights to attribute.
        let attributeReadOnly = isReadOnly(props.schema, props.userAccess, attribute)

        switch (attribute.type) {
          case 'checkbox':
            return <CheckboxAttribute
                attribute={attribute}
                isReadonly={attributeReadOnly}
                value={getNestedValuePath(props.item, attribute.name)}
                handleUserInput={props.handleUserInput}
                displayHelpInfoLink={displayHelpInfoLink}
              />
          case 'multivalue-string':
            validationError = returnErrorMessage(attribute)
            return (
              <MultiValueStringAttribute
              attribute={attribute}
              isReadonly={attributeReadOnly}
              value={getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name).join('\n') : ''}
              errorText={validationError}
              handleUserInput={props.handleUserInput}
              displayHelpInfoLink={displayHelpInfoLink}
            />
            )
          case 'textarea':
            validationError = returnErrorMessage(attribute)
            return (
              <FormField
                key={attribute.name}
                label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <Textarea
                  onChange={event => props.handleUserInput({field: attribute.name, value: event.detail.value, validationError: validationError})}
                  value={getNestedValuePath(props.item, attribute.name)}
                  disabled={attributeReadOnly}
                />
              </FormField>
            )
          case 'json':
            validationError = returnErrorMessage(attribute)
            return(
              <JsonAttribute
                key={attribute.name}
                attribute={attribute}
                item={getNestedValuePath(props.item, attribute.name)}
                handleUserInput={props.handleUserInput}
                errorText={validationError}
              />

            )
          case 'tag':
            return <TagAttribute
              attribute={attribute}
              tags={getNestedValuePath(props.item, attribute.name)}
              handleUserInput={props.handleUserInput}
              displayHelpInfoLink={displayHelpInfoLink}
            />
          case 'list':
            return <ListAttribute
              attribute={attribute}
              isReadonly={attributeReadOnly}
              value={getNestedValuePath(props.item, attribute.name)}
              errorText={returnErrorMessage(attribute)}
              handleUserInput={props.handleUserInput}
              displayHelpInfoLink={displayHelpInfoLink}
            />
          case 'relationship':
            return <RelationshipAttribute
              schemas={props.schemas}
              attribute={attribute}
              isReadonly={attributeReadOnly}
              value={getRelationshipValue(allData, attribute, getNestedValuePath(props.item, attribute.name))}
              record={getRelationshipRecord(allData, attribute, getNestedValuePath(props.item, attribute.name))}
              errorText={returnErrorMessage(attribute)}
              options={getRelationshipSelect(attribute, props.item)}
              handleUserInput={handleUserInput}
              displayHelpInfoLink={displayHelpInfoLink}
            />
          case 'policy': {
            validationError = returnErrorMessage(attribute)
            let value = getNestedValuePath(props.item, attribute.name)

            return (
              getPolicy(props.schemas,attribute, value)
            )
          }
          case 'groups':
            return <GroupsAttribute
              attribute={attribute}
              isReadonly={attributeReadOnly}
              value={getNestedValuePath(props.item, attribute.name)}
              errorText={returnErrorMessage(attribute)}
              handleUserInput={props.handleUserInput}
              displayHelpInfoLink={displayHelpInfoLink}
            />
          case 'policies':
            return <PoliciesAttribute
              attribute={attribute}
              isReadonly={attributeReadOnly}
              options={getRelationshipSelect(attribute, props.item)}
              value={getNestedValuePath(props.item, attribute.name)}
              errorText={returnErrorMessage(attribute)}
              handleUserInput={handleUserInput}
              displayHelpInfoLink={displayHelpInfoLink}
            />
          case 'embedded_entity':
            return <EmbeddedEntityAttribute
              schemas={props.schemas}
              parentSchemaType={props.schema.schema_type}
              parentSchemaName={props.schemaName}
              parentUserAccess={props.userAccess}
              embeddedEntitySchema={getRelationshipValue(allData, attribute, getNestedValuePath(props.item, attribute.lookup))}
              embeddedItem={props.item}
              handleUpdateValidationErrors={props.handleUpdateValidationErrors}
              attribute={attribute}
              handleUserInput={props.handleUserInput}
              displayHelpInfoLink={displayHelpInfoLink}
            />
          case 'date':
            return <DateAttribute
              attribute={attribute}
              isReadonly={attributeReadOnly}
              value={getNestedValuePath(props.item, attribute.name)}
              errorText={returnErrorMessage(attribute)}
              handleUserInput={props.handleUserInput}
              displayHelpInfoLink={displayHelpInfoLink}
            />
          case 'password':
            validationError = returnErrorMessage(attribute)
            return (
              <FormField
                key={attribute.name}
                label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <Input
                  value={getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name) : ''}
                  onChange={event => props.handleUserInput({field: attribute.name, value: event.detail.value, validationError: validationError})}
                  type="password"
                  disabled={attributeReadOnly}
                />
              </FormField>
            )
          default:
            validationError = returnErrorMessage(attribute)
            return (
              <>
                <FormField
                  key={attribute.description ? attribute.description : attribute.name}
                  label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                  description={attribute.long_desc}
                  errorText={validationError}
                >
                  <Input
                    value={getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name) : ''}
                    onChange={event => props.handleUserInput({field: attribute.name, value: event.detail.value, validationError: validationError})}
                    disabled={attributeReadOnly}
                    ariaLabel={attribute.name}
                  />
                </FormField>
              </>
            )
        }

      } else {
        //Attribute is hidden, check that no errors exist for this hidden attribute, could be that a condition has hidden it.

        let existingValidationError = formValidationErrors.filter(function (item) {
          return item.name === attribute.name;
        });


        if (existingValidationError.length === 1){
          //Error present remove as attribute no longer visible.
          clearAttributeFormError(attribute.name);
        }
      }
      return null;
    });
  }

  function buildAttributeGroups(schema){

    let groups = [];

    for (const schemaItem of schema){

      if (schemaItem.group){
        let obj = groups.find(o => o.name === schemaItem.group);
        if(!obj){
          groups.push({name: schemaItem.group, attributes: [schemaItem]});
        } else {
          obj.attributes.push(schemaItem);
        }
      } else {
        let obj = groups.find(o => o.name === constDefaultContainerName);
        if(!obj){
          groups.push({name: constDefaultContainerName, attributes: [schemaItem]});
        } else {
          obj.attributes.push(schemaItem);
        }
      }
    }

    groups = groups.sort(function (a, b) {
      //Always have default group first in UI.
      if(a.name === constDefaultContainerName){
        return -1;
      }

      if (a.name && b.name){
        return a.name.localeCompare(b.name);
      }
      else if (!a.name && b.name){
        return -1;
      }
      else if (a.name && !b.name) {
        return 1;
      }
    });

    return groups;
  }


  function buildFinalUI(schema) {

    if (!schema.attributes){
      return [];
    }
    let groupedAttrs = buildAttributeGroups(schema.attributes);

    //Create containers for each group of attributes.
    let allContainers = groupedAttrs.map((item) => {
      let group = buildAttributeUI(item.attributes)
      let allNull = true;

      for (const attr of group){
        if (attr)
          allNull = false
      }
      //Only show group container if at least one attribute is visible.
      if (!allNull) {
        return (
          <Container key={item.name} header={<Header variant="h2">{item.name}</Header>}>
            <SpaceBetween size="l">
              {group}
            </SpaceBetween>
          </Container>
        )
      } else {
        return null;
      }
    });

    if (!props.hideAudit) {
      allContainers.push(
        <Container header={<Header variant="h2">Audit</Header>}>
          <Audit item={props.item}/>
        </Container>
      );
    }

    return allContainers;
  }

  return (
    <SpaceBetween size="l">
      {
        props.schema
          ?
          buildFinalUI(props.schema)
          :
          undefined
      }
    </SpaceBetween>
  );
};

export default AllAttributes;
