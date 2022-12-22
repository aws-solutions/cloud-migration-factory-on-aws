/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import User from "../actions/user";
import ImportOverview from '../components/import/ImportOverview.jsx';
import {capitalize, getChanges, validateValue} from '../resources/main.js';
import * as XLSX from "xlsx";

import { Auth } from "aws-amplify";

import {
  SpaceBetween,
  Icon,
  Container,
  Header,
  Button,
  FormField,
  Alert,
  Wizard,
  Link,
  ExpandableSection, ButtonDropdown, Select, Form, ProgressBar,
} from '@awsui/components-react';

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook.js";
import { useMFWaves } from "../actions/WavesHook.js";
import { useProgressModal } from "../actions/ProgressModalHook.js";
import IntakeFormTable from '../components/IntakeFormTable.jsx';
import { useModal } from '../actions/Modal.js';
import {useGetDatabases} from "../actions/DatabasesHook";
import {checkAttributeRequiredConditions, getRequiredAttributes, parsePUTResponseErrors} from "../resources/recordFunctions";
import {useCredentialManager} from "../actions/CredentialManagerHook";

const UserImport = (props) => {

  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }, { update: updateApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, { update: updateServers }] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, { update: updateWaves }] = useMFWaves();
  const [{ isLoading: isLoadingDatabases, data: dataDatabases, error: errorDatabases }, { update: updateDatabases }] = useGetDatabases();
  const [{ isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets }, { updateSecrets }] = useCredentialManager();

  const dataAll = {secret: {data: dataSecrets, isLoading: isLoadingSecrets, error: errorSecrets}, database: {data: dataDatabases, isLoading: isLoadingDatabases, error: errorDatabases}, server: {data: dataServers, isLoading: isLoadingServers, error: errorServers}, application: {data: dataApps, isLoading: isLoadingApps, error: errorApps}, wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}};

  //Modals
  const { show: showCommitProgress, hide: hideCommitProgress, setProgress: setImportProgress, RenderModal: CommitProgressModel } = useProgressModal()

  const { show: showNoCommitConfirmaton, hide: hideNoCommitConfirmaton, RenderModal: NoCommitModel } = useModal()

  const [selectedFile, setSelectedFile] = useState(null);
  const [sheetNames, setSheetNames] = useState(null);
  const [selectedSheet, setSelectedSheet] = useState(null);
  const [items, setItems] = useState([]);
  const [committing, setCommitting] = useState(false);
  const [committed, setCommitted] = useState(false);
  const [errors, setErrors] = useState(0);
  const [importProgressStatus, setImportProgressStatus] = useState({status: '', percentageComplete: 0});
  const [warnings, setWarnings] = useState(0);
  const [informational, setInformational] = useState(0);
  const [errorFile, setErrorFile] = useState([]);
  const [outputCommitErrors, setOutputCommitErrors] = useState([]);
  const [summary, setSummary] = useState({
    "entities" : {},
    "hasUpdates" : false
  });

  function handleNotification(notification)
  {
    return props.updateNotification('add', notification)
  }

  function updateUploadStatus(notification, message, numberRecords = 1){
    notification.status = message;
    notification.percentageComplete = notification.percentageComplete + (notification.increment * numberRecords)
    handleNotification({
      id: notification.id,
      type: 'info',
      loading: true,
      dismissible: false,
      content: <ProgressBar
        label={"Importing file '" + notification.importName + "' ..."}
        value={notification.percentageComplete}
        additionalInfo={notification.status}
        variant="flash"
      />
    });
    setImportProgressStatus(notification);
  }

  function updateRelatedItemAttributes(newItem, new_item_schema_name, related_items, related_schema_name){

    if (!props.schema[new_item_schema_name]){
      console.debug('Invalid new_item_schema_name' + new_item_schema_name)
      return;
    }

    if (!props.schema[related_schema_name]){
      console.debug('Invalid related_schema_name' + related_schema_name)
      return;
    }

    if (!related_items || related_items.length === 0){
      console.debug('No related_items to update in items: ' + related_schema_name)
      return;
    }

    if (!newItem){
      console.debug('No new item to reference.')
      return;
    }

    //get all relationship attributes for related items' schema.
    const rel_attributes = props.schema[related_schema_name].attributes.filter(attr => {return attr.type === 'relationship' && attr.rel_entity === new_item_schema_name})

    //Update items with new items ids for created item.
    for (let itemIdx = 0; itemIdx < related_items.length; itemIdx++)
    {
      for (const attr of rel_attributes){
        if (attr.listMultiSelect){
          //Deal with multiple related items. This only currently supports names not IDs.
          if (related_items[itemIdx]["__" + attr.name] && (!related_items[itemIdx][attr.name] || related_items[itemIdx][attr.name].includes('tbc'))) {
            let relatedNamesIDs = related_items[itemIdx][attr.name];
            let relatedNames = related_items[itemIdx]["__" + attr.name];

            //For each related name update the tbc values with new items ID.
            for (let relNameIdx = 0; relNameIdx < relatedNamesIDs.length; relNameIdx++) {
              if (relatedNamesIDs[relNameIdx] === 'tbc') {
                //check if this is a record to update.
                if (relatedNames[relNameIdx].toLowerCase() === newItem[attr.rel_display_attribute].toLowerCase()) {
                  relatedNamesIDs[relNameIdx] = newItem[attr.rel_key];
                }
              }
            }

            related_items[itemIdx][attr.name] = relatedNamesIDs;

          }
        } else {
          //Update single select items.
          if ((!related_items[itemIdx][attr.name] || related_items[itemIdx][attr.name] === 'tbc') && related_items[itemIdx]["__" + attr.name]) {
            if (related_items[itemIdx]["__" + attr.name].toLowerCase() === newItem[attr.rel_display_attribute].toLowerCase()) {
              related_items[itemIdx][attr.rel_key] = newItem[attr.rel_key];
              delete related_items[itemIdx]["__" + attr.name];
            }
          }
        }
      }
    }
  }

  async function commitItems(schema, items, dataImport, action, notification) {

    const schema_shortname = schema === 'application' ? 'app' : schema;

    const start = Date.now();

    if (!items && items.length === 0 ){
      //Nothing to be done as items is empty.
      const millis = Date.now() - start;
      console.debug(`seconds elapsed = ${Math.floor(millis / 1000)}`);
      return;
    }

    let loutputCommit = [];
    let commitItems = [];
    let currentItem = null;
    const session = await Auth.currentSession();
    const apiUser = new User(session);

    for (let itemIdx = 0; itemIdx < items.length; itemIdx++)
    {
      let newItem = Object.assign({}, items[itemIdx]);

      currentItem = items[itemIdx];

      //Remove any calculated keys from object.
      for (const key in newItem){
        if (key.startsWith('__')){
          delete newItem[key]
        }
      }

      commitItems.push(currentItem);

      try {
        if (action === 'Update') {
          let item_id = newItem[schema_shortname + '_id'];
          delete newItem[schema_shortname + '_id'];
          const result = await apiUser.putItem(item_id, newItem, schema_shortname);
          updateUploadStatus(notification, action + " " + schema + " records...");
        }

      } catch (e) {
        updateUploadStatus(notification, action + " " + schema + " records...");
        console.error(e);
        if ('response' in e && 'data' in e.response) {
          if (typeof e.response.data === 'object' && 'cause' in e.response.data){
            loutputCommit.push({
              itemType: schema,
              error: currentItem[schema_shortname + '_name'] ? currentItem[schema_shortname + '_name'] + " - " + e.response.data.cause : e.response.data.cause,
              item: currentItem
            });
          } else {
            loutputCommit.push({
              itemType: schema,
              error: currentItem[schema_shortname + '_name'] ? currentItem[schema_shortname + '_name'] + " - " + e.response.data : e.response.data,
              item: currentItem
            });
          }
        } else{
          loutputCommit.push({itemType: schema, error: currentItem[schema_shortname + '_name'] ? currentItem[schema_shortname + '_name'] + ' - Unknown error occurred' : 'Unknown error occurred', item: currentItem})
        }
      }

    }

    try {
      if (action === 'Create') {
        for (const item in commitItems){
          delete item[schema_shortname + '_id'];
        }

        console.debug("Starting bulk post")
        const result = await apiUser.postItems(commitItems, schema_shortname);
        updateUploadStatus(notification, "Updating any related records with new " + schema + " IDs...", commitItems.length/2);
        console.debug("Bulk post complete")

        if (result['newItems']) {
          console.debug("Updating related items")
          for (const item of result['newItems']){

            for (const updateSchema in dataImport)
            {
              //TODO add logic to determine if the updateSchema is related to current schema by any attributes
              // and then only update those that are, for the moment it will validate all.
              updateRelatedItemAttributes(item, schema, dataImport[updateSchema].Create, updateSchema);
              updateRelatedItemAttributes(item, schema, dataImport[updateSchema].Update, updateSchema);
            }
          }

          updateUploadStatus(notification, "Updating any related records with new " + schema + " IDs...", commitItems.length/2);
        }

        if (result['errors']) {
          console.debug("PUT " + schema + " errors");
          console.debug(result['errors']);
          let errorsReturned = parsePUTResponseErrors(result['errors']);
          loutputCommit.push({
            'itemType': schema,
            'error': 'Create failed',
            'item': errorsReturned
          });
        }
      }

    } catch (e) {
      console.debug(e);
      if(e) {
        loutputCommit.push({
          itemType: schema + ' ' + action,
          error: 'Internal API error - Contact support',
          item: JSON.stringify(e)
        });
      } else {
        loutputCommit.push({
          itemType: schema + ' ' + action,
          error: 'Internal API error - Contact support',
          item: {}
        });
      }

      updateUploadStatus(notification, "Error uploading records of type :" + schema, commitItems.length);
    }

    const millis = Date.now() - start;
    console.debug(`seconds elapsed = ${Math.floor(millis / 1000)}`);

    if (loutputCommit.length > 0) {
      let newCommitError = outputCommitErrors;
      newCommitError.push(...loutputCommit)
      setOutputCommitErrors(newCommitError);
    }
  }

  function readCSVFile(file){
    if (typeof (FileReader) !== "undefined") {
      var reader = new FileReader();

      return new Promise((resolve, reject) => {
        reader.onerror = () => {
          reader.abort();
          reject(new DOMException("Problem parsing input file."));
        };

        reader.onload = () => {
          resolve(reader.result);
        };
        reader.readAsText(file);
      });
    } else {
      setErrorFile(["This browser does not support HTML5, it is not possible to import files."])
    }
  }

  function readXLSXFile(file){
    if (typeof (FileReader) !== "undefined") {
      var reader = new FileReader();

      return new Promise((resolve, reject) => {
        reader.onerror = () => {
          reader.abort();
          reject(new DOMException("Problem parsing input file."));
        };

        reader.onload = () => {
          resolve(reader.result);
        };
        reader.readAsArrayBuffer(file);
      });
    } else {
      setErrorFile(["This browser does not support HTML5, it is not possible to import files."])
    }
  }

  async function handleDownloadTemplate(e){
    e.preventDefault();

    let action = e.detail.id;

    switch (action) {
      case 'download_req':{
        exportTemplate();
        break;
      }
      case 'download_all':{
        exportAllTemplate();
        break;
      }
    }

  }

  function exportTemplate(){

    var ws_data = {}

    let attributes = getRequiredAttributesAllSchemas(props.schema); // get all required attributes from all schemas

    let headers = {}
    for (const attr_idx in attributes){
      if (attributes[attr_idx].type === "relationship") {
        headers[attributes[attr_idx].rel_display_attribute] = attributes[attr_idx].sample_data_intake ? attributes[attr_idx].sample_data_intake : "";
      } else {
        headers[attributes[attr_idx].name] = attributes[attr_idx].sample_data_intake ? attributes[attr_idx].sample_data_intake : "";
      }
    }
    const json_output = [headers] // Create single item array with empty values to populate headers fdr intake form.

    var range = { s: { c: 0, r: 0 }, e: { c: attributes.length, r: 1 } }; // set worksheet cell range
    ws_data['!ref'] = XLSX.utils.encode_range(range);

    var wb = XLSX.utils.book_new(); // create new workbook
    wb.SheetNames.push('mf_intake'); // create new worksheet
    wb.Sheets['mf_intake'] = XLSX.utils.json_to_sheet(json_output); // load headers array into worksheet

    XLSX.writeFile(wb, "cmf-intake-form-req.xlsx") // export to user

    console.log("CMF intake template exported.")
  }

  function exportAllTemplate(){

    var ws_data = {}

    let attributes = getAllAttributes(props.schema); // get all required attributes from all schemas

    let headers = {}
    for (const attr_idx in attributes){
      if (attributes[attr_idx].type === "relationship") {
        headers['[' + attributes[attr_idx].schema + ']'+ attributes[attr_idx].rel_display_attribute] = attributes[attr_idx].sample_data_intake ? attributes[attr_idx].sample_data_intake : "";
      } else {
        headers['[' + attributes[attr_idx].schema + ']'+ attributes[attr_idx].name] = attributes[attr_idx].sample_data_intake ? attributes[attr_idx].sample_data_intake : "";
      }
    }

    const json_output = [headers] // Create single item array with empty values to populate headers fdr intake form.

    var range = { s: { c: 0, r: 0 }, e: { c: attributes.length, r: 1 } }; // set worksheet cell range
    ws_data['!ref'] = XLSX.utils.encode_range(range);

    var wb = XLSX.utils.book_new(); // create new workbook
    wb.SheetNames.push('mf_intake'); // create new worksheet
    wb.Sheets['mf_intake'] = XLSX.utils.json_to_sheet(json_output); // load headers array into worksheet

    XLSX.writeFile(wb, "cmf-intake-form-all.xlsx") // export to user

    console.log("CMF intake template exported.")
  }

  function getRequiredAttributesAllSchemas(schemas){
    let required_attributes = [];

    if (schemas) {
      for (const schema_name in schemas) {
        if (schemas[schema_name].schema_type === 'user') {
          let req_attributes = getRequiredAttributes(schemas[schema_name]);

          if (req_attributes.length > 0) {
            required_attributes = required_attributes.concat(req_attributes);
          }
        }
      }
    }

    return required_attributes;

  }

  function getAllAttributes(schemas){
    let required_attributes = [];

    if (schemas) {
      for (const schema_name in schemas) {
        if (schemas[schema_name].schema_type === 'user') {
          let req_attributes = schemas[schema_name].attributes.filter(attr => {
            if (!attr.hidden) {
              attr.schema = schemas[schema_name].schema_name === 'app' ? 'application' : schemas[schema_name].schema_name;
              return attr;
            }
          });

          if (req_attributes.length > 0) {
            required_attributes = required_attributes.concat(req_attributes);
          }
        }
      }
    }

    return required_attributes;

  }

  function performDataValidation (csvData){
    let objArray = [];
    let attributeMappings = [];
    let schemas = [];

    for (var itemIdx = 0; itemIdx < csvData.length; itemIdx++) {
      //let item = {};
      let itemErrors = [];
      let itemWarnings = [];
      let itemInformational = [];
      for (const key in csvData[itemIdx]) {
        let attr = [];
        let schema_name = null;
        if (key.startsWith('[')) {
          //Schema name provided in key.
          let keySplit = key.split(']');
          if (keySplit.length > 1) {
            if (keySplit[0] !== '' && keySplit[1] !== '') {
              schema_name = keySplit[0].substring(1);
              attr = getFindAttribute(keySplit[1], props.schema, schema_name);
            } else {
              //check with full key as not in correct format.
              //Key does not provide schema hint.
              attr = getFindAttribute(key, props.schema);
            }
          } else {
            //check with full key as not in correct format.
            //Key does not provide schema hint.
            attr = getFindAttribute(key, props.schema);
          }
        }else{
          //Key does not provide schema hint.
          attr = getFindAttribute(key, props.schema);
        }

        if (attr.length > 1) {
          itemInformational.push({attribute: key, error: 'Ambiguous attribute name provided. It is found in multiple schemas ['+ attr.map(item => {return item.schema_name}).join(', ') +']. Import will map data to schemas as required based on record types.'});
        }

        for (const foundAttr of attr){
          foundAttr['import_raw_header'] = key;

          let filterMappings = attributeMappings.filter(item => {
            if (item['import_raw_header'] === key) {
              if (item['schema_name'] === foundAttr.schema_name){
                return true;
              } else {
                return false;
              }

            } else {
              return false;
            }
          });

          if (filterMappings.length === 0){
            attributeMappings.push(foundAttr);
          }

          //Add schema names to list for quick lookup later.
          if (foundAttr.attribute && !schemas.includes(foundAttr.schema_name)){
            schemas.push(foundAttr.schema_name);
          }

          let msgError = performValueValidation(foundAttr, csvData[itemIdx][key])
          if (msgError){
            if (msgError.type === 'error') {
              itemErrors.push({attribute: key, error: msgError.message});
            } else if (msgError.type === 'warning') {
              itemWarnings.push({attribute: key, error: msgError.message});
            }
          }
        }

        //}
      }

      csvData[itemIdx]['__import_row'] = itemIdx;
      csvData[itemIdx]['__validation'] = {};
      csvData[itemIdx]['__validation']['errors'] = itemErrors;
      csvData[itemIdx]['__validation']['warnings'] = itemWarnings;
      csvData[itemIdx]['__validation']['informational'] = itemInformational
    }

    return {'data': csvData, 'attributeMappings': attributeMappings, 'schema_names': schemas};
  }

  async function handleUploadChange(e) {
    e.preventDefault();

    //Reset for new upload.
    setErrorFile([]);
    setErrors(0);
    setWarnings(0);
    setInformational(0);
    setItems([]);
    setSelectedFile(null);
    setOutputCommitErrors([]);
    setCommitted(false);
    setCommitting(false);
    setSelectedSheet(null);
    setSheetNames(null);

    setSelectedFile(e.target.files[0])

    let dataJson = []
    if (e.target.files[0].type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
      let data = await readXLSXFile(e.target.files[0])
      let workbook = XLSX.read(data)
      let sheet = workbook.Sheets[workbook.SheetNames[0]];
      //Set first sheet as default import source.
      setSelectedSheet(workbook.SheetNames[0]);
      if (workbook.SheetNames.length > 1) {
        setSheetNames(workbook.SheetNames);
        setSelectedSheet(workbook.SheetNames[0]);
      }
    } else {
      //Supported format of file.
    }
  }

  function getSchemaAttribute(attributeName, schema) {
    let attr = null;

    for (var row = 0; row < schema.attributes.length; row++) {
      if (schema.attributes[row].name === attributeName){
        attr = schema.attributes[row];
        break;
      }
    }

    return attr;
  }

  function getSchemaRelationshipAttributes(attributeName, schema) {
    let attributes = [];

    for (var row = 0; row < schema.attributes.length; row++) {
      if (schema.attributes[row].type === 'relationship'){
        if (schema.attributes[row].rel_display_attribute === attributeName){
          //We've got a live one!!
          attributes.push(schema.attributes[row]);
          break;
        }
      }
    }

    return attributes.length > 0 ? attributes : null;
  }

  function getFindAttribute(attributeName, schemas, schema_name = null) {
    let attr = null;
    let attrList = [];

    if (schemas) {

      if (schema_name) {
        //Schema name provided.
        if(!schemas[schema_name]) {
          attrList.push({
            'attribute': attr,
            'schema_name': null,
            'lookup_attribute_name': attributeName,
            'lookup_schema_name': schema_name
          });  //Schema_name not valid.
        } else {
          if (schemas[schema_name].schema_type === 'user') {
            attr = getSchemaAttribute(attributeName, schemas[schema_name]);
            if (attr) {
              attrList.push({
                'attribute': attr,
                'schema_name': schema_name,
                'lookup_attribute_name': attributeName,
                'lookup_schema_name': schema_name
              });
            } else
              attrList.push({
                'attribute': attr,
                'schema_name': null,
                'lookup_attribute_name': attributeName,
                'lookup_schema_name': schema_name
              });
          } else {
            attrList.push({
              'attribute': attr,
              'schema_name': null,
              'lookup_attribute_name': attributeName,
              'lookup_schema_name': schema_name
            });
          }
        }
      } else {

        //Schema name not provided, search all schemas.
        for (const schema_name in schemas) {
          if (schemas[schema_name].schema_type === 'user') {
            let lAttr = null;
            lAttr = getSchemaAttribute(attributeName, schemas[schema_name]);
            if (lAttr) {
              attrList.push({
                'attribute': lAttr,
                'schema_name': schema_name,
                'lookup_attribute_name': attributeName,
                'lookup_schema_name': schema_name
              });
            }

            let lRelatedAttrs = null;
            lRelatedAttrs = getSchemaRelationshipAttributes(attributeName, schemas[schema_name]);
            if (lRelatedAttrs) {
              for (const lRelatedAttr of lRelatedAttrs){
                attrList.push({
                  'attribute': lRelatedAttr,
                  'schema_name': schema_name,
                  'lookup_attribute_name': attributeName,
                  'lookup_schema_name': schema_name
                });
              }
            }
          }
        }
      }
    }

    //Not found set default response.
    if (attrList.length === 0) {
      attrList.push({
        'attribute': null,
        'schema_name': null,
        'lookup_attribute_name': attributeName,
        'lookup_schema_name': schema_name
      });
    }

    return attrList;

  }

  //Function checks the item passed has valid data as per the schema requirements.
  function checkValidItemCreate(item, schema){
    const requiredAttributes = getRequiredAttributes(schema, true);

    let invalidAttributes = [];

    for (const attr of requiredAttributes){
      if (attr.required){
        //Attribute is required.
        if (attr.name in item){
          if (!(item[attr.name] !== '' && item[attr.name] !== undefined && item[attr.name] !== null)){
            invalidAttributes.push(attr);
          }
        } else {
          //key not in item, missing required attribute.
          invalidAttributes.push(attr);
        }
      } else if ('conditions' in attr){
        if (checkAttributeRequiredConditions(item,attr.conditions).required){
          if (!(item[attr.name] !== '' && item[attr.name] !== undefined && item[attr.name] !== null)){
            invalidAttributes.push(attr);
          }
        }
      }
    }

    if (invalidAttributes.length > 0) {
      return invalidAttributes
    } else {
      return null;
    }
  }



  function getSummary(items) {

    let distinct = {};

    let result = {
      "entities": {},
      "hasUpdates" : false
    };

    for (const schema_name in props.schema){
      if (props.schema[schema_name].schema_type === 'user'){
        let temp_schema_name = schema_name === 'application' ? 'app' : schema_name;
        let schema_reference = props.schema[schema_name].friendly_name ? props.schema[schema_name].friendly_name : capitalize(schema_name);
        result['entities'][schema_name] = {
          "Create": [],
          "Update": [],
          "NoChange": []

        };

        //Populate distinct records from data import for each schema, referenced by _name or _id attribute.
        const tempDistinct = [...new Set(items.data.map(x => {
          if (temp_schema_name + '_name' in x){
            return x[temp_schema_name + '_name'];
          } else if ('[' + schema_name + ']' + temp_schema_name + '_name' in x) {
            return x['[' + schema_name + ']' + temp_schema_name + '_name'];
          } else if (temp_schema_name + '_id' in x){
            return x[temp_schema_name + '_id'];
          } else if ('[' + schema_name + ']' + temp_schema_name + '_id' in x) {
            return x['[' + schema_name + ']' + temp_schema_name + '_id'];
          }
        }))];

        distinct[schema_name] = tempDistinct.filter(item => {return item !== undefined && item !== ''});

        if (distinct[schema_name] === undefined) { //If nothing returned then continue to next schema.
          distinct[schema_name] = []
          continue;
        }

        let schemaAttributes = [];

        schemaAttributes = items.attributeMappings.filter(attr => {
          return attr.schema_name === schema_name;
        });

        let keyAttribute = schemaAttributes.find(attr => { //Get schema key attribute.
          if (attr.attribute.name === temp_schema_name + '_name'){ //check if _name key present in attributes
            return attr;
          } else if (attr.attribute.name === temp_schema_name + '_id'){//if no _name then check if _id key present in attributes
            return attr;
          }
        });

        for (let itemIdx = 0; itemIdx < distinct[schema_name].length; itemIdx++) {

          if (distinct[schema_name][itemIdx] === undefined){
            continue
          }

          if (distinct[schema_name][itemIdx] !== undefined && distinct[schema_name][itemIdx].toLowerCase() !== '') { //Verify that the key has a value, if not ignore.

            let itemOrMismatch = isMismatchedItem(items.data, schemaAttributes, keyAttribute.import_raw_header, distinct[schema_name][itemIdx].toLowerCase());
            if (itemOrMismatch !== null) {
              let importrow = items.data.find(item => {
                  if (item[keyAttribute.import_raw_header]) {
                    if (item[keyAttribute.import_raw_header].toLowerCase() === distinct[schema_name][itemIdx].toLowerCase()) {
                      return true;
                    }
                  } else {
                    return false;
                  }
                }
              )

              let importApp = {};
              importApp[keyAttribute.attribute.name] = distinct[schema_name][itemIdx];

              for (const attr of schemaAttributes) {
                if (importrow[attr.import_raw_header] && attr.attribute.type !== 'relationship') {
                  switch (attr.attribute.type) {
                    case 'list': {
                      if (attr.attribute.listMultiSelect) {
                        //Build array for multiselect attribute.
                        let formattedText = importrow[attr.import_raw_header];
                        formattedText = formattedText.split(';');

                        importApp[attr.attribute.name] = formattedText;
                      } else {
                        importApp[attr.attribute.name] = importrow[attr.import_raw_header];
                      }
                      break;
                    }
                    case 'multivalue-string': {
                      let formattedText = importrow[attr.import_raw_header];
                      formattedText = formattedText.split(';');

                      importApp[attr.attribute.name] = formattedText;
                      break;
                    }
                    case 'tag': {
                      let formattedTags = importrow[attr.import_raw_header];

                      formattedTags = formattedTags.split(';');
                      formattedTags = formattedTags.map(tag => {
                        let key_value = tag.split('=');
                        return {key: key_value[0], value: key_value[1]}
                      });

                      importApp[attr.attribute.name] = formattedTags;
                      break;
                    }
                    default: {
                      importApp[attr.attribute.name] = importrow[attr.import_raw_header];
                    }
                  }
                } else if (attr.attribute.type === 'relationship') {
                  let relationshipValueType = ''

                  //Determine how the import has provided the relationship, by name/display value or the ID of the related record.
                  if (attr.import_raw_header === ('[' + schema_name + ']' + attr.attribute.rel_display_attribute).toLowerCase()){
                    relationshipValueType = 'name';
                  } else if (attr.import_raw_header.toLowerCase() === attr.attribute.rel_display_attribute.toLowerCase()) {
                    relationshipValueType = 'name';
                  } else if (attr.import_raw_header.toLowerCase() === attr.attribute.name.toLowerCase() && attr.attribute.listMultiSelect) {
                    relationshipValueType = 'name';
                  } else if (attr.import_raw_header.toLowerCase() === ('[' + schema_name + ']' + attr.attribute.name).toLowerCase() && attr.attribute.listMultiSelect) {
                    relationshipValueType = 'name';
                  } else if (attr.import_raw_header.toLowerCase() === attr.attribute.name.toLowerCase()){
                    relationshipValueType = 'id';
                  } else if (attr.import_raw_header.toLowerCase() === ('[' + schema_name + ']' + attr.attribute.name).toLowerCase()) {
                    relationshipValueType = 'id';
                  }

                  if (relationshipValueType === 'name') {
                    //relationship value is a name not ID, perform search to see if this item exists.
                    if (attr.attribute.listMultiSelect) {
                      //Multiselect attribute.
                      const valuesRaw = importrow[attr.import_raw_header].split(";");
                      let valuesID = [];
                      let valuesDisplay = [];

                      if (valuesRaw.length > 0){
                        for (const itemValue of valuesRaw){
                          let relatedItem = dataAll[attr.attribute.rel_entity].data.find(item => {
                              if (item[attr.attribute.rel_display_attribute] && itemValue) {
                                if (item[attr.attribute.rel_display_attribute].toLowerCase() === itemValue.toLowerCase()) {
                                  return true;
                                }
                              }
                            }
                          )
                          if (relatedItem) {
                            valuesID.push(relatedItem[attr.attribute.rel_key]);
                            valuesDisplay.push(relatedItem[attr.attribute.rel_display_attribute]);
                          } else {
                            if (importrow[attr.import_raw_header] !== '' && importrow[attr.import_raw_header] !== undefined) {
                              //Item name does not exist so will be created if provided.
                              valuesID.push('tbc');
                              valuesDisplay.push(itemValue);
                            }
                          }
                        }

                        importApp[attr.attribute.name] = valuesID;
                        importApp['__' + attr.attribute.name] = valuesDisplay;

                      } else {
                        //No values provided.
                        importApp[attr.attribute.name] = [];
                      }

                    } else {
                      //Not a multiselect relational value.
                      let relatedItem = dataAll[attr.attribute.rel_entity].data.find(item => {
                          if (item[attr.attribute.rel_display_attribute] && importrow[attr.import_raw_header]) {
                            if (item[attr.attribute.rel_display_attribute].toLowerCase() === importrow[attr.import_raw_header].toLowerCase()) {
                              return true;
                            }
                          }
                        }
                      )
                      if (relatedItem) {
                        importApp[attr.attribute.name] = relatedItem[attr.attribute.rel_key];
                      } else {
                        if (importrow[attr.import_raw_header] !== '' && importrow[attr.import_raw_header] !== undefined) {
                          //Item name does not exist, so will be created if provided. Setting ID to 'tbc', once the related
                          // record is created then this will be updated in the commit with the new records' ID.
                          importApp[attr.attribute.name] = 'tbc'
                          importApp['__' + attr.attribute.name] = importrow[attr.import_raw_header];
                        }
                      }
                    }
                  } else if (relationshipValueType === 'id') {
                    //related attribute display value not present in import, ID has been provided.

                    if (importrow[attr.import_raw_header] !== '' && importrow[attr.import_raw_header] !== undefined) {
                      //ID is being provided instead of display value.
                      if (attr.attribute.listMultiSelect) {
                        importApp[attr.attribute.name] = importrow[attr.import_raw_header].split(";");
                      } else {
                        importApp[attr.attribute.name] = importrow[attr.import_raw_header];
                      }
                    }
                  } else{
                    console.log('UNHANDLED: relationship type not found.')
                  }
                }
              }

              if (dataAll[schema_name].data.some(item => item[keyAttribute.attribute.name].toLowerCase() === distinct[schema_name][itemIdx].toLowerCase())) {
                //If [schema]_name is being imported then we get the item by name and then use the id from it.
                let item_id = -1;
                let item_name = null;
                let item = dataAll[schema_name].data.find(item => {
                    if (item[keyAttribute.attribute.name]) {
                      if (item[keyAttribute.attribute.name].toLowerCase() === distinct[schema_name][itemIdx].toLowerCase()) {
                        return true;
                      }
                    }
                  }
                )

                if (item) {
                  item_id = item[temp_schema_name + '_id'];
                  item_name = item[temp_schema_name + '_name'];
                }

                let changesItemWithCalc = getChanges(importApp, dataAll[schema_name].data, keyAttribute.attribute.name, true)
                let changesItem = getChanges(importApp, dataAll[schema_name].data, keyAttribute.attribute.name, false)

                if (changesItem) {
                  //Create a temporary item that has all updates and validate.
                  let newItem = Object.assign({}, item);

                  //Update temp object with changes.
                  const keys = Object.keys(changesItem);
                  for (let key of keys){
                    newItem[key] = changesItem[key];
                  }
                  let check = checkValidItemCreate(newItem, props.schema[schema_name])

                  //Add appid to item.
                  if (check === null) {
                    changesItemWithCalc[temp_schema_name + '_id'] = item_id;
                    changesItemWithCalc[temp_schema_name + '_name'] = item_name;
                    result.entities[schema_name].Update.push(changesItemWithCalc);
                    result.hasUpdates = true;
                  } else {
                    //Errors found on requirements check, log errors against data row.

                    let importRow = items.data.find(item => {
                        if (item[keyAttribute.import_raw_header]) {
                          if (item[keyAttribute.import_raw_header].toLowerCase() === distinct[schema_name][itemIdx].toLowerCase()) {
                            return true;
                          }
                        }
                      }
                    )

                    for (const error of check) {
                      importRow['__validation']['errors'].push({
                        attribute: error.name,
                        error: "Missing required " + schema_name + " attribute: " + error.name
                      });
                    }
                  }
                } else {
                  let NoChangeItem = {};
                  NoChangeItem[temp_schema_name + '_name'] = item_name
                  result.entities[schema_name].NoChange.push(NoChangeItem);
                }

              } else {
                //1. Get required schema attributes for this entity type.
                //2. check returned required attributes against the list of attributes supplied in attributeMappings.
                //3. if there are missing required attributes add an error to the record/row.
                //4. recheck that values have been provided for all required attributes. Add errors to record/row if they do not have values.
                //5. Do not add to Create array.
                // Note: this check might need to be done with updates to once the ability to clear values is implemented.

                //Check the entity is valid, i.e. it has the user key defined, if not, do not add as this is not something the user is looking to create.

                if (keyAttribute.attribute.name in importApp && importApp[keyAttribute.attribute.name] !== '') {
                  let check = checkValidItemCreate(importApp, props.schema[schema_name])

                  if (check === null) {
                    //No errors on item add to create array.
                    result.entities[schema_name].Create.push(importApp);
                    result.hasUpdates = true;
                  } else {
                    //Errors found on requirements check, log errors against data row.

                    let importRow = items.data.find(item => {
                        if (item[keyAttribute.import_raw_header]) {
                          if (item[keyAttribute.import_raw_header].toLowerCase() === distinct[schema_name][itemIdx].toLowerCase()) {
                            return true;
                          }
                        }
                      }
                    )

                    for (const error of check) {
                      importRow['__validation']['errors'].push({
                        attribute: error.name,
                        error: "Missing required " + schema_name + " attribute: " + error.name
                      });
                    }
                  }
                } else {
                  //Name not provided.
                  console.log('_name not provided.')

                }
              }
            } else {
              //Not an issue as validation errors would have been recorded.
            }
          }
        }
      }
    }

    //Pass attribute mappings back as needed to build table columns and config.
    result.attributeMappings = items.attributeMappings;

    return result;
  }

  function isMismatchedItem(dataArray, checkAttributes, key, value){

    let misMatchFound = false;
    let finalItem = null;

    let arrayItems = dataArray.filter(item => {
        if (item[key]) {
          if (item[key].toLowerCase() === value.toLowerCase()) {
            return true;
          }
        } else {
          return false;
        }
      }
    )

    if (arrayItems.length > 1){
      //Multiple entries for same item, need to check that attribute values are the same for all.
      finalItem = arrayItems[0]; //set to first element as if not mismatched we with return this record.
      for (const attr of checkAttributes){
        //For each attribute in this import for the same schema check that it is consistent.
        let distinctValue = [...new Set(arrayItems.map(x => {
          if (attr.attribute.type === 'relationship'){
            return x[attr.attribute.rel_display_attribute]
          } else {
            return x[attr.attribute.name]
          }
        }))];

        if (distinctValue.length > 1) {
          //Problem found, update validation for all items with this item value.
          for (let itemValue in arrayItems){
            arrayItems[itemValue].__validation.errors.push({attribute: attr.attribute.name, error: attr.attribute.description + " cannot be different for the same " + attr.schema_name + "."})
            misMatchFound = true;
          }
        }
      }

    } else {
      //Only a single entry with this item no need to check.
      finalItem = arrayItems[0];
      misMatchFound = false;
    }

    if (misMatchFound) {
      return null;
    } else {
      return finalItem;
    }

  }

  async function handleModalClose(e) {
    e.preventDefault();

    hideNoCommitConfirmaton();

  }

  async function handleCancelClick(e) {
    e.preventDefault();

    //Reset for new upload.
    setErrorFile([]);
    setErrors(0);
    setItems([]);
    setSelectedFile(null);
    setOutputCommitErrors([]);
    setCommitted(false);
    setCommitting(false);
    setSelectedSheet(null);
    setSheetNames(null);

  }


  function countUpdates(entities){
    let totalUpdates = 0;

    for (const entity in entities){
      totalUpdates += entities[entity].Create.length;
      totalUpdates += entities[entity].Update.length;
    }

    return totalUpdates;
  }

  async function handleUploadClick(e) {
    e.preventDefault();

    if(!summary.hasUpdates){
      showNoCommitConfirmaton()
      return;
    }

    let importName = selectedFile.name;

    if (selectedSheet) {
      importName = selectedFile.name + " [" + selectedSheet + "]"
    }

    let status = {id: null, increment: 1, percentageComplete: 0, status: "Starting upload...", 'importName': importName}
    status.id = handleNotification({
      type: 'info',
      loading: true,
      dismissible: false,
      content: <ProgressBar
        label={"Importing file " + importName + " ..."}
        value={0}
        additionalInfo="Starting upload..."
        variant="flash"
      />
    });

    setCommitting(true);

    let totalUpdates = countUpdates(summary.entities);
    status.increment = 100 / totalUpdates;

    let entities = Object.keys(summary.entities);

    //Ensure that the built-in entity types are processed before others.
    let prefEntityList = ['wave', 'application', 'server', 'database'];
    for (const entityName of entities)
    {
      if (!prefEntityList.includes(entityName)){
        //Add other custom items to end of list.
        prefEntityList.push(entityName);
      }
    }

    //Perform record creation.
    for (const entityName of prefEntityList){
      if (summary.entities[entityName].Create.length > 0){
        await commitItems(entityName, summary.entities[entityName].Create, summary.entities,"Create", status)
      }
    }

    //Perform record updates.
    for (const entityName of prefEntityList){
      if (summary.entities[entityName].Update.length > 0) {
        await commitItems(entityName, summary.entities[entityName].Update, summary.entities, "Update", status)
      }
    }

    hideCommitProgress()
    setErrorFile([]);
    setErrors(0);
    setItems([]);
    setSelectedFile(null);
    setCommitted(true);

    setItems([]);


    if (outputCommitErrors.length > 0) {
      let errors = outputCommitErrors.map(errorItem => (
        <ExpandableSection
          header={errorItem.itemType + " - " + errorItem.error}>{JSON.stringify(errorItem.item)}</ExpandableSection>
      ))

      handleNotification({
        id: status.id,
        type: 'error',
        dismissible: true,
        header: "Import of file '" + importName + "' had " + outputCommitErrors.length + " errors.",
        content: <ExpandableSection header='Error details'>{errors}</ExpandableSection>
      });
    } else {
      handleNotification({
        id: status.id,
        type: 'success',
        dismissible: true,
        header: 'Import of ' + importName + ' successful.'
      });
    }
  }

  function performValueValidation (attribute, value) {

    const stdErrorMulti = "If multiple values supplied, they must be separated by a semi-colon, without spaces."

    //Exit if attribute is not defined or null.
    if(!attribute.attribute && value !== '')
      return {type: 'warning', message: attribute.lookup_attribute_name + " attribute name not found in any user schema and your data file has provided values."};
    else if (!attribute.attribute && value === '')
      return null;

    let errorMsg = null;

    switch (attribute.attribute.type) {
      case 'list':
        let list = value.split(';')
        for (let item in list){
          errorMsg = validateValue(list[item], attribute.attribute)
        }
        break;
      case 'multivalue-string':
        let mvlist = value.split(';')
        for (let item in mvlist){
          errorMsg = validateValue(mvlist[item], attribute.attribute)
        }
        break;
      case 'relationship':
        errorMsg = validateValue(value, attribute.attribute)

        // if(value !== '' && value !== undefined && value !== null) {
        //   let relatedRecord = getRelationshipRecord(attribute, value);
        //   if (relatedRecord === null){
        //     errorMsg = 'Related record not found based on value provided.';
        //   }
        // }
        break;
      case 'json':
        if (value) {
          try{
            let testJSON = JSON.parse(value);
          } catch (objError) {
            if (objError instanceof SyntaxError) {
              console.error(objError.name);
              errorMsg = "Invalid JSON: " + objError.message;
            } else {
              console.error(objError.message);
            }

          }
        }
        break;
      default:
        errorMsg = validateValue(value, attribute.attribute)
    }

    if (errorMsg != null)
      return {'type': 'error', 'message': errorMsg}
    else
      return null;
  }

  useEffect( () => {
    let dataJson = []

    if (selectedFile) {
      (async () => {
        if (selectedFile.name.endsWith('.csv')) {

          let data = await readCSVFile(selectedFile);

          let csv = require('jquery-csv');

          dataJson = csv.toObjects(data);
        } else if (selectedFile.name.endsWith('.xlsx') || selectedFile.name.endsWith('.xls')) {
          let data = await readXLSXFile(selectedFile)
          let workbook = XLSX.read(data)
          let sheet = null;
          if (selectedSheet) {
            if (workbook.Sheets[selectedSheet]) {
              sheet = workbook.Sheets[selectedSheet];
            } else {
              sheet = workbook.Sheets[workbook.SheetNames[0]];
            }
          } else {
            sheet = workbook.Sheets[workbook.SheetNames[0]];
          }
          //Convert all numbers to text.
          Object.keys(sheet).forEach(function (s) {
            if (sheet[s].t === 'n') {
              delete sheet[s].w;
              sheet[s].z = '0';
              sheet[s].t = 's';
              sheet[s].w = sheet[s].v.toString()
              sheet[s].v = sheet[s].v.toString()
            }
          });

          dataJson = XLSX.utils.sheet_to_json(sheet)
        } else {
          //unsupported format of file.
          console.log(selectedFile.name + " - Unsupported file type.")
          setErrorFile(['Unsupported file type.'])
        }

        let columnsNotFound = []

        if (columnsNotFound.length > 0) {
          setErrorFile(columnsNotFound);
        } else {

          dataJson = performDataValidation(dataJson)

          setSummary(getSummary(dataJson));

          let errorCount = dataJson.data.reduce((accumulator, currentValue, currentIndex, array) => {
            return currentValue['__validation'].errors ? accumulator + currentValue['__validation'].errors.length : accumulator + 0
          }, 0);
          setErrors(errorCount);

          let warningCount = dataJson.data.reduce((accumulator, currentValue, currentIndex, array) => {
            return currentValue['__validation'].warnings ? accumulator + currentValue['__validation'].warnings.length : accumulator + 0
          }, 0);
          setWarnings(warningCount);

          let infromationalCount = dataJson.data.reduce((accumulator, currentValue, currentIndex, array) => {
            return currentValue['__validation'].informational ? accumulator + currentValue['__validation'].informational.length : accumulator + 0
          }, 0);
          setInformational(infromationalCount);

          setItems(dataJson.data);
        }
      })();
    }

  }, [selectedFile, selectedSheet])

  return (
    <>
      {<ImportIntakeWizard
        selectedFile={selectedFile}
        commitErrors={outputCommitErrors}
        items={items}
        errors={errors}
        warnings={warnings}
        informational={informational}
        schema={props.schema}
        dataAll={dataAll}
        uploadChange={handleUploadChange}
        uploadClick={handleUploadClick}
        cancelClick={handleCancelClick}
        summary={summary}
        importProgress={importProgressStatus}
        exportClick={handleDownloadTemplate}
        committed={committed}
        committing={committing}
        errorMessage={selectedFile && errorFile.length === 0 ? null : errorFile.length > 0 ? 'Error with file : ' + errorFile.join() : 'No file selected'}
        selectedSheetName={selectedSheet}
        sheetNames={sheetNames}
        sheetChange={setSelectedSheet}
        setHelpPanelContent={props.setHelpPanelContent ? props.setHelpPanelContent : undefined}
      />}

      <CommitProgressModel
        title={'Commit intake'}
        description="Committing intake form data to Migration factory datastore."
        label="Commit in progress"
      />
      <NoCommitModel title={'Commit intake'} noCancel onConfirmation={handleModalClose}>Nothing to be committed!</NoCommitModel>
    </>
  );
};

