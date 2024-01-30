/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useContext, useEffect, useState} from 'react';
import UserApiClient from "../api_clients/userApiClient";
import {useLocation, useNavigate, useParams} from "react-router-dom";
import {getChanges, userAutomationActionsMenuItems} from '../resources/main'
import {exportTable} from "../utils/xlsx-export";

import {SpaceBetween} from '@awsui/components-react';

import ItemAmend from "../components/ItemAmend";
import {WaveDetailsView} from '../components/WaveView'
import AutomationTools from '../components/AutomationTools'
import ItemTable from '../components/ItemTable';

import ToolsApiClient from "../api_clients/toolsApiClient";

import {useAutomationJobs} from "../actions/AutomationJobsHook";
import {useMFApps} from "../actions/ApplicationsHook";
import {useGetServers} from "../actions/ServersHook";
import {useMFWaves} from "../actions/WavesHook";
import {apiActionErrorHandler, parsePUTResponseErrors} from "../resources/recordFunctions";
import {ClickEvent} from "../models/Events";
import {NotificationContext} from "../contexts/NotificationContext";
import {EntitySchema} from "../models/EntitySchema";
import {ToolsContext} from "../contexts/ToolsContext";
import {CMFModal} from "../components/Modal";

type UserWaveTableParams = {
  userEntityAccess: any;
  schemas: Record<string, EntitySchema>;
};
const UserWaveTable = ({schemas, userEntityAccess}: UserWaveTableParams) => {
  const {addNotification} = useContext(NotificationContext);
  const {setHelpPanelContentFromSchema} = useContext(ToolsContext);

  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();

  //Data items for viewer and table.
  const [{isLoading: isLoadingWaves, data: dataWaves, error: errorWaves}, {update: updateWaves}] = useMFWaves();
  const [{isLoading: isLoadingApps, data: dataApps, error: errorApps},] = useMFApps();
  const [{isLoading: isLoadingServers, data: dataServers, error: errorServers},] = useGetServers();
  const [{isLoading: isLoadingJobs, data: dataJobs, error: errorJobs}] = useAutomationJobs();

  const dataAll = {
    job: {data: dataJobs, isLoading: isLoadingJobs, error: errorJobs},
    application: {data: dataApps, isLoading: isLoadingApps, error: errorApps},
    server: {data: dataServers, isLoading: isLoadingServers, error: errorServers},
    wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}
  };

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<Array<any>>([]);
  const [focusItem, setFocusItem] = useState<any>([]);

  //Viewer pane state management.
  const [action, setAction] = useState('View');
  const [actions, setActions] = useState<any[]>([]); //Actions menu dropdown options.
  const [automationAction, setAutomationAction,] = useState<string | undefined>(undefined);
  const [focusSubItem, setFocusSubItem] = useState<any>(undefined);

  const [preformingAction, setPreformingAction] = useState(false);

  //Get base path from the URL, all actions will use this base path.
  const basePath = location.pathname.split('/').length >= 2 ? '/' + location.pathname.split('/')[1] : '/';
  //Key for main item displayed in table.
  const itemIDKey = 'wave_id';
  const schemaName = 'wave';

  //Modals
  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);

  async function handleRefreshClick(e: ClickEvent) {
    e.preventDefault();
    await updateWaves();
  }

  function handleAddItem() {
    navigate({
      pathname: basePath + '/add'
    })
    setAction('Add')
    setFocusItem({});
  }

  function handleDownloadItems() {
    if (selectedItems.length > 0) {
      // Download selected only.
      exportTable(selectedItems, "Waves", "waves")
    } else {
      //Download all.
      exportTable(dataWaves, "Waves", "waves")
    }
  }

  function handleEditItem(selection = null) {
    if (selectedItems.length === 1) {
      navigate({
        pathname: basePath + '/edit/' + selectedItems[0][itemIDKey]
      })
      setAction('Edit')
      setFocusItem(selectedItems[0]);
    } else if (selection) {
      navigate({
        pathname: basePath + '/edit/' + selection[itemIDKey]
      })
      setFocusItem(selection);
      setAction('Edit');
    }

  }

  function handleResetScreen() {
    navigate({
      pathname: basePath
    })
    setAction('View');
  }

  function handleItemSelectionChange(selection: Array<any>) {

    setSelectedItems(selection);
    if (selection.length === 1) {

      //TO-DO Need to pull in Waves or other data here.
      //updateApps(selection[0].app_id);

    }
    //Reset URL to base table path.
    navigate({
      pathname: basePath
    })

  }

  async function handleAction(actionData: any, actionId: number) {

    if (!automationAction) return;

    setPreformingAction(true);

    let newItem = Object.assign({}, actionData);
    let notificationId;

    let apiAction = schemas[automationAction].actions?.filter((entry: { id: number; }) => entry.id === actionId) ?? [];

    if (apiAction.length !== 1) {
      addNotification({
        type: 'error',
        dismissible: true,
        header: "Perform wave action",
        content: schemas[automationAction].friendly_name + ' action [' + actionId + '] not found in schema.',
      })
    } else {

      try {

        if (apiAction[0].additionalData) {
          const keys = Object.keys(apiAction[0].additionalData);
          for (const i in keys) {
            newItem[keys[i]] = apiAction[0].additionalData[keys[i]]
          }
        }

        notificationId = addNotification({
          type: 'success',
          loading: true,
          dismissible: false,
          header: "Perform wave action",
          content: "Performing action - " + apiAction[0].name,
        });

        const apiTools = new ToolsApiClient();
        const response = await apiTools.postTool(apiAction[0].apiPath, newItem);

        //Extra UUID from response.
        let uuid = response.split('+');
        if (uuid.length > 1) {
          uuid = uuid[1];
          handleResetScreen();

          addNotification({
            id: notificationId,
            type: 'success',
            dismissible: true,
            header: "Perform wave action",
            actionButtonTitle: "View Job",
            actionButtonLink: "/automation/jobs/" + uuid,
            content: apiAction[0].name + " action successfully.",
          })
        } else {
          handleResetScreen();

          addNotification({
            id: notificationId,
            type: 'success',
            dismissible: true,
            header: "Perform wave action",
            content: response,
          })
        }


      } catch (e: any) {
        console.log(e);
        const content = apiAction[0].name + ' action failed: ' + (e.response.data?.cause ||
          e.response.data || e.message || "action failed: Unknown error occurred");

        addNotification({
          id: notificationId,
          type: 'error',
          dismissible: true,
          header: "Perform wave action",
          content: content
        })
      }
    }

    setPreformingAction(false);

  }

  async function handleSave(editItem: any, action: string): Promise<void> {

    let newItem = Object.assign({}, editItem);
    try {
      if (action === 'Edit') {
        let wave_id = newItem.wave_id;
        let wave_ref = newItem.wave_name;
        newItem = getChanges(newItem, dataWaves, "wave_id");
        if (!newItem) {
          // no changes to original record.
          addNotification({
            type: 'warning',
            dismissible: true,
            header: "Save " + schemaName,
            content: "No updates to save."
          })
          return;
        }
        delete newItem.wave_id;
        const apiUser = new UserApiClient();
        let resultEdit = await apiUser.putItem(wave_id, newItem, 'wave');

        if (resultEdit['errors']) {
          console.debug("PUT " + schemaName + " errors");
          console.debug(resultEdit['errors']);
          let errorsReturned = parsePUTResponseErrors(resultEdit['errors']).join(',');
          addNotification({
            type: 'error',
            dismissible: true,
            header: "Update " + schemaName,
            content: (errorsReturned)
          })
        } else {

          addNotification({
            type: 'success',
            dismissible: true,
            header: "Update " + schemaName,
            content: wave_ref + " updated successfully.",
          })

          updateWaves();
          handleResetScreen();

          //This is needed to ensure the item in selectItems reflects new updates
          setSelectedItems([]);
          setFocusItem({});
        }
      } else {
        const apiUser = new UserApiClient();
        delete newItem.wave_id;
        let resultAdd = await apiUser.postItem(newItem, 'wave');

        if (resultAdd['errors']) {
          console.debug("PUT " + schemaName + " errors");
          console.debug(resultAdd['errors']);
          let errorsReturned = parsePUTResponseErrors(resultAdd['errors']).join(',');
          addNotification({
            type: 'error',
            dismissible: true,
            header: "Add " + schemaName,
            content: (errorsReturned)
          })
        } else {
          addNotification({
            type: 'success',
            dismissible: true,
            header: "Add " + schemaName,
            content: newItem.wave_name + " added successfully.",
          })
          updateWaves();
          handleResetScreen();
        }
      }

    } catch (e: any) {
      apiActionErrorHandler(action, schemaName, e, addNotification);
    }
  }

  async function handleActionsClick(e: ClickEvent) {
    let action = e.detail.id;

    setFocusItem(selectedItems);
    setAutomationAction(action);
    setAction('Action');
  }

  async function handleDeleteItem() {
    setDeleteConfirmationModalVisible(false);

    let currentItem: any = 0;
    let multiReturnMessage = [];
    let notificationId;

    try {
      const apiUser = new UserApiClient();

      if (selectedItems.length > 1) {
        notificationId = addNotification({
          type: 'success',
          loading: true,
          dismissible: false,
          header: "Deleting selected " + schemaName + "s..."
        });
      }
      for (let item in selectedItems) {
        currentItem = item;
        await apiUser.deleteItem(selectedItems[item].wave_id, 'wave');
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if (selectedItems.length > 1) {
          multiReturnMessage.push(selectedItems[item].wave_name);
        } else {
          addNotification({
            type: 'success',
            dismissible: true,
            header: 'Wave deleted successfully',
            content: selectedItems[item].wave_name + ' was deleted.'
          })
        }
      }

      //Create notification where multi select was used.
      if (selectedItems.length > 1) {
        addNotification({
          id: notificationId,
          type: 'success',
          dismissible: true,
          header: 'Waves deleted successfully',
          content: multiReturnMessage.join(", ") + ' were deleted.'
        })
      }

      //Unselect applications marked for deletion to clear apps.

      setSelectedItems([]);
      await updateWaves();

    } catch (e: any) {
      console.error(e);
      let response = e.response?.data?.errors
        || e.response?.data?.cause
        || selectedItems[currentItem].wave_name + ' failed to delete with an unknown error.';

      addNotification({
        type: 'error',
        dismissible: true,
        header: "Wave deletion failed",
        content: (response)
      })
    }
  }

  //Update actions button options on schema change.
  useEffect(() => {
    setActions(userAutomationActionsMenuItems(schemas, userEntityAccess));

  }, [schemas, userEntityAccess]);

  //Update help tools panel.
  useEffect(() => {
    setHelpPanelContentFromSchema(schemas, schemaName);
  }, [schemas]);

  function provideContent(currentAction: string) {

    switch (currentAction) {
      case 'Action':
        if (!automationAction) return <></>
        return (
          <AutomationTools
            schemaName={automationAction}
            schema={schemas[automationAction]}
            userAccess={userEntityAccess}
            schemas={schemas}
            performingAction={preformingAction}
            selectedItems={focusItem}
            handleAction={handleAction}
            handleCancel={handleResetScreen}/>
        )
      case 'Add':
      case 'Edit':
        return (
          <ItemAmend
            action={action}
            schemaName={schemaName}
            schemas={schemas}
            userAccess={userEntityAccess}
            item={focusItem}
            handleSave={handleSave}
            handleCancel={handleResetScreen}
          />
        )
      default:
        return (
          <SpaceBetween direction="vertical" size="xs">
            <ItemTable
              schema={schemas[schemaName]}
              schemaKeyAttribute={itemIDKey}
              schemaName={schemaName}
              dataAll={dataAll}
              items={dataWaves}
              selectedItems={selectedItems}
              handleSelectionChange={handleItemSelectionChange}
              isLoading={isLoadingWaves}
              errorLoading={errorWaves}
              handleRefreshClick={handleRefreshClick}
              handleAddItem={handleAddItem}
              handleAction={handleActionsClick}
              actionItems={actions}
              handleDeleteItem={async function () {
                setDeleteConfirmationModalVisible(true);
              }}
              handleEditItem={handleEditItem}
              handleDownloadItems={handleDownloadItems}
              userAccess={userEntityAccess}
            />
            <WaveDetailsView
              schemas={schemas}
              selectedItems={selectedItems}
              dataAll={dataAll}
            />
          </SpaceBetween>
        )

    }

  }

  useEffect(() => {
    let selected = [];

    if (!isLoadingWaves) {

      let item = dataWaves.filter(function (entry: { [x: string]: string | undefined; }) {
        return entry[itemIDKey] === params.id;
      });

      if (item.length === 1) {
        selected.push(item[0]);
        handleItemSelectionChange(selected);
        //Check if URL contains edit path and switch to amend component.
        if (location.pathname && location.pathname.match('/edit/')) {
          handleEditItem(item[0]);
        }
      } else if (location.pathname && location.pathname.match('/add')) {
        //Add url used, redirect to add screen.
        handleAddItem();
      }
    }

  }, [dataWaves]);

  return (
    <div>
      {provideContent(action)}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={'Delete waves'}
      >
        <p>Are you sure you wish to delete the {selectedItems.length} selected waves?</p>
      </CMFModal>
    </div>
  );
};
export default UserWaveTable;
