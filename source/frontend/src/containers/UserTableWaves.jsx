/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import User from "../actions/user";
import {useLocation, useNavigate, useParams} from "react-router-dom";
import {
  capitalize,
  exportTable,
  getChanges, getNestedValuePath, userAutomationActionsMenuItems
} from '../resources/main.js'

import { Auth } from "@aws-amplify/auth";


import {
  SpaceBetween,
  Link, StatusIndicator
} from '@awsui/components-react';

import ItemAmend from "../components/ItemAmend";
import WaveView from '../components/WaveView.jsx'
import AutomationTools from '../components/AutomationTools.jsx'
import ItemTable from '../components/ItemTable.jsx';
import { useModal } from '../actions/Modal.js';

import ToolsAPI from "../actions/tools";

//Hook imports
import {useAutomationJobs} from "../actions/AutomationJobsHook";
import { useMFApps } from "../actions/ApplicationsHook";
import { useGetServers } from "../actions/ServersHook.js";
import { useMFWaves } from "../actions/WavesHook.js";
import AllViewerAttributes from "../components/ui_attributes/AllViewerAttributes";
import Audit from "../components/ui_attributes/Audit";
import {parsePUTResponseErrors} from "../resources/recordFunctions";

const Viewer = (props) => {
  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');
  function getCurrentWaveApplications() {

    if (props.selectedItems.length === 1) {
      let apps = props.dataAll.application.data.filter(function (entry) {
        return entry.wave_id === props.selectedItems[0].wave_id;
      });

      if ( apps.length > 0){
        return apps;
      } else {
        return [];
      }
    }
  }

  function getCurrentWaveServers() {

    if (props.selectedItems.length === 1) {

      let apps = getCurrentWaveApplications();
      let servers = [];

      for(let item in apps) {
        let lservers = props.dataAll.server.data.filter(function (entry) {
          return entry.app_id === apps[item].app_id;
        });

        servers = servers.concat(lservers);
      }

      if ( servers.length > 0){
        return servers;
      } else {
        return [];
      }
    }
  }

  function getCurrentWaveJobs() {

    if (props.selectedItems.length === 1) {
      let jobs = props.dataAll.job.data.filter(function (entry) {
        //Return only jobs that have an argument with a Waveid matching the currently selected wave_id.
        if (entry.script.script_arguments) {
          return entry.script.script_arguments.Waveid === props.selectedItems[0].wave_id;
        } else
        {
          return false;
        }
      });

      if ( jobs.length > 0){
        return jobs;
      } else {
        return [];
      }
    }
  }

  async function handleViewerTabChange(tabselected)
  {
    setViewerCurrentTab(tabselected);
  }

  if (props.selectedItems.length === 1) {

    return (
      //<div></div>
      <WaveView {...props}
                wave={props.selectedItems[0]}
                dataAll={props.dataAll}
                apps={{items: getCurrentWaveApplications(), isLoading:  props.dataAll.application.isLoading, error: props.dataAll.application.error, handleSelectionChange: undefined}}
                servers={{items: getCurrentWaveServers(), isLoading:  props.dataAll.server.isLoading, error: props.dataAll.server.error, handleSelectionChange: undefined}}
                jobs={{items: getCurrentWaveJobs(), isLoading:  props.dataAll.job.isLoading, error: props.dataAll.job.error}}
                handleTabChange={handleViewerTabChange}
                selectedTab={viewerCurrentTab}
      />
    );
  } else {
    return (null);
  }
}

