/* eslint-disable */
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { useContext, useEffect, useState, useMemo } from "react";
import UserApiClient from "../api_clients/userApiClient";
import * as XLSX from "xlsx";

import { ExpandableSection, ProgressBar } from "@cloudscape-design/components";

import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook";
import { useMFWaves } from "../actions/WavesHook";
import { useGetDatabases } from "../actions/DatabasesHook";
import { parsePUTResponseErrors } from "../resources/recordFunctions";
import { useCredentialManager } from "../actions/CredentialManagerHook";
import { NotificationContext } from "../contexts/NotificationContext";
import { EntitySchema } from "../models/EntitySchema";
import { ClickEvent } from "../models/Events";
import { ImportIntakeWizard } from "../components/import/ImportIntakeWizard";
import {
  buildCommitExceptionNotification,
  convertDataFileToJSON,
  exportAllTemplate,
  getRequiredAttributesAllSchemas,
  getSummary,
  mergeDuplicates,
  performDataValidation,
  readXLSXFile,
  removeCalculatedKeyValues,
  removeNullKeys,
  removeTbcValues,
  splitIntoEntities,
  updateAllRelationships,
} from "../utils/import-utils";
import { CMFModal } from "../components/Modal";
import { CompletionNotification } from "../models/CompletionNotification";

// Type definitions for better type safety
type CommitAction = "Create" | "Update";

type DataImportStructure = {
  [schemaName: string]: {
    Create: any[];
    Update: any[];
  };
};

