// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import User from "../actions/user";
import ImportOverview from '../components/import/ImportOverview';
import { getChanges, validateValue} from '../resources/main';
import * as XLSX from "xlsx";

import { Auth } from "@aws-amplify/auth";

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
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import { useProgressModal } from "../actions/ProgressModalHook";
import IntakeFormTable from '../components/IntakeFormTable';
import { useModal } from '../actions/Modal';
import {useGetDatabases} from "../actions/DatabasesHook";
import {checkAttributeRequiredConditions, getRequiredAttributes, parsePUTResponseErrors} from "../resources/recordFunctions";
import {useCredentialManager} from "../actions/CredentialManagerHook";

const UserImport = (props) => {

  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps },] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers },] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, ] = useMFWaves();
  const [{ isLoading: isLoadingDatabases, data: dataDatabases, error: errorDatabases }, ] = useGetDatabases();
  const [{ isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets }, ] = useCredentialManager();

  const dataAll = {secret: {data: dataSecrets, isLoading: isLoadingSecrets, error: errorSecrets}, database: {data: dataDatabases, isLoading: isLoadingDatabases, error: errorDatabases}, server: {data: dataServers, isLoading: isLoadingServers, error: errorServers}, application: {data: dataApps, isLoading: isLoadingApps, error: errorApps}, wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}};

  //Modals
  const { hide: hideCommitProgress, RenderModal: CommitProgressModel } = useProgressModal()

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
    for (let item of related_items)
    {
      for (const attr of rel_attributes){
        if (attr.listMultiSelect){
          //Deal with multiple related items. This only currently supports names not IDs.
          if (item["__" + attr.name] && (!item[attr.name] || item[attr.name].includes('tbc'))) {
            let relatedNamesIDs = item[attr.name];
            let relatedNames = item["__" + attr.name];

            //For each related name update the tbc values with new items ID.
            for (let relNameIdx = 0; relNameIdx < relatedNamesIDs.length; relNameIdx++) {
              if (relatedNamesIDs[relNameIdx] === 'tbc') {
                //check if this is a record to update.
                if (relatedNames[relNameIdx].toLowerCase() === newItem[attr.rel_display_attribute].toLowerCase()) {
                  relatedNamesIDs[relNameIdx] = newItem[attr.rel_key];
                }
              }
            }

            item[attr.name] = relatedNamesIDs;

          }
        } else {
          //Update single select items.
          if ((!item[attr.name] || item[attr.name] === 'tbc') && item["__" + attr.name]) {
            if (item["__" + attr.name].toLowerCase() === newItem[attr.rel_display_attribute].toLowerCase()) {
              item[attr.rel_key] = newItem[attr.rel_key];
              delete item["__" + attr.name];
            }
          }
        }
      }
    }
  }

  function removeCalculatedKeyValues(item){
    for (const key in item){
      if (key.startsWith('__')){
        delete item[key]
      }
    }
  }

  function buildCommitExceptionNotification(exception, schema, schema_shortname, currentItem){
    if ('response' in exception && 'data' in exception.response) {
      if (typeof exception.response.data === 'object' && 'cause' in exception.response.data){
        return ({
          itemType: schema,
          error: currentItem[schema_shortname + '_name'] ? currentItem[schema_shortname + '_name'] + " - " + exception.response.data.cause : exception.response.data.cause,
          item: currentItem
        });
      } else if ('errors' in exception.response.data){
          return ({
            itemType: schema,
            error: currentItem[schema_shortname + '_name'] ? currentItem[schema_shortname + '_name'] + " - " + JSON.stringify(exception.response.data.errors) : JSON.stringify(exception.response.data.errors),
            item: currentItem
          });
      } else {
        return ({
          itemType: schema,
          error: currentItem[schema_shortname + '_name'] ? currentItem[schema_shortname + '_name'] + " - " + JSON.stringify(exception.response.data) : JSON.stringify(exception.response.data),
          item: currentItem
        });
      }
    } else{
      return ({itemType: schema, error: currentItem[schema_shortname + '_name'] ? currentItem[schema_shortname + '_name'] + ' - Unknown error occurred' : 'Unknown error occurred', item: currentItem})
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

    for (let item of items)
    {
      let newItem = Object.assign({}, item);

      currentItem = item;

      removeCalculatedKeyValues(newItem);

      commitItems.push(currentItem);

      try {
        if (action === 'Update') {
          let item_id = newItem[schema_shortname + '_id'];
          delete newItem[schema_shortname + '_id'];
          await apiUser.putItem(item_id, newItem, schema_shortname);
          updateUploadStatus(notification, action + " " + schema + " records...");
        }

      } catch (e) {
        updateUploadStatus(notification, action + " " + schema + " records...");
        console.error(e);
        loutputCommit.push(buildCommitExceptionNotification(e,schema,schema_shortname,currentItem));
      }

    }

    try {
      if (action === 'Create') {
        for (let item of commitItems){
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
      let reader = new FileReader();

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
      let reader = new FileReader();

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

    let ws_data = {}

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

    let range = { s: { c: 0, r: 0 }, e: { c: attributes.length, r: 1 } }; // set worksheet cell range
    ws_data['!ref'] = XLSX.utils.encode_range(range);

    let wb = XLSX.utils.book_new(); // create new workbook
    wb.SheetNames.push('mf_intake'); // create new worksheet
    wb.Sheets['mf_intake'] = XLSX.utils.json_to_sheet(json_output); // load headers array into worksheet

    XLSX.writeFile(wb, "cmf-intake-form-req.xlsx") // export to user

    console.log("CMF intake template exported.")
  }

  function exportAllTemplate(){

    let ws_data = {}

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

    let range = { s: { c: 0, r: 0 }, e: { c: attributes.length, r: 1 } }; // set worksheet cell range
    ws_data['!ref'] = XLSX.utils.encode_range(range);

    let wb = XLSX.utils.book_new(); // create new workbook
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
    let attributeMappings = [];
    let schemas = [];

    for (let [itemIdx, item] of csvData.entries()) {
      let itemErrors = [];
      let itemWarnings = [];
      let itemInformational = [];
      for (const key in item) {
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
              return (item['schema_name'] === foundAttr.schema_name)
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

          let msgError = performValueValidation(foundAttr, item[key])
          if (msgError){
            if (msgError.type === 'error') {
              itemErrors.push({attribute: key, error: msgError.message});
            } else if (msgError.type === 'warning') {
              itemWarnings.push({attribute: key, error: msgError.message});
            }
          }
        }
      }

      item['__import_row'] = itemIdx;
      item['__validation'] = {};
      item['__validation']['errors'] = itemErrors;
      item['__validation']['warnings'] = itemWarnings;
      item['__validation']['informational'] = itemInformational
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

    if (e.target.files[0].type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
      let data = await readXLSXFile(e.target.files[0])
      let workbook = XLSX.read(data)
      //Set first sheet as default import source.
      setSelectedSheet(workbook.SheetNames[0]);
      if (workbook.SheetNames.length > 1) {
        setSheetNames(workbook.SheetNames);
        setSelectedSheet(workbook.SheetNames[0]);
      }
    }
  }

  function getSchemaAttribute(attributeName, schema) {
    let attr = null;

    for (let attribute of schema.attributes){
      if (attribute.name === attributeName){
        attr = attribute;
        break;
      }
    }

    return attr;
  }

  function getSchemaRelationshipAttributes(attributeName, schema) {
    let attributes = [];

    for (let attribute of schema.attributes) {
      if (attribute.type === 'relationship'){
        if (attribute.rel_display_attribute === attributeName){
          //We've got a live one!!
          attributes.push(attribute);
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

  function extractImportedRecordKeysForSchema(importData, schemaName){
    let tempSchemaName = schemaName === 'application' ? 'app' : schemaName;
    //Populate distinct records from data import for each schema, referenced by _name or _id attribute.
    const tempDistinct = [...new Set(importData.map(x => {
     if (tempSchemaName + '_id' in x){
        return x[tempSchemaName + '_id'];
      } else if ('[' + schemaName + ']' + tempSchemaName + '_id' in x) {
        return x['[' + schemaName + ']' + tempSchemaName + '_id'];
      } else  if (tempSchemaName + '_name' in x){
       return x[tempSchemaName + '_name'];
     } else if ('[' + schemaName + ']' + tempSchemaName + '_name' in x) {
       return x['[' + schemaName + ']' + tempSchemaName + '_name'];
     }
    }))];

    let cleanRecords = tempDistinct.filter(item => {return item !== undefined && item !== ''});

    if (cleanRecords === undefined) { //If nothing returned then continue to next schema.
      cleanRecords = []
    }

    return cleanRecords
  }

  function addImportedRecordCreateToSummary(schemaName, keyAttribute, keyAttributeValue, importedRecord, summaryResults, importDataRow){
    //1. Get required schema attributes for this entity type.
    //2. check returned required attributes against the list of attributes supplied in attributeMappings.
    //3. if there are missing required attributes add an error to the record/row.
    //4. recheck that values have been provided for all required attributes. Add errors to record/row if they do not have values.
    //5. Do not add to Create array.
    // Note: this check might need to be done with updates to once the ability to clear values is implemented.

    //Check the entity is valid, i.e. it has the user key defined, if not, do not add as this is not something the user is looking to create.

    if (keyAttribute.attribute.name in importedRecord && importedRecord[keyAttribute.attribute.name] !== '') {
      let check = checkValidItemCreate(importedRecord, props.schema[schemaName])

      if (check === null) {
        //No errors on item add to create array.
        summaryResults.entities[schemaName].Create.push(importedRecord);
        summaryResults.hasUpdates = true;
      } else {
        //Errors found on requirements check, log errors against data row.
        for (const error of check) {
          importDataRow['__validation']['errors'].push({
            attribute: error.name,
            error: "Missing required " + schemaName + " attribute: " + error.name
          });
        }
      }
    } else {
      //Name not provided.
      console.log('_name not provided.')

    }
  }

  function addImportedRecordExistingToSummary(schemaName, keyAttribute, keyAttributeValue, importedRecord, summaryResults, importDataRow){
    const tempSchemaName = schemaName === 'application' ? 'app' : schemaName;

    let item_id = -1;
    let item_name = null;
    let item = dataAll[schemaName].data.find(dataItem => {
        if (dataItem[keyAttribute.attribute.name]) {
          if (dataItem[keyAttribute.attribute.name].toLowerCase() === keyAttributeValue.toLowerCase()) {
            return true;
          }
        }
      }
    )

    if (item) {
      item_id = item[tempSchemaName + '_id'];
      item_name = item[tempSchemaName + '_name'];
    }

    let changesItemWithCalc = getChanges(importedRecord, dataAll[schemaName].data, keyAttribute.attribute.name, true)
    let changesItem = getChanges(importedRecord, dataAll[schemaName].data, keyAttribute.attribute.name, false)

    if (changesItem) {
      //Create a temporary item that has all updates and validate.
      let newItem = Object.assign({}, item);

      //Update temp object with changes.
      const keys = Object.keys(changesItem);
      for (let key of keys){
        newItem[key] = changesItem[key];
      }
      let check = checkValidItemCreate(newItem, props.schema[schemaName])

      //Add appid to item.
      if (check === null) {
        changesItemWithCalc[tempSchemaName + '_id'] = item_id;
        if (!changesItemWithCalc.hasOwnProperty(tempSchemaName + '_name')) {
          changesItemWithCalc[tempSchemaName + '_name'] = item_name;
        }
        summaryResults.entities[schemaName].Update.push(changesItemWithCalc);
        summaryResults.hasUpdates = true;
      } else {
        //Errors found on requirements check, log errors against data row.

        for (const error of check) {
          importDataRow['__validation']['errors'].push({
            attribute: error.name,
            error: "Missing required " + schemaName + " attribute: " + error.name
          });
        }
      }
    } else {
      let NoChangeItem = {};
      NoChangeItem[tempSchemaName + '_name'] = item_name
      summaryResults.entities[schemaName].NoChange.push(NoChangeItem);
    }
  }

  function addImportRowValuesToImportSummaryRecord(schemaName, attribute, importRow, importRecord){
    if (importRow.hasOwnProperty(attribute.import_raw_header) && attribute.attribute.type !== 'relationship') {
      switch (attribute.attribute.type) {
        case 'list': {
          if (attribute.attribute.listMultiSelect) {
            //Build array for multiselect attribute.
            let formattedText = importRow[attribute.import_raw_header];
            formattedText = formattedText.split(';');

            importRecord[attribute.attribute.name] = formattedText;
          } else {
            importRecord[attribute.attribute.name] = importRow[attribute.import_raw_header];
          }
          break;
        }
        case 'multivalue-string': {
          let formattedText = importRow[attribute.import_raw_header];
          formattedText = formattedText.split(';');

          importRecord[attribute.attribute.name] = formattedText;
          break;
        }
        case 'tag': {
          let formattedTags = importRow[attribute.import_raw_header];

          formattedTags = formattedTags.split(';');
          formattedTags = formattedTags.map(tag => {
            let key_value = tag.split('=');
            return {key: key_value[0], value: key_value[1]}
          });

          importRecord[attribute.attribute.name] = formattedTags;
          break;
        }
        case 'checkbox': {
          const formattedText = importRow[attribute.import_raw_header];
          const regex=/^\s*(true|1|on)\s*$/i
          importRecord[attribute.attribute.name] = regex.test(formattedText);
          break;
        }
        default: {
          importRecord[attribute.attribute.name] = importRow[attribute.import_raw_header];
        }
      }
    } else if (attribute.attribute.type === 'relationship') {
      addRelationshipValueToImportSummaryRecord(attribute, schemaName, importRow, importRecord)
    }
  }

  function getRelationshipValueType(importedAttribute, schemaName){
    if (importedAttribute.import_raw_header === ('[' + schemaName + ']' + importedAttribute.attribute.rel_display_attribute).toLowerCase()){
      return 'name';
    } else if (importedAttribute.import_raw_header.toLowerCase() === importedAttribute.attribute.rel_display_attribute.toLowerCase()) {
      return 'name';
    } else if (importedAttribute.import_raw_header.toLowerCase() === importedAttribute.attribute.name.toLowerCase() && importedAttribute.attribute.listMultiSelect) {
      return 'name';
    } else if (importedAttribute.import_raw_header.toLowerCase() === ('[' + schemaName + ']' + importedAttribute.attribute.name).toLowerCase() && importedAttribute.attribute.listMultiSelect) {
      return 'name';
    } else if (importedAttribute.import_raw_header.toLowerCase() === importedAttribute.attribute.name.toLowerCase()){
      return 'id';
    } else if (importedAttribute.import_raw_header.toLowerCase() === ('[' + schemaName + ']' + importedAttribute.attribute.name).toLowerCase()) {
      return 'id';
    }
  }

  function extractRelationshipList(importValueDelimitedStringList, importedAttribute, importSummaryRecord) {
    //Multiselect attribute.
    // Nothing to process if importValueDelimitedStringList is empty string so return.
    if (!importValueDelimitedStringList) {
      return;
    }
    const valuesRaw = importValueDelimitedStringList.split(";");
    let valuesID = [];
    let valuesDisplay = [];

    if (valuesRaw.length > 0) {
      for (const itemValue of valuesRaw) {
        let relatedItem = dataAll[importedAttribute.attribute.rel_entity].data.find(item => {
            if (item[importedAttribute.attribute.rel_display_attribute] && itemValue) {
              if (item[importedAttribute.attribute.rel_display_attribute].toLowerCase() === itemValue.toLowerCase()) {
                return true;
              }
            }
          }
        )
        if (relatedItem) {
          valuesID.push(relatedItem[importedAttribute.attribute.rel_key]);
          valuesDisplay.push(relatedItem[importedAttribute.attribute.rel_display_attribute]);
        } else {
          if (importValueDelimitedStringList !== '' && importValueDelimitedStringList !== undefined) {
            //Item name does not exist so will be created if provided.
            valuesID.push('tbc');
            valuesDisplay.push(itemValue);
          }
        }
      }

      importSummaryRecord[importedAttribute.attribute.name] = valuesID;
      importSummaryRecord['__' + importedAttribute.attribute.name] = valuesDisplay;
    }else {
      //No values provided.
      importSummaryRecord[importedAttribute.attribute.name] = [];
    }
  }

  function addRelationshipValueToImportSummaryRecord(importedAttribute, schemaName, importRow, importSummaryRecord) {
    const relationshipValueType = getRelationshipValueType(importedAttribute, schemaName);

    if (relationshipValueType === 'name') {
      //relationship value is a name not ID, perform search to see if this item exists.
      if (importedAttribute.attribute.listMultiSelect && importRow[importedAttribute.import_raw_header]) {
        extractRelationshipList(importRow[importedAttribute.import_raw_header],importedAttribute,importSummaryRecord)
      } else {
        //Not a multiselect relational value.
        let relatedItem = dataAll[importedAttribute.attribute.rel_entity].data.find(item => {
            if (item[importedAttribute.attribute.rel_display_attribute] && importRow[importedAttribute.import_raw_header]) {
              if (item[importedAttribute.attribute.rel_display_attribute].toLowerCase() === importRow[importedAttribute.import_raw_header].toLowerCase()) {
                return true;
              }
            }
          }
        )
        if (relatedItem) {
          importSummaryRecord[importedAttribute.attribute.name] = relatedItem[importedAttribute.attribute.rel_key];
        } else {
          if (importRow[importedAttribute.import_raw_header] !== '' && importRow[importedAttribute.import_raw_header] !== undefined) {
            //Item name does not exist, so will be created if provided. Setting ID to 'tbc', once the related
            // record is created then this will be updated in the commit with the new records' ID.
            importSummaryRecord[importedAttribute.attribute.name] = 'tbc'
            importSummaryRecord['__' + importedAttribute.attribute.name] = importRow[importedAttribute.import_raw_header];
          }
        }
      }
    } else if (relationshipValueType === 'id') {
      //related attribute display value not present in import, ID has been provided.

      if (importRow[importedAttribute.import_raw_header] !== '' && importRow[importedAttribute.import_raw_header] !== undefined) {
        //ID is being provided instead of display value.
        if (importedAttribute.attribute.listMultiSelect) {
          importSummaryRecord[importedAttribute.attribute.name] = importRow[importedAttribute.import_raw_header].split(";");
        } else {
          importSummaryRecord[importedAttribute.attribute.name] = importRow[importedAttribute.import_raw_header];
        }
      }
    } else{
      console.error('UNHANDLED: relationship type not found.')
    }
  }

  function isValidKeyValue(importItem, keyAttribute, importedRecordKeyValue){
    if (importItem[keyAttribute.import_raw_header]) {
      if (importItem[keyAttribute.import_raw_header].toLowerCase() === importedRecordKeyValue.toLowerCase()) {
        return true;
      }
    } else {
      return false;
    }
  }

  function getSummary(dataJson) {

    let distinct = {};

    let result = {
      "entities": {},
      "hasUpdates" : false
    };

    for (const schema_name in props.schema){
      if (props.schema[schema_name].schema_type === 'user'){
        let temp_schema_name = schema_name === 'application' ? 'app' : schema_name;
        result['entities'][schema_name] = {
          "Create": [],
          "Update": [],
          "NoChange": []

        };

        distinct[schema_name] = extractImportedRecordKeysForSchema(dataJson.data, schema_name);

        if (distinct[schema_name].length === 0) { //If nothing returned then continue to next schema.
          continue;
        }

        let schemaAttributes = [];

        schemaAttributes = dataJson.attributeMappings.filter(attr => {
          return attr.schema_name === schema_name;
        });

        let keyAttribute = schemaAttributes.find(attr => { //Get schema key attribute.
          if (attr.attribute.name === temp_schema_name + '_name' || attr.attribute.name === temp_schema_name + '_id') { //check if _name key present in attributes
            return attr;
          }
        });

        for (const importedRecordKeyValue of distinct[schema_name]) {

          if (importedRecordKeyValue === undefined){
            continue
          }

          if (importedRecordKeyValue !== undefined && importedRecordKeyValue.toLowerCase() !== '') { //Verify that the key has a value, if not ignore.

            let itemOrMismatch = isMismatchedItem(dataJson.data, schemaAttributes, keyAttribute.import_raw_header, importedRecordKeyValue.toLowerCase());
            if (itemOrMismatch !== null) {
              let importRow = dataJson.data.find(importItem => isValidKeyValue(importItem,keyAttribute, importedRecordKeyValue))

              let importRecord = {};
              importRecord[keyAttribute.attribute.name] = importedRecordKeyValue;

              for (const attr of schemaAttributes) {
                addImportRowValuesToImportSummaryRecord(schema_name, attr, importRow, importRecord)
              }

              if (dataAll[schema_name].data.some(dataItem => dataItem[keyAttribute.attribute.name].toLowerCase() === importedRecordKeyValue.toLowerCase())) {
                addImportedRecordExistingToSummary(schema_name,keyAttribute,importedRecordKeyValue,importRecord,result,importRow);
              } else {
                addImportedRecordCreateToSummary(schema_name,keyAttribute,importedRecordKeyValue,importRecord,result,importRow);
              }
            } else {
              //Not an issue as validation errors would have been recorded.
            }
          }
        }
      }
    }

    //Pass attribute mappings back as needed to build table columns and config.
    result.attributeMappings = dataJson.attributeMappings;

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
          key={errorItem.itemType + " - " + errorItem.error}
          headerText={errorItem.itemType + " - " + errorItem.error}>
          {JSON.stringify(errorItem.item)}
        </ExpandableSection>
      ))

      handleNotification({
        id: status.id,
        type: 'error',
        dismissible: true,
        header: "Import of file '" + importName + "' had " + outputCommitErrors.length + " errors.",
        content: <ExpandableSection headerText='Error details'>{errors}</ExpandableSection>
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

  function getCurrentErrorMessage() {

    if (selectedFile && errorFile.length === 0){
      return null;
    } else if (errorFile.length > 0) {
      return 'Error with file : ' + errorFile.join();
    } else {
      return 'No file selected'
    }
  }

  function performValueValidation (attribute, value) {

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
        break;
      case 'json':
        if (value) {
          try{
            JSON.parse(value);
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

  async function convertExcelToJSON(selectedFile){
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

    return XLSX.utils.sheet_to_json(sheet);
  }


//Function to remove null key values from json object array.
  function removeNullKeys(dataJson) {
    for (let i = 0; i < dataJson.length; i++) {
      for (let key in dataJson[i]) {
        if (dataJson[i][key] === null || dataJson[i][key] === "") {
          delete dataJson[i][key];
        }
      }
    }
    return dataJson;
  }

  function updateProcessingResultCounts(dataJson){
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
          dataJson = await convertExcelToJSON(selectedFile);
        } else {
          //unsupported format of file.
          console.error(selectedFile.name + " - Unsupported file type.")
          setErrorFile(['Unsupported file type.'])
        }

        dataJson = removeNullKeys(dataJson);

        let columnsNotFound = []

        if (columnsNotFound.length > 0) {
          setErrorFile(columnsNotFound);
        } else {

          dataJson = performDataValidation(dataJson)

          setSummary(getSummary(dataJson));

          updateProcessingResultCounts(dataJson);

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
        errorMessage={getCurrentErrorMessage()}
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
              <ExpandableSection
                key={errorItem.itemType + " - " + errorItem.error}
                header={errorItem.itemType + " - " + errorItem.error}>
                {JSON.stringify(errorItem.item)}
              </ExpandableSection>
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