const UserWaveTable = (props) => {
  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();

  //Data items for viewer and table.
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, { update: updateWaves }] = useMFWaves();
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }, ] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, ] = useGetServers();
  const [{ isLoading: isLoadingJobs, data: dataJobs, error: errorJobs }, ] = useAutomationJobs();

  const dataAll = { job: {data: dataJobs, isLoading: isLoadingJobs, error: errorJobs}, application: {data: dataApps, isLoading: isLoadingApps, error: errorApps}, server: {data: dataServers, isLoading: isLoadingServers, error: errorServers}, wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}};

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState([]);
  const [focusItem, setFocusItem] = useState([]);

  //Viewer pane state management.
  const [action, setAction] = useState('View');
  const [actions, setActions] = useState([]); //Actions menu dropdown options.
  const [automationAction, setAutomationAction] = useState(undefined);
  const [focusSubItem, setFocusSubItem] = useState(undefined);

  const [preformingAction, setPreformingAction] = useState(false);

  //Get base path from the URL, all actions will use this base path.
  const basePath = location.pathname.split('/').length >= 2 ? '/' + location.pathname.split('/')[1] : '/';
  //Key for main item displayed in table.
  const itemIDKey = 'wave_id';
  const schemaName = 'wave';

  //Modals
  const { show: showDeleteConfirmaton, hide: hideDeleteConfirmaton, RenderModal: DeleteModal } = useModal();
  const { show: showLinkedRecord, hide: hideLinkedRecord, RenderModal: LinkedRecordModal } = useModal();

  function handleNotification(notification)
  {
    return props.updateNotification('add', notification)
  }

  async function handleRefreshClick(e) {
    e.preventDefault();
    await updateWaves();
  }

  function handleAddItem()
  {
   navigate({
      pathname: basePath + '/add'
    })
    setAction('Add')
    setFocusItem({});
  }

  function handleDownloadItems()
  {
    if (selectedItems.length > 0 ) {
      // Download selected only.
      exportTable(selectedItems, "Waves", "waves")
    } else {
      //Download all.
      exportTable(dataWaves, "Waves", "waves")
    }
  }

  function handleEditItem(selection = null)
  {
    if ( selectedItems.length === 1) {
     navigate({
        pathname: basePath + '/edit/' + selectedItems[0][itemIDKey]
      })
      setAction('Edit')
      setFocusItem(selectedItems[0]);
    } else if ( selection ) {
     navigate({
        pathname: basePath + '/edit/' + selection[itemIDKey]
      })
      setFocusItem(selection);
      setAction('Edit');
    }

  }

  function handleResetScreen()
  {
   navigate({
      pathname: basePath
    })
    setAction('View');
  }

  function handleItemSelectionChange(selection) {

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

  async function handleAction(actionData, actionId) {

    setPreformingAction(true);

    let newItem = Object.assign({}, actionData);
    let notificationId = null;

    let apiAction = props.schema[automationAction].actions.filter(function (entry) {
      return entry.id === actionId;
    });

    if (apiAction.length !== 1) {
      handleNotification({
        type: 'error',
        dismissible: true,
        header: "Perform wave action",
        content: props.schema[automationAction].friendly_name + ' action [' & actionId & '] not found in schema.',
      });
    } else {

      try {

        if (apiAction[0].additionalData){
          const keys = Object.keys(apiAction[0].additionalData);
          for (const i in keys){
            newItem[keys[i]] = apiAction[0].additionalData[keys[i]]
          }
        }

        notificationId = handleNotification({
          type: 'success',
          loading: true,
          dismissible: false,
          header: "Perform wave action",
          content: "Performing action - " + apiAction[0].name,
        });

        const session = await Auth.currentSession();
        const apiTools = await new ToolsAPI(session);
        const response  = await apiTools.postTool(apiAction[0].apiPath, newItem);
        console.log(response)

        //Extra UUID from response.
        let uuid = response.split('+');
        if (uuid.length > 1){
          uuid = uuid[1];
          await handleResetScreen();

          handleNotification({
            id: notificationId,
            type: 'success',
            dismissible: true,
            header: "Perform wave action",
            actionButtonTitle: "View Job",
            actionButtonLink: "/automation/jobs/" + uuid,
            content: apiAction[0].name + " action successfully.",
          });
        } else {
          await handleResetScreen();

          handleNotification({
            id: notificationId,
            type: 'success',
            dismissible: true,
            header: "Perform wave action",
            content: response,
          });
        }


      } catch (e) {
        console.log(e);
        if ('response' in e) {
          if(e.response != null && typeof e.response === 'object') {
            if ('data' in e.response) {
              handleNotification({
                id: notificationId,
                type: 'error',
                dismissible: true,
                header: "Perform wave action1",
                content: apiAction[0].name + ' action failed: ' + (e.response.data.cause ? e.response.data.cause : e.response.data)
              });
            }
          } else {
            handleNotification({
              id: notificationId,
              type: 'error',
              dismissible: true,
              header: "Perform wave action2",
              content: apiAction[0].name + ' action failed: ' + e.message
            });
          }
        } else {
          handleNotification({
            id: notificationId,
            type: 'error',
            dismissible: true,
            header: "Perfrom wave action",
            content: apiAction[0].name + ' action failed: Unknown error occured',
          });
        }
      }
    }

    setPreformingAction(false);

  }

  async function  handleSave(editItem, action) {

    let newItem = Object.assign({}, editItem);
    try {
      if (action === 'Edit') {
        let wave_id = newItem.wave_id;
        let wave_ref = newItem.wave_name;
        newItem = getChanges(newItem, dataWaves, "wave_id");
        if(!newItem){
          // no changes to original record.
          handleNotification({
            type: 'warning',
            dismissible: true,
            header: "Save " + schemaName,
            content: "No updates to save."
          });
          return false;
        }
        delete newItem.wave_id;
        const session = await Auth.currentSession();
        const apiUser = new User(session);
        let resultEdit = await apiUser.putItem(wave_id, newItem, 'wave');

        if (resultEdit['errors']) {
          console.debug("PUT " + schemaName + " errors");
          console.debug(resultEdit['errors']);
          let errorsReturned = parsePUTResponseErrors(resultEdit['errors']);
          handleNotification({
            type: 'error',
            dismissible: true,
            header: "Update " + schemaName,
            content: (errorsReturned)
          });
        } else {

          handleNotification({
            type: 'success',
            dismissible: true,
            header: "Update " + schemaName,
            content: wave_ref + " updated successfully.",
          });

          updateWaves();
          handleResetScreen();

          //This is needed to ensure the item in selectItems reflects new updates
          setSelectedItems([]);
          setFocusItem({});
        }
      }
      else {

        const session = await Auth.currentSession();
        const apiUser = new User(session);
        delete newItem.wave_id;
        let resultAdd = await apiUser.postItem(newItem, 'wave');

        if (resultAdd['errors']) {
          console.debug("PUT " + schemaName + " errors");
          console.debug(resultAdd['errors']);
          let errorsReturned = parsePUTResponseErrors(resultAdd['errors']);
          handleNotification({
            type: 'error',
            dismissible: true,
            header: "Add " + schemaName,
            content: (errorsReturned)
          });
        } else {
          handleNotification({
            type: 'success',
            dismissible: true,
            header: "Add " + schemaName,
            content: newItem.wave_name + " added successfully.",
          });
          updateWaves();
          handleResetScreen();
        }
      }

    } catch (e) {
      console.error(e);
      let response = '';
      if ('response' in e && 'data' in e.response) {
        //Check if errors key exists from Lambda errors.
        if (e.response.data.errors)
        {
          response = e.response.data.errors;
          response = parsePUTResponseErrors(response);
        } else if (e.response.data.cause){
          response = e.response.data.cause;
        } else {
          response = 'Unknown error occurred.';
        }
      } else {
        response = 'Unknown error occurred.';
      }

      handleNotification({
        type: 'error',
        dismissible: true,
        header: "Save " + schemaName,
        content: (response)
      });
    }
  }

  async function handleDeleteItemClick(e) {
    e.preventDefault();
    showDeleteConfirmaton();
  }

  async function handleActionsClick(e) {
    e.preventDefault();

    let action = e.detail.id;

    setFocusItem(selectedItems);
    setAutomationAction(action);
    setAction('Action');
  }

  async function handleDeleteItem(e) {
    e.preventDefault();

    await hideDeleteConfirmaton();

    let currentItem = 0;
    let multiReturnMessage = [];
    let notificationId;

    try {
      const session = await Auth.currentSession();
      const apiUser = new User(session);

      if(selectedItems.length > 1) {
        notificationId = handleNotification({
          type: 'success',
          loading: true,
          dismissible: false,
          header: "Deleting selected " + schemaName + "s..."
        });
      }
      for(let item in selectedItems) {
        currentItem = item;
        await apiUser.deleteItem(selectedItems[item].wave_id, 'wave');
        //Combine notifications into a single message if multi selected used, to save user dismiss clicks.
        if(selectedItems.length > 1){
          multiReturnMessage.push(selectedItems[item].wave_name);
        } else {
          handleNotification({
            type: 'success',
            dismissible: true,
            header: 'Wave deleted successfully',
            content: selectedItems[item].wave_name + ' was deleted.'
          });
        }
      }

      //Create notification where multi select was used.
      if(selectedItems.length > 1){
        handleNotification({
          id: notificationId,
          type: 'success',
          dismissible: true,
          header: 'Waves deleted successfully',
          content: multiReturnMessage.join(", ") + ' were deleted.'
        });
      }

      //Unselect applications marked for deletion to clear apps.

      setSelectedItems([]);
      await updateWaves();

    } catch (e) {
      console.error(e);
      let response = '';
      if ('response' in e && 'data' in e.response) {
        //Check if errors key exists from Lambda errors.
        if (e.response.data.errors)
        {
          response = e.response.data.errors;
        } else if (e.response.data.cause){
          response = e.response.data.cause;
        } else {
          response = selectedItems[currentItem].wave_name + ' failed to delete with an unknown error.';
        }
      } else {
        response = selectedItems[currentItem].wave_name + ' failed to delete with an unknown error.';
      }

      handleNotification({
        type: 'error',
        dismissible: true,
        header: "Wave deletion failed",
        content: (response)
      });
    }
  }

  //Update actions button options on schema change.
  useEffect( () => {

    if(!props.schemaIsLoading && props.isReady){

      setActions(userAutomationActionsMenuItems(props.schema, props.userEntityAccess));
    }
  },[props.schema, props.userEntityAccess]);

  //Update help tools panel.
  useEffect(() => {
    if (props.schema && props.schema[schemaName].help_content) {
      let tempContent = props.schema[schemaName].help_content;
      tempContent.header = props.schema[schemaName].friendly_name ? props.schema[schemaName].friendly_name : capitalize(schemaName);
      props.setHelpPanelContent(tempContent)
    }
  }, [props.schema]);

  function provideContent(currentAction){

    if(props.schemaIsLoading || !props.isReady){
      return (
        <StatusIndicator type="loading">
          Loading schema...
        </StatusIndicator>
      )
    }

    switch (currentAction) {
      case 'Action':
        return (
          <AutomationTools action={action} schemaName={automationAction} schema={props.schema[automationAction]} userAccess={props.userEntityAccess} schemas={props.schema} performingAction={preformingAction} selectedItems={focusItem} handleAction={handleAction} handleCancel={handleResetScreen} updateNotification={handleNotification}/>
        )
      case 'Add':
      case 'Edit':
        return (
          <ItemAmend action={action} schemaName={schemaName} schemas={props.schema} userAccess={props.userEntityAccess} item={focusItem} handleSave={handleSave} handleCancel={handleResetScreen} updateNotification={handleNotification} setHelpPanelContent={props.setHelpPanelContent}/>
        )
      default:
        return (
          <SpaceBetween direction="vertical" size="xs">
            <ItemTable
              sendNotification={handleNotification}
              schema={props.schema[schemaName]}
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
              handleDeleteItem={handleDeleteItemClick}
              handleEditItem={handleEditItem}
              handleDownloadItems={handleDownloadItems}
              userAccess={props.userEntityAccess}
              setHelpPanelContent={props.setHelpPanelContent}
              />
            <Viewer
              {...props}
              selectedItems={selectedItems}
              dataAll={dataAll}
            />
          </SpaceBetween>
        )

    }

  }

  useEffect( () => {
    let selected = [];

    if (!isLoadingWaves) {

      let item = dataWaves.filter(function (entry) {
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
      <DeleteModal title={'Delete waves'} onConfirmation={handleDeleteItem}>{selectedItems.length === 1 ? <p>Are you sure you wish to delete the selected wave?</p> : <p>Are you sure you wish to delete the {selectedItems.length} selected waves?</p>}</DeleteModal>
      <LinkedRecordModal title={'Quick View'} noCancel={true} onConfirmation={hideLinkedRecord}>
            <SpaceBetween size="l">
              <Link
                external
                externalIconAriaLabel="Opens record for editing in a new tab"
                href={focusSubItem ? '/' + focusSubItem.schema + 's/edit/' + focusSubItem.recordId : ''}
              >
                Edit
              </Link>
              <AllViewerAttributes
                schema={focusSubItem ? getNestedValuePath(props.schema, focusSubItem.schema) : undefined}
                schemas={props.schema}
                item={focusSubItem ? focusSubItem.item : undefined}
                dataAll={props.dataAll}
              />
              <Audit item={focusSubItem ? focusSubItem : undefined} expanded={true}/>
            </SpaceBetween>
      </LinkedRecordModal>
    </div>
  );
};

// Component TableView is a skeleton of a Table using AWS-UI React components.
export default UserWaveTable;