const ImportCompletion = (props) => {
  return (
    <Form
      header={<Header variant="h1">{' Intake form upload status.'}</Header>}
      actions={
        // located at the bottom of the form
        <SpaceBetween direction="horizontal" size="xs">
          <Button
            onClick={(e) => {
              props.cancelClick(e);
              props.setActiveStepIndex(0);
            }}
            disabled={!props.committed}
            variant="primary">
            New Upload
          </Button>
        </SpaceBetween>
      }
      errorText={null}
    >
      <Container
        header={
          <Header variant="h2">
            Intake form upload status.
          </Header>
        }
      >
        <SpaceBetween direction="vertical" size="l">
          {!props.committed ?
            <SpaceBetween size={"xxs"}>
              <Alert
                visible={!props.committed && props.committing}
                dismissAriaLabel="Close alert"
                header="Uploading..."
              >
                Intake data is being uploaded. If you navigate away from this page then errors will not be visible until the import job has completed, and will be displayed in the notification bar. It is recommended that you do not make changes to the data records that are included in the intake upload until it has completed.
              </Alert>
              <ProgressBar
                status={props.importProgress.percentageComplete >= 100 ? "success" : "in-progress"}
                value={props.importProgress.percentageComplete}
                additionalInfo={props.importProgress.status}
                label={'Upload progress'}
              />
            </SpaceBetween>
            :
            null
          }
          <Alert
            visible={props.commitErrors.length > 0}
            dismissAriaLabel="Close alert"
            type="error"
            header={"Errors returned during upload of " + props.commitErrors.length + " records."}>
            {props.commitErrors.map(errorItem => (
              <ExpandableSection header={errorItem.itemType + " - " + errorItem.error}>{JSON.stringify(errorItem.item)}</ExpandableSection>
            ))}
          </Alert>
          <Alert
            visible={(!props.summary.hasUpdates)}
            dismissAriaLabel="Close alert"
            type="success"
            header={"Nothing to upload! The contents of the selected import file match the data currently in Migration Factory."}
          >
            If this is not what you expected please check you loaded the correct file.
          </Alert>
          <Alert
            visible={(props.commitErrors.length === 0 && props.committed)}
            dismissAriaLabel="Close alert"
            type="success"
            header={"Intake file upload completed successfully."}
          >
          </Alert>
          <ExpandableSection header={"Record Overview"}>
            <ImportOverview
              items={props.summary}
              schemas={props.schema}
              dataAll={props.dataAll}
            />
          </ExpandableSection>
        </SpaceBetween>
      </Container>
    </Form>
  )

}

