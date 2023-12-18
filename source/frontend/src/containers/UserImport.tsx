/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useContext, useEffect, useState} from 'react';
import UserApiClient from "../api_clients/userApiClient";
import * as XLSX from "xlsx";

import {ExpandableSection, ProgressBar,} from '@awsui/components-react';

import {useMFApps} from "../actions/ApplicationsHook";
import {useGetServers} from "../actions/ServersHook";
import {useMFWaves} from "../actions/WavesHook";
import {useGetDatabases} from "../actions/DatabasesHook";
import {parsePUTResponseErrors} from "../resources/recordFunctions";
import {useCredentialManager} from "../actions/CredentialManagerHook";
import {NotificationContext} from "../contexts/NotificationContext";
import {EntitySchema} from "../models/EntitySchema";
import {ClickEvent} from "../models/Events";
import {ImportIntakeWizard} from "../components/import/ImportIntakeWizard";
import {
  buildCommitExceptionNotification,
  convertExcelToJSON,
  exportAllTemplate,
  getRequiredAttributesAllSchemas,
  getSummary,
  performDataValidation,
  readCSVFile,
  readXLSXFile,
  removeCalculatedKeyValues,
  removeNullKeys,
  updateRelatedItemAttributes
} from "../utils/import-utils";
import {CMFModal} from "../components/Modal";
import {CompletionNotification} from "../models/CompletionNotification";