const UserImport = (props: { schemas: Record<string, EntitySchema> }) => {
  const { addNotification } = useContext(NotificationContext);
  const apiUser = new UserApiClient();

  // Remove the duplicate "application" key from the schema
  const schemas = useMemo(() => {
    const { app, ...filteredSchemas } = props.schemas;
    return filteredSchemas;
  }, [props.schemas]);

  //Data items for viewer and table.
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }] = useMFWaves();
  const [{ isLoading: isLoadingDatabases, data: dataDatabases, error: errorDatabases }] = useGetDatabases();
  const [{ isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets }] = useCredentialManager();

  // Track items created/updated during import
  const [importedItems, setImportedItems] = useState<Record<string, any[]>>({
    secret: [],
    database: [],
    server: [],
    application: [],
    wave: [],
  });

  // dataAll includes both original data from the backend and imported items
  const dataAll: Record<string, any> = useMemo(() => {
    const mergeData = (originalData: any[], importedData: any[], keyField: string) => {
      if (!importedData.length) return originalData;

      const merged = [...originalData];
      const existingIds = new Set(originalData.map(item => item[keyField]).filter(id => id != null));

      // Add new items that don't exist in original data
      for (const importedItem of importedData) {
        const itemId = importedItem[keyField];
        if (itemId != null && !existingIds.has(itemId)) {
          merged.push(importedItem);
        } else if (itemId != null) {
          // Update existing items with imported changes
          const existingIndex = merged.findIndex(item => item[keyField] === itemId);
          if (existingIndex !== -1) {
            merged[existingIndex] = { ...merged[existingIndex], ...importedItem };
          }
        }
      }

      return merged;
    };

    return {
      secret: {
        data: mergeData(dataSecrets || [], importedItems.secret, 'Name'),
        isLoading: isLoadingSecrets,
        error: errorSecrets
      },
      database: {
        data: mergeData(dataDatabases || [], importedItems.database, 'database_id'),
        isLoading: isLoadingDatabases,
        error: errorDatabases
      },
      server: {
        data: mergeData(dataServers || [], importedItems.server, 'server_id'),
        isLoading: isLoadingServers,
        error: errorServers
      },
      application: {
        data: mergeData(dataApps || [], importedItems.application, 'app_id'),
        isLoading: isLoadingApps,
        error: errorApps
      },
      wave: {
        data: mergeData(dataWaves || [], importedItems.wave, 'wave_id'),
        isLoading: isLoadingWaves,
        error: errorWaves
      },
    };
  }, [
    dataSecrets, dataDatabases, dataServers, dataApps, dataWaves,
    isLoadingSecrets, isLoadingDatabases, isLoadingServers, isLoadingApps, isLoadingWaves,
    errorSecrets, errorDatabases, errorServers, errorApps, errorWaves,
    importedItems
  ]);

  const [isNoCommitModalVisible, setNoCommitModalVisible] = useState(false);

  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [sheetNames, setSheetNames] = useState<string[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string | undefined>();
  const [items, setItems] = useState<any[]>([]);
  const [committing, setCommitting] = useState(false);
  const [committed, setCommitted] = useState(false);
  const [errors, setErrors] = useState(0);
  const [importProgressStatus, setImportProgressStatus] = useState<CompletionNotification>({
    status: "",
    percentageComplete: 0,
    increment: 0,
  });
  const [warnings, setWarnings] = useState(0);
  const [informational, setInformational] = useState(0);
  const [errorFile, setErrorFile] = useState<string[]>([]);
  const [outputCommitErrors, setOutputCommitErrors] = useState<any[]>([]);
  const [summary, setSummary] = useState({
    entities: {} as Record<string, any>,
    hasUpdates: false,
    attributeMappings: [] as any[],
  });

  if (typeof FileReader === "undefined") {
    setErrorFile(["This browser does not support HTML5, it is not possible to import files."]);
  }

  const reader = new FileReader();

  function updateUploadStatus(notification: CompletionNotification, message: string, numberRecords = 1) {
    notification.status = message;
    notification.percentageComplete = notification.percentageComplete + notification.increment * numberRecords;
    addNotification({
      id: notification.id,
      type: "info",
      loading: true,
      dismissible: false,
      content: (
        <ProgressBar
          label={"Importing file '" + notification.importName + "' ..."}
          value={notification.percentageComplete}
          additionalInfo={notification.status}
          variant="flash"
        />
      ),
    });
    setImportProgressStatus(notification);
  }

  async function commitItems(
    schema: string,
    items: any[],
    dataImport: DataImportStructure,
    action: CommitAction,
    notification: CompletionNotification,
    returnCreatedItems: boolean = false
  ): Promise<{ items: any[], errors: any[] }> {
    const startTime = Date.now();
    const schemaShortname = schema === "application" ? "app" : schema;

    // Early return for empty items
    if (!items?.length) {
      console.debug(`${action} ${schema}: No items to process`);
      return { items: [], errors: [] };
    }

    console.debug(`Starting ${action} for ${items.length} ${schema} items`);

    const errors: any[] = [];

    try {
      if (action === "Create") {
        const createdItems = await handleCreateItems(items, schema, schemaShortname, dataImport, notification, returnCreatedItems, errors);
        return { items: createdItems, errors };
      } else if (action === "Update") {
        await handleUpdateItems(items, schema, schemaShortname, notification, errors);
        return { items: [], errors };
      } else {
        throw new Error(`Unsupported action: ${action}`);
      }
    } catch (error) {
      console.error(`Error during ${action} operation for ${schema}:`, error);
      errors.push(buildCommitExceptionNotification(error as any, schema, schemaShortname, {}));
      return { items: [], errors };
    } finally {
      // Log timing and handle errors
      const duration = Math.floor((Date.now() - startTime) / 1000);
      console.debug(`${action} ${schema} completed in ${duration} seconds`);
    }
  }

  async function handleCreateItems(
    items: any[],
    schema: string,
    schemaShortname: string,
    dataImport: DataImportStructure,
    notification: CompletionNotification,
    returnCreatedItems: boolean,
    errors: any[]
  ): Promise<any[]> {
    // Prepare items for creation
    const preparedItems = items.map(item => {
      const cleanItem = { ...item };
      removeCalculatedKeyValues(cleanItem);
      removeTbcValues(cleanItem);
      // Remove ID field for creation
      delete cleanItem[schemaShortname + "_id"];
      return cleanItem;
    });

    try {
      console.debug(`Starting bulk creation for ${preparedItems.length} ${schema} items`);
      const result = await apiUser.postItems(preparedItems, schemaShortname);

      let createdItems: any[] = [];

      if (result.newItems) {
        updateUploadStatus(notification, `Created ${schema} records...`, preparedItems.length);

        // Inject returned IDs back into dataImport for relationship updates
        injectReturnedIdsIntoDataImport(result.newItems, dataImport, schemaShortname);

        if (returnCreatedItems) {
          // Add schema metadata for later relationship updates
          createdItems = result.newItems.map((item: any) => ({
            ...item,
            __schemaName: schema
          }));
        }

        console.debug(`Successfully created ${result.newItems.length} ${schema} items`);
      }

      if (result.errors) {
        console.warn(`Creation errors for ${schema}:`, result.errors);
        const parsedErrors = parsePUTResponseErrors(result.errors);
        errors.push({
          itemType: schema,
          error: "Create failed",
          item: parsedErrors,
        });
      }

      return createdItems;
    } catch (error) {
      console.error(`Bulk creation failed for ${schema}:`, error);
      handleCommitItemsError(error, schema, "Create", notification, errors);
      return [];
    }
  }

  function handleCommitItemsError(
    e: any,
    schema: string,
    action: string,
    notification: CompletionNotification,
    loutputCommit: any[]
  ) {
    console.debug(e);
    let item = {};
    if (e) {
      item = JSON.stringify(e);
      if (e?.response?.data?.errors) {
        // return API errors to user.
        console.debug(e.response.data.errors);
        item = parsePUTResponseErrors(e.response.data.errors);
      }
    }

    loutputCommit.push({
      itemType: schema + " " + action,
      error: "Internal API error - Contact support",
      item: item,
    });

    updateUploadStatus(notification, "Error uploading records of type :" + schema, commitItems.length);
  }

  async function handleUpdateItems(
    items: any[],
    schema: string,
    schemaShortname: string,
    notification: CompletionNotification,
    errors: any[]
  ): Promise<void> {
    const batchSize = 10; // Process updates in batches to avoid overwhelming the API

    for (let i = 0; i < items.length; i += batchSize) {
      const batch = items.slice(i, i + batchSize);
      const batchPromises = batch.map(async (item) => {
        try {
          const updateItem = { ...item };
          removeCalculatedKeyValues(updateItem);
          removeTbcValues(updateItem);

          const itemId = updateItem[schemaShortname + "_id"];
          if (!itemId) {
            throw new Error(`Missing ID for ${schema} update operation`);
          }

          // Remove ID from update payload
          delete updateItem[schemaShortname + "_id"];

          await apiUser.putItem(itemId, updateItem, schemaShortname);
          console.debug(`Successfully updated ${schema} item ${itemId}`);
        } catch (error) {
          console.error(`Failed to update ${schema} item:`, error);
          errors.push(buildCommitExceptionNotification(error as any, schema, schemaShortname, item));
        }
      });

      // Wait for current batch to complete before processing next batch
      await Promise.all(batchPromises);

      // Update progress
      const completed = Math.min(i + batchSize, items.length);
      updateUploadStatus(notification, `Updated ${schema} records...`, completed);
    }
  }

  function injectReturnedIdsIntoDataImport(
    newItems: any[],
    dataImport: DataImportStructure,
    schemaShortname: string
  ): void {
    if (!newItems?.length) {
      return;
    }

    // Create a lookup map for newly created items by their name
    const nameToIdMap = new Map<string, string>();
    const nameKey = schemaShortname + "_name";
    const idKey = schemaShortname + "_id";

    for (const newItem of newItems) {
      const itemName = newItem[nameKey];
      const itemId = newItem[idKey];

      if (itemName && itemId) {
        const compositeKey = `${schemaShortname}:${itemName.toLowerCase()}`
        nameToIdMap.set(compositeKey, itemId);
      }
    }

    if (nameToIdMap.size === 0) {
      console.debug("No valid name-to-ID mappings found in new items");
      return;
    }

    console.debug(`Injecting ${nameToIdMap.size} IDs into dataImport for ${schemaShortname}`);

    // Update all items in dataImport that might reference the newly created items
    for (const [schemaName, schemaData] of Object.entries(dataImport)) {
      const allItems = [...schemaData.Create, ...schemaData.Update];
      const currentSchemaShortname = schemaName === "application" ? "app" : schemaName;
      const currentNameKey = currentSchemaShortname + "_name";
      const currentIdKey = currentSchemaShortname + "_id";

      for (const item of allItems) {
        // Check if this item needs an ID injection
        const itemName = item[currentNameKey];
        const compositeKey = `${currentSchemaShortname}:${itemName.toLowerCase()}`

        if (itemName && nameToIdMap.has(compositeKey) && !item[currentIdKey]) {
          item[currentIdKey] = nameToIdMap.get(compositeKey);
        }

        // Also check for relationship references that might need updating
        injectIdsIntoRelationshipFields(item, nameToIdMap, schemaShortname);
      }
    }
  }

  function injectIdsIntoRelationshipFields(
    item: any,
    nameToIdMap: Map<string, string>,
    schemaShortname: string,
  ): void {
    // Look for relationship fields that might reference the newly created items
    for (const [key, value] of Object.entries(item)) {
      if (key.startsWith('__') && typeof value === 'string') {
        // This might be a relationship display value that needs ID injection
        const actualKey = key.substring(2); // Remove __ prefix

        if (item.hasOwnProperty(actualKey)) {
          // Get the related item ID if available
          const cachedId = getIdFromCache(actualKey, nameToIdMap, schemaShortname);

          if (cachedId) {
            // Update the actual relationship field with the ID
            item[actualKey] = cachedId;
            console.debug(`Updated relationship field ${actualKey} with ID for ${value}`);
          } else {
            console.warn(`Skipping field ${actualKey}`);
          }
        }
      }
    }
  }

  function getIdFromCache(fieldName: string, nameToIdMap: Map<string, string>, currentSchema: string): string | undefined {
    // Find the schema which relates to the attribute
    const schema = Object.entries(schemas).find(([schemaName, _]) => schemaName === currentSchema);
    if (!schema) {
      return;
    }
    // Look for the field in this schema's attributes
    const attribute = schema[1].attributes.find(attr => attr.name === fieldName);
    if (!attribute) {
      return;
    }
    // Check if this is a relationship field that references the target schema
    const isRelationshipField = attribute.type === 'relationship' || attribute.type === 'multivalue-relationship';
    if (!isRelationshipField) {
      return;
    }
    // Get the schema name of the target entity
    const targetSchemaName = attribute.rel_entity
    return nameToIdMap.get(`${targetSchemaName}:${fieldName.toLowerCase()}`)
  }

  async function handleDownloadTemplate(e: ClickEvent) {
    e.preventDefault();

    const action = e.detail.id;

    switch (action) {
      case "download_req": {
        exportTemplate();
        break;
      }
      case "download_all": {
        exportAllTemplate(schemas);
        break;
      }
    }
  }

  function exportTemplate() {
    const ws_data: Record<string, any> = {};

    const attributes = getRequiredAttributesAllSchemas(schemas); // get all required attributes from all schemas

    const headers: Record<string, any> = {};
    for (const attr_idx in attributes) {
      const attribute = attributes[attr_idx];
      if (attribute.type === "relationship") {
        headers[attribute.rel_display_attribute!] = attribute.sample_data_intake ? attribute.sample_data_intake : "";
      } else {
        headers[attribute.name] = attribute.sample_data_intake ? attribute.sample_data_intake : "";
      }
    }
    const json_output = [headers]; // Create single item array with empty values to populate headers fdr intake form.

    const range = { s: { c: 0, r: 0 }, e: { c: attributes.length, r: 1 } }; // set worksheet cell range
    ws_data["!ref"] = XLSX.utils.encode_range(range);

    const wb = XLSX.utils.book_new(); // create new workbook
    wb.SheetNames.push("mf_intake"); // create new worksheet
    wb.Sheets["mf_intake"] = XLSX.utils.json_to_sheet(json_output); // load headers array into worksheet

    XLSX.writeFile(wb, "cmf-intake-form-req.xlsx"); // export to user

    console.log("CMF intake template exported.");
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

    // Reset imported items for new upload
    setImportedItems({
      secret: [],
      database: [],
      server: [],
      application: [],
      wave: [],
    });

    setSelectedFile(e.target.files[0]);

    if (e.target.files[0].type === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet") {
      const data = await readXLSXFile(reader, e.target.files[0]);
      const workbook = XLSX.read(data, { raw: true });
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

    // Reset imported items
    setImportedItems({
      secret: [],
      database: [],
      server: [],
      application: [],
      wave: [],
    });
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
      setNoCommitModalVisible(true);
      return;
    }

    let importName = selectedFile?.name;

    if (selectedSheet) {
      importName = selectedFile?.name + " [" + selectedSheet + "]";
    }

    const status: CompletionNotification = {
      increment: 1,
      percentageComplete: 0,
      status: "Starting upload...",
      importName: importName,
    };
    status.id = addNotification({
      type: "info",
      loading: true,
      dismissible: false,
      content: (
        <ProgressBar
          label={"Importing file " + importName + " ..."}
          value={0}
          additionalInfo="Starting upload..."
          variant="flash"
        />
      ),
    });

    setCommitting(true);

    const totalUpdates = countUpdates(summary.entities);
    status.increment = 100 / totalUpdates;

    const entities = Object.keys(summary.entities);

    //Ensure that the built-in entity types are processed before others.
    const prefEntityList = ["wave", "application", "server", "database"];
    for (const entityName of entities) {
      if (!prefEntityList.includes(entityName)) {
        //Add other custom items to end of list.
        prefEntityList.push(entityName);
      }
    }

    // Track all created and updated items so we can display post import summary
    const allCreatedItems: Record<string, any[]> = {
      secret: [],
      database: [],
      server: [],
      application: [],
      wave: [],
    };
    const allUpdatedItems: Record<string, any[]> = {
      secret: [],
      database: [],
      server: [],
      application: [],
      wave: [],
    };

    // Step 1: Perform all record creation first (without relationship updates)
    const allNewItems: any[] = [];
    const allCreateErrors: any[] = [];
    for (const entityName of prefEntityList) {
      if (summary.entities[entityName].Create.length > 0) {
        const result = await commitItems(entityName, summary.entities[entityName].Create, summary.entities, "Create", status, true);
        allNewItems.push(...result.items);
        allCreateErrors.push(...result.errors);

        // Track created items
        if (result.items.length > 0) {
          allCreatedItems[entityName].push(...result.items);
        }
      }
    }

    // Step 2: Perform record updates
    const allUpdateErrors: any[] = [];
    for (const entityName of prefEntityList) {
      if (summary.entities[entityName].Update.length > 0) {
        const result = await commitItems(entityName, summary.entities[entityName].Update, summary.entities, "Update", status);
        allUpdateErrors.push(...result.errors);

        // Track updated items
        if (result.items.length > 0) {
          allUpdatedItems[entityName].push(...result.items);
        }
      }
    }

    // Step 3: Now update all relationships in one final pass
    const allRelationshipErrors: any[] = [];
    if (allNewItems.length > 0) {
      await updateAllRelationships(
        allNewItems,
        summary.entities,
        schemas,
        status,
        updateUploadStatus,
        outputCommitErrors,
        allRelationshipErrors
      );
    }

    // Step 4: Update importedItems state to enhance dataAll
    setImportedItems(prevImported => {
      const newImported = { ...prevImported };

      // Add all created and updated items to the imported items
      for (const entityName of Object.keys(allCreatedItems)) {
        if (allCreatedItems[entityName].length > 0 || allUpdatedItems[entityName].length > 0) {
          // Combine created and updated items, removing duplicates by ID
          const combinedItems = [...allCreatedItems[entityName], ...allUpdatedItems[entityName]];

          // Remove duplicates and merge with existing imported items
          let entityIdField = entityName === 'application' ? 'app_id' : `${entityName}_id`;
          const existingItems = prevImported[entityName] || [];
          const existingIds = new Set(existingItems.map(item => item[entityIdField]));

          const newItems = combinedItems.filter(item => !existingIds.has(item[entityIdField]));
          newImported[entityName] = [...existingItems, ...newItems];
        }
      }

      return newImported;
    });

    // Add all collected errors to state at once
    const allErrors = [...allCreateErrors, ...allUpdateErrors, ...allRelationshipErrors];
    if (allErrors.length > 0) {
      setOutputCommitErrors(prev => [...prev, ...allErrors]);
    }

    setErrorFile([]);
    setErrors(0);
    setItems([]);
    setSelectedFile(null);
    setCommitted(true);

    console.debug("Final allErrors check:", allErrors.length, allErrors);
    if (allErrors.length > 0) {
      const errors = allErrors.map((errorItem) => (
        <ExpandableSection
          key={errorItem.itemType + " - " + errorItem.error}
          headerText={errorItem.itemType + " - " + errorItem.error}
        >
          {JSON.stringify(errorItem.item)}
        </ExpandableSection>
      ));

      console.debug("Adding error notification with", allErrors.length, "errors");
      addNotification({
        id: status.id,
        type: "error",
        dismissible: true,
        header: "Import of file '" + importName + "' had " + allErrors.length + " errors.",
        content: <ExpandableSection headerText="Error details">{errors}</ExpandableSection>,
      });
    } else {
      addNotification({
        id: status.id,
        type: "success",
        dismissible: true,
        header: "Import of " + importName + " successful.",
      });
    }
  }

  function getCurrentErrorMessage() {
    if (selectedFile && errorFile.length === 0) {
      return null;
    } else if (errorFile.length > 0) {
      return "Error with file : " + errorFile.join();
    } else {
      return "No file selected";
    }
  }

  function updateProcessingResultCounts(dataJson: any) {
    const errorCount = dataJson.data.reduce((accumulator: number, currentValue: { [x: string]: { errors: any[] } }) => {
      return currentValue["__validation"].errors
        ? accumulator + currentValue["__validation"].errors.length
        : accumulator;
    }, 0);
    setErrors(errorCount);

    const warningCount = dataJson.data.reduce(
      (accumulator: number, currentValue: { [x: string]: { warnings: any[] } }) => {
        return currentValue["__validation"].warnings
          ? accumulator + currentValue["__validation"].warnings.length
          : accumulator;
      },
      0
    );
    setWarnings(warningCount);

    const infromationalCount = dataJson.data.reduce(
      (accumulator: number, currentValue: { [x: string]: { informational: any[] } }) => {
        return currentValue["__validation"].informational
          ? accumulator + currentValue["__validation"].informational.length
          : accumulator;
      },
      0
    );
    setInformational(infromationalCount);
  }

  useEffect(() => {
    let dataJson: any = [];

    if (selectedFile) {
      (async () => {
        if (selectedFile.name.endsWith(".xlsx") || selectedFile.name.endsWith(".xls") || selectedFile.name.endsWith(".csv")) {
          dataJson = await convertDataFileToJSON(reader, selectedFile, selectedSheet);
        } else {
          //unsupported format of file.
          console.error(selectedFile.name + " - Unsupported file type.");
          setErrorFile(["Unsupported file type."]);
        }

        dataJson = removeNullKeys(dataJson);

        dataJson = performDataValidation(schemas, dataJson);

        const splitEntities = splitIntoEntities(dataJson.data, schemas);
        const mergedEntities = mergeDuplicates(splitEntities, schemas);

        // Update dataJson.data with the split entities
        dataJson.data = mergedEntities;

        const summary1 = getSummary(schemas, dataJson, dataAll);
        setSummary(summary1);

        updateProcessingResultCounts(dataJson);

        setItems(dataJson.data);
      })();
    }
  }, [selectedFile, selectedSheet]);

  const hideNoCommitModal = () => setNoCommitModalVisible(false);
  return (
    <>
      {
        <ImportIntakeWizard
          selectedFile={selectedFile}
          items={items}
          errors={errors}
          warnings={warnings}
          informational={informational}
          schema={schemas}
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
        />
      }

      <CMFModal onDismiss={hideNoCommitModal} visible={isNoCommitModalVisible} header={"Commit intake"}>
        Nothing to be committed!
      </CMFModal>
    </>
  );
};

export default UserImport;
