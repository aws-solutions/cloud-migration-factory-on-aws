/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import {
  FormField,
  Input,
  Checkbox,
  Textarea,
  Select,
  Multiselect,
  TagEditor,
  Container,
  Header,
  DatePicker,
  SpaceBetween,
  Link,
  Button,
  Grid,
  Spinner,
  Tabs
} from '@awsui/components-react';

import { useMFApps } from "../../actions/ApplicationsHook";
import { useGetServers } from "../../actions/ServersHook.js";
import { useMFWaves } from "../../actions/WavesHook.js";
import {useAutomationScripts} from "../../actions/AutomationScriptsHook";
import {useValueLists} from "../../actions/ValueListsHook";

import JsonAttribute from "./JsonAttribute.jsx";
import Audit from "./Audit";

import {
  validateValue,
  getNestedValuePath, capitalize
} from '../../resources/main.js'

import RelatedRecordPopover from "./RelatedRecordPopover";
import {useCredentialManager} from "../../actions/CredentialManagerHook";
import {useAdminPermissions} from "../../actions/AdminPermissionsHook";
import {
  checkAttributeRequiredConditions,
  getRelationshipRecord,
  getRelationshipValue
} from "../../resources/recordFunctions";
import {useGetDatabases} from "../../actions/DatabasesHook";

const constDefaultContainerName = 'Details';