const UserImport = (props: { schemas: Record<string, EntitySchema> }) => {

  const {addNotification, setNotifications} = useContext(NotificationContext);

  //Data items for viewer and table.
  const [{isLoading: isLoadingApps, data: dataApps, error: errorApps},] = useMFApps();
  const [{isLoading: isLoadingServers, data: dataServers, error: errorServers},] = useGetServers();
  const [{isLoading: isLoadingWaves, data: dataWaves, error: errorWaves},] = useMFWaves();
  const [{isLoading: isLoadingDatabases, data: dataDatabases, error: errorDatabases},] = useGetDatabases();
  const [{isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets},] = useCredentialManager();

  const dataAll: Record<string, any> = {
    secret: {data: dataSecrets, isLoading: isLoadingSecrets, error: errorSecrets},
    database: {data: dataDatabases, isLoading: isLoadingDatabases, error: errorDatabases},
    server: {data: dataServers, isLoading: isLoadingServers, error: errorServers},
    application: {data: dataApps, isLoading: isLoadingApps, error: errorApps},
    wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}
  };

  const [isNoCommitModalVisible, setNoCommitModalVisible] = useState(false)

  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string | undefined>();
  const [items, setItems] = useState<any[]>([]);
  const [committing, setCommitting] = useState(false);
  const [committed, setCommitted] = useState(false);
  const [errors, setErrors] = useState(0);
  const [importProgressStatus, setImportProgressStatus]
    = useState<CompletionNotification>({status: '', percentageComplete: 0, increment: 0});
  const [warnings, setWarnings] = useState(0);
  const [informational, setInformational] = useState(0);
  const [errorFile, setErrorFile] = useState<string[]>([]);
  const [outputCommitErrors, setOutputCommitErrors] = useState<any[]>([]);
  const [summary, setSummary] = useState({
    "entities": {} as Record<string, any>,
    "hasUpdates": false,
    attributeMappings: [] as any[]
  });

  if (typeof (FileReader) === "undefined") {
    setErrorFile(["This browser does not support HTML5, it is not possible to import files."]);
  }

  const reader = new FileReader();

  function updateUploadStatus(notification: CompletionNotification, message: string, numberRecords = 1) {
    notification.status = message;
    notification.percentageComplete = notification.percentageComplete + (notification.increment * numberRecords)
    addNotification({
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

  async function commitItems(
    schema: string,
    items: any[],
    dataImport: {
      [x: string]: {
        Create: any[];
        Update: any[];
      };
    },
    action: string,
    notification: CompletionNotification
  ) {

    const schema_shortname = schema === 'application' ? 'app' : schema;

    const start = Date.now();

    if (!items || items.length === 0) {
      //Nothing to be done as items is empty.
      const millis = Date.now() - start;
      console.debug(`seconds elapsed = ${Math.floor(millis / 1000)}`);
      return;
    }

    let loutputCommit = [];
    let commitItems = [];
    let currentItem = null;
    const apiUser = new UserApiClient();

    for (let item of items) {
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

      } catch (e: any) {
        updateUploadStatus(notification, action + " " + schema + " records...");
        console.error(e);
        loutputCommit.push(buildCommitExceptionNotification(e, schema, schema_shortname, currentItem));
      }

    }

    try {
      if (action === 'Create') {
        for (let item of commitItems) {
          delete item[schema_shortname + '_id'];
        }

        console.debug("Starting bulk post")
        const result = await apiUser.postItems(commitItems, schema_shortname);
        updateUploadStatus(notification, "Updating any related records with new " + schema + " IDs...", commitItems.length / 2);
        console.debug("Bulk post complete")

        if (result['newItems']) {
          console.debug("Updating related items")
          for (const item of result['newItems']) {

            for (const updateSchema in dataImport) {
              //TODO add logic to determine if the updateSchema is related to current schema by any attributes
              // and then only update those that are, for the moment it will validate all.
              updateRelatedItemAttributes(props.schemas, item, schema, dataImport[updateSchema].Create, updateSchema);
              updateRelatedItemAttributes(props.schemas, item, schema, dataImport[updateSchema].Update, updateSchema);
            }
          }

          updateUploadStatus(
            notification,
            `Updating any related records with new ${schema} IDs...`, commitItems.length / 2);
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

    } catch (e: any) {
      console.debug(e);
      if (e) {
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

  async function handleDownloadTemplate(e: ClickEvent) {
    e.preventDefault();

    let action = e.detail.id;

    switch (action) {
      case 'download_req': {
        exportTemplate();
        break;
      }
      case 'download_all': {
        exportAllTemplate(props.schemas);
        break;
      }
    }

  }

  function exportTemplate() {

    let ws_data: Record<string, any> = {}

    let attributes = getRequiredAttributesAllSchemas(props.schemas); // get all required attributes from all schemas

    let headers: Record<string, any> = {}
    for (const attr_idx in attributes) {
      const attribute = attributes[attr_idx];
      if (attribute.type === "relationship") {
        headers[attribute.rel_display_attribute!] = attribute.sample_data_intake ? attribute.sample_data_intake : "";
      } else {
        headers[attribute.name] = attribute.sample_data_intake ? attribute.sample_data_intake : "";
      }
    }
    const json_output = [headers] // Create single item array with empty values to populate headers fdr intake form.

    let range = {s: {c: 0, r: 0}, e: {c: attributes.length, r: 1}}; // set worksheet cell range
    ws_data['!ref'] = XLSX.utils.encode_range(range);

    let wb = XLSX.utils.book_new(); // create new workbook
    wb.SheetNames.push('mf_intake'); // create new worksheet
    wb.Sheets['mf_intake'] = XLSX.utils.json_to_sheet(json_output); // load headers array into worksheet

    XLSX.writeFile(wb, "cmf-intake-form-req.xlsx") // export to user

    console.log("CMF intake template exported.")
  }



  async function handleUploadChange(e: any) {

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
    setSelectedSheet(undefined);
    setSheetNames([]);

    setSelectedFile(e.target.files[0])

    if (e.target.files[0].type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
      let data = await readXLSXFile(reader, e.target.files[0])
      let workbook = XLSX.read(data)
      //Set first sheet as default import source.
      setSelectedSheet(workbook.SheetNames[0]);
      if (workbook.SheetNames.length > 1) {
        setSheetNames(workbook.SheetNames);
        setSelectedSheet(workbook.SheetNames[0]);
      }
    }
  }

  async function handleCancelClick() {

    //Reset for new upload.
    setErrorFile([]);
    setErrors(0);
    setItems([]);
    setSelectedFile(null);
    setOutputCommitErrors([]);
    setCommitted(false);
    setCommitting(false);
    setSelectedSheet(undefined);
    setSheetNames([]);

  }

  function countUpdates(entities: {
    [x: string]: {
      Create: any[];
      Update: any[];
    };
  }) {
    let totalUpdates = 0;

    for (const entity in entities) {
      totalUpdates += entities[entity].Create.length;
      totalUpdates += entities[entity].Update.length;
    }

    return totalUpdates;
  }

  async function handleUploadClick() {

    if (!summary.hasUpdates) {
      setNoCommitModalVisible(true)
      return;
    }

    let importName = selectedFile?.name;

    if (selectedSheet) {
      importName = selectedFile?.name + " [" + selectedSheet + "]"
    }

    let status: CompletionNotification = {
      increment: 1,
      percentageComplete: 0,
      status: "Starting upload...",
      'importName': importName
    }
    status.id = addNotification({
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
    for (const entityName of entities) {
      if (!prefEntityList.includes(entityName)) {
        //Add other custom items to end of list.
        prefEntityList.push(entityName);
      }
    }

    //Perform record creation.
    for (const entityName of prefEntityList) {
      if (summary.entities[entityName].Create.length > 0) {
        await commitItems(entityName, summary.entities[entityName].Create, summary.entities, "Create", status)
      }
    }

    //Perform record updates.
    for (const entityName of prefEntityList) {
      if (summary.entities[entityName].Update.length > 0) {
        await commitItems(entityName, summary.entities[entityName].Update, summary.entities, "Update", status)
      }
    }

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

      addNotification({
        id: status.id,
        type: 'error',
        dismissible: true,
        header: "Import of file '" + importName + "' had " + outputCommitErrors.length + " errors.",
        content: <ExpandableSection headerText='Error details'>{errors}</ExpandableSection>
      });
    } else {
      addNotification({
        id: status.id,
        type: 'success',
        dismissible: true,
        header: 'Import of ' + importName + ' successful.'
      });
    }
  }

  function getCurrentErrorMessage() {

    if (selectedFile && errorFile.length === 0) {
      return null;
    } else if (errorFile.length > 0) {
      return 'Error with file : ' + errorFile.join();
    } else {
      return 'No file selected'
    }
  }

  function updateProcessingResultCounts(dataJson: any) {
    let errorCount = dataJson.data.reduce((accumulator: number, currentValue: { [x: string]: { errors: any[]; }; }) => {
      return currentValue['__validation'].errors ? accumulator + currentValue['__validation'].errors.length : accumulator
    }, 0);
    setErrors(errorCount);

    let warningCount = dataJson.data.reduce((accumulator: number, currentValue: { [x: string]: { warnings: any[]; }; }) => {
      return currentValue['__validation'].warnings ? accumulator + currentValue['__validation'].warnings.length : accumulator
    }, 0);
    setWarnings(warningCount);

    let infromationalCount = dataJson.data.reduce((accumulator: number, currentValue: { [x: string]: { informational: any[]; }; }) => {
      return currentValue['__validation'].informational ? accumulator + currentValue['__validation'].informational.length : accumulator
    }, 0);
    setInformational(infromationalCount);
  }

  useEffect(() => {
    let dataJson: any = []

    if (selectedFile) {
      (async () => {

        if (selectedFile.name.endsWith('.csv')) {

          let data = await readCSVFile(reader, selectedFile);

          let csv = require('jquery-csv');

          dataJson = csv.toObjects(data);
        } else if (selectedFile.name.endsWith('.xlsx') || selectedFile.name.endsWith('.xls')) {
          dataJson = await convertExcelToJSON(reader, selectedFile, selectedSheet);
        } else {
          //unsupported format of file.
          console.error(selectedFile.name + " - Unsupported file type.")
          setErrorFile(['Unsupported file type.'])
        }

        dataJson = removeNullKeys(dataJson);

        dataJson = performDataValidation(props.schemas, dataJson)

        const summary1 = getSummary(props.schemas, dataJson, dataAll);
        setSummary(summary1);

        updateProcessingResultCounts(dataJson);

        setItems(dataJson.data);

      })();
    }

  }, [selectedFile, selectedSheet])

  const hideNoCommitModal = () => setNoCommitModalVisible(false);
  return (
    <>
      {<ImportIntakeWizard
        selectedFile={selectedFile}
        items={items}
        errors={errors}
        warnings={warnings}
        informational={informational}
        schema={props.schemas}
        dataAll={dataAll}
        uploadChange={handleUploadChange}
        uploadClick={handleUploadClick}
        cancelClick={handleCancelClick}
        summary={summary}
        exportClick={handleDownloadTemplate}
        committing={committing}
        committed={committed}
        importProgressStatus={importProgressStatus}
        errorMessage={getCurrentErrorMessage()}
        selectedSheetName={selectedSheet}
        sheetNames={sheetNames}
        sheetChange={setSelectedSheet}
        outputCommitErrors={outputCommitErrors}
      />}

      <CMFModal
        onDismiss={hideNoCommitModal}
        visible={isNoCommitModalVisible}
        header={'Commit intake'}
      >
        Nothing to be committed!
      </CMFModal>

    </>
  );
};

export default UserImport;