const ImportIntakeWizard = (props) => {
  const [
    activeStepIndex,
    setActiveStepIndex
  ] = React.useState(0);

  const hiddenFileInput = React.createRef();

  const helpContent = {
    header: 'Import',
    content_text: 'From here you can import an intake form for to create or update records with the Waves, Applications and Servers.'
  }

  return (
    props.committing
      ?
      <ImportCompletion {...props}
                        setActiveStepIndex={setActiveStepIndex}
      />
      :
      <Wizard
        i18nStrings={{
          stepNumberLabel: stepNumber =>
            `Step ${stepNumber}`,
          collapsedStepsLabel: (stepNumber, stepsCount) =>
            `Step ${stepNumber} of ${stepsCount}`,
          cancelButton: "Cancel",
          previousButton: "Previous",
          nextButton: "Next",
          submitButton: "Upload",
          optional: "optional"
        }}
        onCancel={(e) => {
          props.cancelClick(e);
          setActiveStepIndex(0);
        }
        }
        onSubmit={(e) => {
          props.uploadClick(e);
        }
        }
        onNavigate={({ detail }) => {

          //onClick={props.uploadClick} disabled={(props.errors > 0 || !props.selectedFile || props.committed)}

          switch (detail.requestedStepIndex) {
            case 0:
              setActiveStepIndex(detail.requestedStepIndex)
              break;
            case 1:
              if (!props.errorMessage) {
                setActiveStepIndex(detail.requestedStepIndex)
              }
              break;
            case 2:
              if (!(props.errorMessage || props.errors > 0)) {
                setActiveStepIndex(detail.requestedStepIndex)
              }
              break;
            default:
              break;
          }


        }
        }
        activeStepIndex={activeStepIndex}
        steps={[
          {
            title: "Select import file",
            info: props.setHelpPanelContent ? <Link variant="info" onFollow={() => props.setHelpPanelContent(helpContent, false)}>Info</Link> : undefined,
            description:
              <SpaceBetween size={'xl'} direction={'vertical'}>
                Intake forms should be in CSV/UTF8 or Excel/xlsx format.
              </SpaceBetween>,
            content: (
              <SpaceBetween size={'xl'} direction={'vertical'}>
                <SpaceBetween size={'s'} direction={'horizontal'}>
                  Download a template intake form.
                  <ButtonDropdown
                    items={[{
                      id: 'download_req',
                      text: 'Template with only required attributes',
                      description: 'Download template with required only.'
                    },{
                      id: 'download_all',
                      text: 'Template with all attributes',
                      description: 'Download template with all attributes.'
                    }]}
                    onItemClick={props.exportClick}
                  >Actions
                  </ButtonDropdown>
                </SpaceBetween>
                <Container
                  header={
                    <Header variant="h2">
                      Select file to commit
                    </Header>
                  }
                >
                  <FormField
                    label={'Intake Form'}
                    description={'Upload your intake form to load new data into Migration Factory.'}
                    errorText={props.errorMessage}
                  >
                    <SpaceBetween direction="vertical" size="xs">
                      <input ref={hiddenFileInput} accept=".csv,.xlsx" type="file" name="file" onChange={props.uploadChange} style={{ display: 'none' }}/>
                      <Button variant="primary" iconName="upload" onClick={() => {
                        hiddenFileInput.current.click();
                      }}>Select file
                      </Button>
                      {( props.selectedFile) ?
                        (
                          <SpaceBetween size={'xxl'} direction={'vertical'}>
                            <SpaceBetween size={'xxs'} direction={'vertical'}>
                              <SpaceBetween size={'xxs'} direction={'horizontal'}>
                                <Icon
                                  name={props.errorMessage ? "status-negative" : "status-positive"}
                                  size="normal"
                                  variant={props.errorMessage ? "error" : "success"}
                                /><>Filename: {props.selectedFile.name}</>
                              </SpaceBetween>
                              <SpaceBetween size={'xxs'} direction={'horizontal'}>File size: {(props.selectedFile.size/1024).toFixed(4)} KB</SpaceBetween>
                            </SpaceBetween>
                            {props.sheetNames ?
                              <SpaceBetween size={'xxs'} direction={'vertical'}>
                                Select Excel sheet to import from.
                                <Select
                                  selectedOption={{'label': props.selectedSheetName, 'value': props.selectedSheetName}}
                                  options={props.sheetNames.map(item => {
                                    return {'label': item, 'value': item}
                                  })}
                                  onChange={e => {props.sheetChange(e.detail.selectedOption.value)}}
                                />
                              </SpaceBetween>
                              :
                              null
                            }
                          </SpaceBetween>
                        )
                        :
                        null
                      }
                    </SpaceBetween>

                  </FormField>
                </Container>
              </SpaceBetween>
            )
          },
          {
            title: "Review changes",
            content: (
              <Container
                header={
                  <Header variant="h2">
                    Pre-upload validation
                  </Header>
                }
              >
                {( props.selectedFile) ?
                  <SpaceBetween direction="vertical" size="l">
                    <Alert
                      visible={(props.errors > 0)}
                      dismissAriaLabel="Close alert"
                      type="error"
                      header={"Your intake form has " + props.errors + " validation errors."}
                    >
                      Please see table below for details of the validation errors, you cannot import this file until resolved.
                    </Alert>
                    <Alert
                      visible={(props.warnings > 0)}
                      dismissAriaLabel="Close alert"
                      type="info"
                      header={"Your intake form has " + props.warnings + " validation warnings."}
                    >
                      Please see table below for details of the validation warnings, you can import this file with these warnings.
                    </Alert>
                    <Alert
                      visible={(props.informational > 0)}
                      dismissAriaLabel="Close alert"
                      type="info"
                      header={"Your intake form has " + props.informational + " informational validation messages."}
                    >
                      Please see table below for details of the validation messages.
                    </Alert>

                    <IntakeFormTable
                      items={props.items}
                      isLoading={false}
                      errorLoading={null}
                      schema={props.summary.attributeMappings ? props.summary.attributeMappings : []}
                    />
                  </SpaceBetween>
                  :
                  null
                }
              </Container>
            )
          },
          {
            title: "Upload data",
            content: (
              <ImportOverview
                items={props.summary}
                schemas={props.schema}
                dataAll={props.dataAll}
              />
            )
          }
        ]}
      />
  );
}

// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserImport;