const AllAttributes = (props) =>
{
  //Load all related data into the UI for all relationships to work correctly.
  // TODO this is not optimal currently as all data is pulled back, needs update in future to make APIs return related data for a item.
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, { update: updateWaves }] = useMFWaves();
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }, { update: updateApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, { update: updateServers }] = useGetServers();
  const [{ isLoading: isLoadingScripts, data: dataScripts, error: errorScripts }, {update: updateScripts } ] = useAutomationScripts();
  const [{ isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets }, { updateSecrets }] = useCredentialManager();
  const [{ isLoading: isLoadingDatabases, data: dataDatabases, error: errorDatabases }, { update: updateDatabases }] = useGetDatabases()
  const [{ isLoading: permissionsIsLoading, data: permissionsData, error: permissionsError}, { update: permissionsUpdate }] = useAdminPermissions();
  const [{ isLoading: isLoadingVL, data: dataVL, error: errorVL }, {update: updateVL , addValueListItem } ] = useValueLists();

  const allData = {secret: {data: dataSecrets, isLoading: isLoadingSecrets, error: errorSecrets},script: {data: dataScripts, isLoading: isLoadingScripts, error: errorScripts},database: {data: dataDatabases, isLoading: isLoadingDatabases, error: errorDatabases}, server: {data: dataServers, isLoading: isLoadingServers, error: errorServers}, application: {data: dataApps, isLoading: isLoadingApps, error: errorApps}, wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}};

  const [formValidationErrors, setFormValidationErrors] = useState([]);
  const [embeddedAttributes, setEmbeddedAttributes] = useState({});
  const [optionsChanged, setOptionsChanged] = useState(0);
  const [showadvancedpolicy, setShowadvancedpolicy] = useState(false);

  //
  //Function adds all attributes that have an API generated value list selection, to the useValueLists hook, which will async gather the dropdown data.
  //
  useEffect(() => {

    if (!props.schema){
      return;
    }

    let attributes_with_lists = props.schema.attributes.filter(function (entry) {
      //Return only attributes that are lists that have the listValueAPI key defined.
      return (entry.type === 'list' && entry.listValueAPI || entry.type === 'groups' && entry.listValueAPI);
    })

    for (const attribute of attributes_with_lists){
      addValueListItem(attribute.listValueAPI);
    }

    updateVL();

  },[props.schema]);

  function getRelationships(){
    let attributes_with_rels = props.schema.attributes.filter(function (entry) {
      return entry.type === 'relationship';
    })

    let distinctTables = [...new Set(attributes_with_rels.map(x => x.rel_entity))];

    for (let tableIndx = 0; tableIndx < distinctTables.length; tableIndx++){

    }
  }

  async function handleUserInput(attribute, value, validationError){

    let attributes_with_rel_filter = props.schema.attributes.filter(attributeFilter => {
      if (attribute.name === attributeFilter.source_filter_attribute_name) {
        //this attribute's value is used to filter another select
        return true;
      } else {
        //not used forget it.
        return false;
      }
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
      options = options.map((item, index) => {
        return (
          { label: item, value: item}
        )
      });
    }

    //Get related records list, based on entity.
    switch (attribute.rel_entity) {
      case 'application':
        if (isLoadingApps)
          return [];
        else {
          let dataFiltered = []
          if ('rel_filter_attribute_name' in attribute && 'source_filter_attribute_name' in attribute){
            dataFiltered = dataApps.filter((item) => {
              const rel_value =  getNestedValuePath(item, attribute.rel_filter_attribute_name);
              const source_value = getNestedValuePath(currentRecord, attribute.source_filter_attribute_name);
              if (rel_value === source_value) {
                return true;
              } else {
                return false;
              }
            });
          } else {
            dataFiltered = dataApps
          }

          listFull = dataFiltered.map((item, index) => {
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
        break;
      case 'wave':
        if (isLoadingWaves)
          return [];
        else {
          let dataFiltered = []
          if ('rel_filter_attribute_name' in attribute && 'source_filter_attribute_name' in attribute){
            dataFiltered = dataWaves.filter((item) => {
              const rel_value =  getNestedValuePath(item, attribute.rel_filter_attribute_name);
              const source_value = getNestedValuePath(currentRecord, attribute.source_filter_attribute_name);
              if (rel_value === source_value) {
                return true;
              } else {
                return false;
              }
            });
          } else {
            dataFiltered = dataWaves
          }

          listFull = dataFiltered.map((item, index) => {
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
        break;
      case 'server':
        if (isLoadingServers)
          return [];
        else {
          let dataFiltered = []
          if ('rel_filter_attribute_name' in attribute && 'source_filter_attribute_name' in attribute){
            dataFiltered = dataServers.filter((item) => {
              const rel_value =  getNestedValuePath(item, attribute.rel_filter_attribute_name);
              const source_value = getNestedValuePath(currentRecord, attribute.source_filter_attribute_name);
              if (rel_value === source_value) {
                return true;
              } else {
                return false;
              }
            });
          } else {
            dataFiltered = dataServers
          }

          listFull = dataFiltered.map((item, index) => {
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
          })

        }
        break;
      case 'script':
        if (isLoadingScripts)
          return [];
        else {
          let dataFiltered = []
          if ('rel_filter_attribute_name' in attribute && 'source_filter_attribute_name' in attribute){
            dataFiltered = dataScripts.filter((item) => {
              const rel_value =  getNestedValuePath(item, attribute.rel_filter_attribute_name);
              const source_value = getNestedValuePath(currentRecord, attribute.source_filter_attribute_name);
              if (rel_value === source_value) {
                return true;
              } else {
                return false;
              }
            });
          } else {
            dataFiltered = dataScripts
          }

          listFull = dataFiltered.map((item, index) => {
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
        break;
      case 'secret':
        if (isLoadingSecrets)
          return [];
        else {
          let dataFiltered = []
          if ('rel_filter_attribute_name' in attribute && 'source_filter_attribute_name' in attribute){
            dataFiltered = dataSecrets.filter((item) => {
              const rel_value =  getNestedValuePath(item, attribute.rel_filter_attribute_name);
              const source_value = getNestedValuePath(currentRecord, attribute.source_filter_attribute_name);
              if (rel_value === source_value) {
                return true;
              } else {
                return false;
              }
            });
          } else {
            dataFiltered = dataSecrets;
          }

          listFull = dataFiltered.map((item, index) => {
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
        break;
      case 'policy':
        if (permissionsIsLoading)
          return [];
        else {
          let dataFiltered = []
          if ('rel_filter_attribute_name' in attribute && 'source_filter_attribute_name' in attribute){
            //Filter criteria provided, return only matching data.
            dataFiltered = permissionsData.policies.filter((item) => {
              const rel_value =  getNestedValuePath(item, attribute.rel_filter_attribute_name);
              const source_value = getNestedValuePath(currentRecord, attribute.source_filter_attribute_name);
              if (rel_value === source_value) {
                return true;
              } else {
                return false;
              }
            });
          } else {
            //No filter return all records.
            dataFiltered = permissionsData.policies;
          }

          listFull = dataFiltered.map((item, index) => {
            let tags = [];
            //Check if additional values have been requested for display on selector as tags.
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
        break;
      default:
        return [];
    }

    //Prepend fixed options if used.
    listFull = options.concat(listFull);

    //Deduplicate the list of applications.
    let listDeduped = [];

    for (let itemIdx = 0; itemIdx < listFull.length; itemIdx++) {
      let found = undefined;
      found = listDeduped.find(itemNew => {
        if (itemNew.value === listFull[itemIdx].value){
          return true;
        }
      });

      if (!found) {
        if (listFull[itemIdx].value !== undefined){
          listDeduped.push(listFull[itemIdx]);
        }
      }
    }

    //Return fully populated list.
    return listDeduped;

  }

  function returnErrorMessage (attribute) {

    let errorMsg = null;

    //TODO Temporary fix for dealing with scripts that have incorrect type case on key. Need to update packages to support correct format.
    let attributeType = attribute.type ? attribute.type : attribute.Type ? attribute.Type : null;
    switch (attributeType) {
      case 'multivalue-string': {
        let requiredConditionalList = false;
        let valueList = getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name): []

        if (attribute.conditions) {
          //Is still required after checking the conditions.
          requiredConditionalList = checkAttributeRequiredConditions(props.item, attribute.conditions).required
        }

        if ((attribute.required || requiredConditionalList) && (valueList.length === 0 || valueList === '' || valueList === undefined || valueList === null)) {
          errorMsg = 'You must specify a value.';
        } else {
          for (const item of valueList) {
            errorMsg = validateValue(item, attribute)
          }
        }
        break;
      }
      case 'relationship': {
        let requiredConditionalList = false;
        let valueList = getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name) : attribute.listMultiSelect ? [] : '';

        if (attribute.conditions) {
          //Is still required after checking the conditions.
          requiredConditionalList = checkAttributeRequiredConditions(props.item, attribute.conditions).required
        }

        if ((attribute.required || requiredConditionalList) && (valueList.length === 0 || valueList === '' || valueList === undefined || valueList === null)) {
          errorMsg = 'You must specify a value.';
        } else {
          if (attribute.listMultiSelect) {
            for (let item in valueList) {
              //errorMsg = validateValue(getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name)[item] : '', attribute)
            }
            break;
          } else {
            errorMsg = validateValue(value, attribute)

            if (valueList !== '' && valueList !== undefined && valueList !== null && !(attribute.listvalue && attribute.listvalue.includes(valueList))) {
              let relatedRecord = getRelationshipRecord(allData, attribute, valueList);
              if (relatedRecord === null) {
                errorMsg = 'Related record not found based on value provided, please select an item.';
              }
            }
          }
        }
        break;
      }
      case 'json': {
        let requiredConditionalList = false;
        let value = getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name) : '';

        if (attribute.conditions) {
          //Is still required after checking the conditions.
          requiredConditionalList = checkAttributeRequiredConditions(props.item, attribute.conditions).required
        }

        if ((attribute.required || requiredConditionalList) && (value.length === 0 || value === '' || value === undefined || value === null)) {
          errorMsg = 'You must enter a value.';
        } else {
          if (getNestedValuePath(props.item, attribute.name)) {
            try {
              let testJSON = JSON.parse(value);
            } catch (objError) {
              if (objError instanceof SyntaxError) {
                errorMsg = "Invalid JSON: " + objError.message;
              }
            }
          }
        }
        break;
      }
      case 'list': {
        let valueList = getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name) : [];
        let requiredConditionalList = false;

        if (attribute.conditions) {
          //Is still required after checking the conditions.
          requiredConditionalList = checkAttributeRequiredConditions(props.item, attribute.conditions).required
        }

        if ((attribute.required || requiredConditionalList) && (valueList.length === 0 || valueList === '' || valueList === undefined || valueList === null)) {
          errorMsg = 'You must specify a value.';
        } else {

          if (attribute.listMultiSelect) {
            for (const valueItem of valueList) {
              errorMsg = validateValue(valueItem, attribute)
            }
          } else {
            errorMsg = validateValue(getNestedValuePath(props.item, attribute.name), attribute)
          }
        }

        break;
      }
      default:
        let value = getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name) : '';
        let requiredConditional = false;

        if (attribute.conditions) {
          //Is still required after checking the conditions.
          requiredConditional = checkAttributeRequiredConditions(props.item, attribute.conditions).required
        }
        if((attribute.required || requiredConditional) && (value === '' || value === undefined || value === null)){
          errorMsg = 'You must specify a value.';
        } else {
          errorMsg = validateValue(value, attribute)
        }

    }

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
      let newValidationErrors = formValidationErrors.filter(item => {
        return item.name !== attribute.name;
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

  function getPolicy(schemas, attribute, policy){
    let policyUITabs = [];
    let policyUI = [];

    for (const schemaName in schemas){
      //Do not display edit for the following schemas as this will be made available in future releases.

      if (schemas[schemaName].schema_type === 'system' && !showadvancedpolicy) {
        continue
      }
      let options = []

      //console.log(JSON.stringify(schemas[schemaName]));

      if (attribute.listMultiSelect) {
        options.push({label: 'All', value: '__system_all'})
      }

      if (schemas[schemaName].attributes) {
        options = options.concat(schemas[schemaName].attributes.map(schemaAttribute => {
          return {label: schemaAttribute.description, value: schemaAttribute.name}
        })); //Add all attributes from schema to options.
      }

      let filteredValues = [];
      let otherValues = [];

      if (policy !== undefined){
        filteredValues = policy;
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
                      selectedOptions={numItemsSelected == 0 ? [] : selectedAttributes}
                      onChange={event => HandleAccessChange(
                        event.detail.selectedOptions.find(valueItem => {
                          return valueItem.value === '__system_all'
                        }) // if All selected by user then override other selections and add all items.
                          ?
                          options.filter(valueItem => {
                            return valueItem.value != '__system_all'
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
                      placeholder={policy ? numItemsSelected == 0 ? "Select " + ' editable ' + schemaName + ' attributes' : numItemsSelected + ' editable ' + schemaName + ' attributes' + ' selected' : "Select " + ' editable ' + schemaName + ' attributes'}
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

    return <SpaceBetween>
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

  function buildAttributeUI(attributes){
    var allAttributes = [];

    attributes = attributes.sort(function (a, b) {
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

    allAttributes = attributes.map((attribute, indx) => {
      const checkConditions = checkAttributeRequiredConditions(props.item, attribute.conditions);

      if ((!attribute.hidden && checkConditions.hidden === null) || (checkConditions.hidden === false)) {
        let validationError = null;

        //TODO Temporary fix for dealing with scripts that have incorrect type case on key. Need to update packages to support correct format.
        let attributeType = attribute.type ? attribute.type : attribute.Type ? attribute.Type : null;

        //Check if user has update rights to attribute.
        let attributeReadOnly = true;

        // if (props.schema.schema_type === 'automation') {
        //   if (props.userAccess[props.schemaName]) {
        //     //Automations screen loading.
        //     for (const attr_access of props.userAccess[props.schema.schema_name]) {
        //       if (props.userAccess[props.schema.schema_name].create) {
        //         attributeReadOnly = false
        //       }
        //     }
        //   } else
        //   {
        //     //schema not found, needs to be handled by backend permissions, default to allow access to attribute in UI.
        //     //TODO IN future we may want to change this logic to restrict this view, but really this needs to be done higher up on the actions button.
        //     attributeReadOnly = false;
        //   }
        // } else {
        if (props.userAccess[props.schemaName]) {
          if (props.userAccess[props.schemaName].create && (attribute.required || props.schema.schema_type === 'automation')) {
            //Any required attributes will be available if the user has the create permission.
            attributeReadOnly = false
          } else {
            for (const attr_access of props.userAccess[props.schemaName].attributes) {
              if (attr_access.attr_name === attribute.name && (props.userAccess[props.schemaName].create || props.userAccess[props.schemaName].update)) {
                attributeReadOnly = false
                break;
              }
            }
          }
        }
        else
        {
          //schema not found, needs to be handled by backend permissions, default to allow access to attribute in UI.
          attributeReadOnly = false;
        }
        // }

        switch (attributeType) {
          case 'checkbox':
            return (
              <Checkbox
                key={attribute.name}
                onChange={event => props.handleUserInput({field: attribute.name, value: event.detail.checked, validationError: validationError})}
                checked={getNestedValuePath(props.item, attribute.name)}
                disabled={attributeReadOnly}
              >
                {attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
              </Checkbox>
            )

          case 'multivalue-string':
            validationError = returnErrorMessage(attribute)
            return (
              <FormField
                key={attribute.name}
                label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <Textarea
                  onChange={event => props.handleUserInput({field: attribute.name, value:  event.detail.value === '' ? [] : event.detail.value.split('\n'), validationError: validationError})}
                  value={getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name).join('\n') : ''}
                  disabled={attributeReadOnly}
                />
              </FormField>
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
          case 'tag': {
            let tags = [];
            if (getNestedValuePath(props.item, attribute.name)) {
              let temptags = getNestedValuePath(props.item, attribute.name);
              tags = temptags.map((item, index) => {
                return {...item, existing: false}
              });
            }
            return (
              <Container
                key={attribute.name}
                header={
                  <Header
                    variant="h2"
                    description={attribute.long_desc}
                  >
                    {attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                  </Header>
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
                    undoPrompt:
                      "This tag will be removed upon saving changes",
                    loading:
                      "Loading tags that are associated with this resource",
                    keyHeader: "Key",
                    valueHeader: "Value",
                    optional: "optional",
                    keySuggestion: "Custom tag key",
                    valueSuggestion: "Custom tag value",
                    emptyTags:
                      "No tags associated with the resource.",
                    tooManyKeysSuggestion:
                      "You have more keys than can be displayed",
                    tooManyValuesSuggestion:
                      "You have more values than can be displayed",
                    keysSuggestionLoading: "Loading tag keys",
                    keysSuggestionError:
                      "Tag keys could not be retrieved",
                    valuesSuggestionLoading: "Loading tag values",
                    valuesSuggestionError:
                      "Tag values could not be retrieved",
                    emptyKeyError: "You must specify a tag key",
                    maxKeyCharLengthError:
                      "The maximum number of characters you can use in a tag key is 128.",
                    maxValueCharLengthError:
                      "The maximum number of characters you can use in a tag value is 256.",
                    duplicateKeyError:
                      "You must specify a unique tag key.",
                    invalidKeyError:
                      "Invalid key. Keys can only contain alphanumeric characters, spaces and any of the following: _.:/=+@-",
                    invalidValueError:
                      "Invalid value. Values can only contain alphanumeric characters, spaces and any of the following: _.:/=+@-",
                    awsPrefixError: "Cannot start with aws:",
                    tagLimit: availableTags =>
                      availableTags === 1
                        ? "You can add up to 1 more tag."
                        : "You can add up to " +
                        availableTags +
                        " more tags.",
                    tagLimitReached: tagLimit =>
                      tagLimit === 1
                        ? "You have reached the limit of 1 tag."
                        : "You have reached the limit of " +
                        tagLimit +
                        " tags.",
                    tagLimitExceeded: tagLimit =>
                      tagLimit === 1
                        ? "You have exceeded the limit of 1 tag."
                        : "You have exceeded the limit of " +
                        tagLimit +
                        " tags.",
                    enteredKeyLabel: key => 'Use "' + key + '"',
                    enteredValueLabel: value => 'Use "' + value + '"'
                  }}
                  tags={tags}
                  onChange={({detail}) => props.handleUserInput({
                    field: attribute.name,
                    value: detail.tags,
                    validationError: detail.valid ? null : 'invalid tags'
                  })}
                />
              </Container>
            )
          }
          case 'list': {
            validationError = returnErrorMessage(attribute)
            let options = [];
            let errorMessage = undefined;
            if ('listvalue' in attribute) {
              options = attribute.listvalue.split(',');
              options = options.map((item, index) => {
                return (
                  {label: item, value: item}
                )
              })
            } else if ('listValueAPI' in attribute && !isLoadingVL && attribute.listValueAPI in dataVL) {
              //Attributes value list is obtained from a dynamic API call.
              if (dataVL[attribute.listValueAPI].errorMessage !== undefined) {
                errorMessage = dataVL[attribute.listValueAPI].errorMessage
                return options;
              } else {
                options = dataVL[attribute.listValueAPI].values.map((item, index) => {
                  let tags = [];
                  for (const key in item) {
                    //Add value of child key to tags, if not the main key
                    if (key !== attribute.labelKey) {
                      tags.push(item[key])
                    }
                  }

                  return (
                    {label: item[attribute.labelKey], value: item[attribute.valueKey], tags: tags}

                  )
                });
              }
            }

            let value = getNestedValuePath(props.item, attribute.name)

            return (
              <FormField
                key={attribute.name}
                label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                description={attribute.long_desc}
                errorText={validationError}
              >
                {attribute.listMultiSelect
                  ?
                  <Multiselect
                    selectedOptions={value == null ? [] : value.map(item => {return {'value': item, 'label': item}})}
                    onChange={event => props.handleUserInput({
                      field: attribute.name,
                      value: event.detail.selectedOptions.map(item => {return item.value}),
                      validationError: validationError
                    })}
                    statusType={attribute.listValueAPI && isLoadingVL ? errorMessage ? "error" : "loading" : undefined}
                    loadingText={"Loading values..."}
                    errortext={errorMessage ? errorMessage : undefined}
                    options={options}
                    disabled={attributeReadOnly}
                    selectedAriaLabel={'Selected'}
                    filteringType="auto"
                    placeholder={value ? value.length == 0 ? "Select " + attribute.description : value.length + ' ' + attribute.description + ' selected' : "Select " + attribute.description}
                  />
                  :
                  <Grid
                    gridDefinition={[{ colspan: 10}, { colspan: 2 }]}
                  >
                    <Select
                      selectedOption={getNestedValuePath(props.item, attribute.name) ? {
                        label: getNestedValuePath(props.item, attribute.name),
                        value: getNestedValuePath(props.item, attribute.name)
                      } : null}
                      onChange={event => props.handleUserInput({
                        field: attribute.name,
                        value: event.detail.selectedOption.value,
                        validationError: validationError
                      })}
                      statusType={attribute.listValueAPI && isLoadingVL ? errorMessage ? "error" : "loading" : undefined}
                      loadingText={"Loading values..."}
                      errortext={errorMessage ? errorMessage : undefined}
                      options={options}
                      disabled={attributeReadOnly}
                      selectedAriaLabel={'Selected'}
                      placeholder={"Select " + attribute.description}
                    />
                    <Button iconName="close" variant="normal" disabled={attributeReadOnly} onClick={event => props.handleUserInput({
                      field: attribute.name,
                      value: ''
                    })}>Clear</Button>
                  </Grid>
                }
              </FormField>
            )
          }
          case 'relationship': {
            validationError = returnErrorMessage(attribute)
            let value = getRelationshipValue(allData, attribute, getNestedValuePath(props.item, attribute.name))
            let record = getRelationshipRecord(allData, attribute, getNestedValuePath(props.item, attribute.name))
            const relatedSchema = attribute.rel_entity;
            if (!props.schemas[relatedSchema]) {
              //Valid schema not found, display text.

              //TODO Need to handle this, the situation should not really happen.
            }

            return (

              <FormField
                key={attribute.name}
                label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                description={attribute.long_desc}
                errorText={validationError}
              >
                {attribute.listMultiSelect
                  ?
                  <Multiselect
                    selectedOptions={record == null ? [] : record.map(item => {return {'label': item[attribute.rel_display_attribute], 'value': item[attribute.rel_key]}})}
                    onChange={event => handleUserInput(attribute,
                      event.detail.selectedOptions.length != 0
                        ? event.detail.selectedOptions.find(valueItem => {return valueItem.value === '__system_all'}) // if All selected by user then override other selections and add all items.
                          ? getRelationshipSelect(attribute, props.item)
                            .filter(valueItem => {return valueItem.value != '__system_all'})  // remove __system_all from the list as only used to select all.
                            .map(valueItem => valueItem.value) // get all values to store in record, without labels and tages.
                          : event.detail.selectedOptions.map(valueItem => valueItem.value)
                        : [],
                      validationError
                    )}
                    loadingText={"Loading " + attribute.rel_entity + "s"}
                    statusType={isLoadingApps ? "loading" : undefined}
                    options={getRelationshipSelect(attribute, props.item)}
                    disabled={attributeReadOnly}
                    selectedAriaLabel={'selected'}
                    filteringType="auto"
                    placeholder={value.value ? value.value.length == 0 ? "Select " + attribute.description : value.value.length + ' ' + attribute.description + ' selected' : "Select " + attribute.description}
                  />
                  :
                  <Grid
                    gridDefinition={[{ colspan: 10}, { colspan: 2 }]}
                  >
                    <SpaceBetween
                      size="xxxs"
                      key={attribute.name}
                    >
                      <Select
                        selectedOption={value}
                        onChange={event => handleUserInput(attribute,
                          event.detail.selectedOption.value,
                          validationError
                        )}
                        loadingText={"Loading " + attribute.rel_entity + "s"}
                        statusType={value.status === 'loading' ? "loading" : undefined}
                        options={getRelationshipSelect(attribute, props.item)}
                        selectedAriaLabel={'selected'}
                        disabled={attributeReadOnly}
                        placeholder={"Choose " + attribute.description}
                      />
                      {(getNestedValuePath(props.item, attribute.name) && getNestedValuePath(props.item, attribute.name) !== '')
                        ?
                        !((record===null) || (attribute.listMultiSelect) || (attribute.listvalue && attribute.listvalue.includes(getNestedValuePath(props.item, attribute.name))))
                          ?
                          //TODO Implement way to provide this functionality with multiselect.
                          <RelatedRecordPopover key={attribute.name}
                                                item={record}
                                                schema={props.schemas[relatedSchema]}
                                                schemas={props.schemas}>
                            Related details
                          </RelatedRecordPopover>
                          :
                          undefined
                        :
                        undefined
                      }
                    </SpaceBetween>
                    <Button iconName="close" variant="normal" disabled={attributeReadOnly} onClick={event => props.handleUserInput({
                      field: attribute.name,
                      value: ''
                    })}>Clear</Button>
                  </Grid>
                }
              </FormField>
            )
          }
          case 'policy': {
            validationError = returnErrorMessage(attribute)
            let value = getNestedValuePath(props.item, attribute.name)

            return (
              getPolicy(props.schemas,attribute, value)
            )
          }
          case 'groups': {
            validationError = returnErrorMessage(attribute)
            let value = getNestedValuePath(props.item, attribute.name)
            //let record = getRelationshipRecord(attribute, getNestedValuePath(props.item, attribute.name))

            let options =[];
            let errorMessage = undefined;

            if ('listValueAPI' in attribute && !isLoadingVL && attribute.listValueAPI in dataVL) {
              //Attributes value list is obtained from a dynamic API call.
              if (dataVL[attribute.listValueAPI].errorMessage !== undefined) {
                errorMessage = dataVL[attribute.listValueAPI].errorMessage
                return options;
              } else {
                options = dataVL[attribute.listValueAPI].values.map((item) => {
                  return (
                    {label: item, value: item}

                  )
                });
              }
            }

            return (
              <FormField
                key={attribute.name}
                label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <Multiselect
                  selectedOptions={value == null ? [] : value.map(item => {return {label: item.group_name, value: item.group_name}})}
                  onChange={event => props.handleUserInput({
                    field: attribute.name,
                    value: event.detail.selectedOptions.map(item => {return {group_name: item.value}}),
                    validationError: validationError
                  })}
                  statusType={attribute.listValueAPI && isLoadingVL ? errorMessage ? "error" : "loading" : undefined}
                  loadingText={"Loading values..."}
                  errortext={errorMessage ? errorMessage : undefined}
                  options={options}
                  disabled={attributeReadOnly}
                  selectedAriaLabel={'Selected'}
                  filteringType="auto"
                  placeholder={value ? value.length == 0 ? "Select " + attribute.description : value.length + ' ' + attribute.description + ' selected' : "Select " + attribute.description}
                />
              </FormField>
            )
          }
          case 'policies': {
            validationError = returnErrorMessage(attribute)
            let value = getNestedValuePath(props.item, attribute.name)
            //let record = getRelationshipRecord(attribute, getNestedValuePath(props.item, attribute.name))

            let options = getRelationshipSelect(attribute, props.item);
            let resolvedOptions = false;

            let errorMessage = undefined;

            let selectedOptions = [];
            if (value) {
              resolvedOptions = options.length === 0 && value.length > 0;
              if (resolvedOptions) {
                selectedOptions = value.map(item => {
                  return {label: item.policy_id, value: item.policy_id}
                });
              } else {
                selectedOptions = options.filter(itemOption => {
                  for (const selectedOption of value) {
                    if (selectedOption.policy_id === itemOption.value) {
                      //Valid selection.
                      return true;
                    }
                  }
                  //Selection not valid.
                  return false;
                });
              }
            }

            return (
              <FormField
                key={attribute.name}
                label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <Multiselect
                  selectedOptions={selectedOptions}
                  disabled={attributeReadOnly}
                  onChange={event => handleUserInput(attribute,
                    event.detail.selectedOptions.length != 0
                      ? event.detail.selectedOptions.find(valueItem => {return valueItem.value === '__system_all'}) // if All selected by user then override other selections and add all items.
                        ? options
                          .filter(valueItem => {return valueItem.value != '__system_all'})  // remove __system_all from the list as only used to select all.
                          .map(valueItem => {return {policy_id: valueItem.value}}) // get all values to store in record, without labels and tags.
                        : event.detail.selectedOptions.map(valueItem => {return {policy_id: valueItem.value}})
                      : [],
                    validationError
                  )}
                  statusType={value ? resolvedOptions ? "loading" : undefined : undefined}
                  loadingText={"Loading values..."}
                  errortext={errorMessage ? errorMessage : undefined}
                  options={options}
                  selectedAriaLabel={'Selected'}
                  filteringType="auto"
                  placeholder={selectedOptions ? selectedOptions.length == 0 ? "Select " + attribute.description : selectedOptions.length + ' ' + attribute.description : "Select " + attribute.description}
                />
                {resolvedOptions ? <div><Spinner size="normal" /> Resolving IDs.. </div>: undefined}
              </FormField>
            )
          }
          case 'embedded_entity': {
            validationError = null
            let currentValue = getNestedValuePath(props.item, attribute.lookup)
            let embedded_value = getRelationshipValue(allData, attribute, currentValue)

            const embedded_relatedSchema = attribute.rel_entity;

            if (!props.schemas[embedded_relatedSchema]) {
              //Valid schema not found, display text.
              console.log(embedded_relatedSchema + ' not found in schemas.')
            }

            //check if this new embedded item has already been stored in the state, if not create it.
            if (!embeddedAttributes[attribute.name + currentValue] && embedded_value.value !== null) {

              let updateEmbeddedAttributes = embeddedAttributes;
              if (embedded_value.value != null) {
                //Remove any invalid items where name key is not defined. This should not be the case but possible with script packages where incorrectly written.
                embedded_value.value = embedded_value.value.filter((item) => {
                  return item.name !== undefined;
                });
                embedded_value.value = embedded_value.value.map((item, index) => {
                  //prepend the embedded_entity name to all attribute names in order to store them under a single key.
                  let appendedName = attribute.name + '.' + item.name;
                  if (item.__orig_name){
                    //Item has already been updated name.
                    return (
                      item
                    )
                  } else {
                    //Store original name of item.
                    item.__orig_name = item.name;
                    item.name = appendedName;
                    item.group = attribute.description;
                    return (
                      item
                    )
                  }
                });
              } else {
                embedded_value.value = [];
              }

              updateEmbeddedAttributes[attribute.name + currentValue] = {"schema_type": props.schema.schema_type,"attributes": embedded_value.value};
              setEmbeddedAttributes(updateEmbeddedAttributes);
            }

            let options = [];
            if ('listvalue' in attribute) {
              options = attribute.listvalue.split(',');
            }
            return (
              <SpaceBetween
                size="xxxs"
                key={attribute.name}
              >
                <AllAttributes
                  schema={embeddedAttributes[attribute.name + currentValue] ? embeddedAttributes[attribute.name + currentValue] : undefined}
                  schemaName={props.schemaName}
                  userAccess={props.userAccess}
                  schemas={props.schemas}
                  hideAudit={true}
                  item={props.item}
                  handleUserInput={props.handleUserInput}
                  handleUpdateValidationErrors={props.handleUpdateValidationErrors}/>
              </SpaceBetween>
            )
          }
          case 'date':
            validationError = returnErrorMessage(attribute)
            return (
              <FormField
                key={attribute.name}
                label={attribute.description ? <SpaceBetween direction='horizontal' size='xs'>{attribute.description}{displayHelpInfoLink(attribute)} </SpaceBetween> :<SpaceBetween direction='horizontal' size='xs'>{attribute.name}{displayHelpInfoLink(attribute)} </SpaceBetween>}
                description={attribute.long_desc}
                errorText={validationError}
              >
                <DatePicker
                  onChange={event => props.handleUserInput({field: attribute.name, value: event.detail.value, validationError: validationError})}
                  value={getNestedValuePath(props.item, attribute.name) ? getNestedValuePath(props.item, attribute.name) : ''}
                  openCalendarAriaLabel={selectedDate =>
                    "Choose Date" +
                    (selectedDate
                      ? `, selected date is ${selectedDate}`
                      : "")
                  }
                  nextMonthAriaLabel="Next month"
                  placeholder="YYY/MM/DD"
                  previousMonthAriaLabel="Previous month"
                  todayAriaLabel="Today"
                  disabled={attributeReadOnly}
                />
              </FormField>
            )
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
          let newValidationErrors = formValidationErrors.filter(item => {
            return item.name !== attribute.name;
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
      }
      return null;
    });

    return allAttributes;
  }

  function buildAttributeGroups(schema){

    let groups = [];

    for (let attributeIdx = 0; attributeIdx < schema.length; attributeIdx++){

      if (schema[attributeIdx].group){
        let obj = groups.find(o => o.name === schema[attributeIdx].group);
        if(!obj){
          groups.push({name: schema[attributeIdx].group, attributes: [schema[attributeIdx]]});
        } else {
          obj.attributes.push(schema[attributeIdx]);
        }
      } else {
        let obj = groups.find(o => o.name === constDefaultContainerName);
        if(!obj){
          groups.push({name: constDefaultContainerName, attributes: [schema[attributeIdx]]});
        } else {
          obj.attributes.push(schema[attributeIdx]);
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
    let allContainers = groupedAttrs.map((item, index) => {
      let group = buildAttributeUI(item.attributes)
      let allNull = true;

      for (const attr of group){
        if (attr)
          allNull = false
      }
      //Only show group container if at least one attribute is visible.
      if (!allNull) {
        return (
          <Container header={<Header variant="h2">{item.name}</Header>}>
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
