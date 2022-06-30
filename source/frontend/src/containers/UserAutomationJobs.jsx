import React, {useEffect, useState} from 'react';
import {useLocation, useNavigate, useParams} from "react-router-dom";

import {
  Button,
  SpaceBetween,
  StatusIndicator
} from '@awsui/components-react';

import AutomationJobView from '../components/AutomationJobView.jsx'
import { useAutomationJobs } from "../actions/AutomationJobsHook.js";
import { useGetServers } from "../actions/ServersHook.js";
import { useMFWaves } from "../actions/WavesHook.js";
import ItemTable from '../components/ItemTable.jsx';
import { useModal } from '../actions/Modal.js';
import {useMFApps} from "../actions/ApplicationsHook";
import AutomationTools from '../components/AutomationTools.jsx'
import {Auth} from "aws-amplify";
import ToolsAPI from "../actions/tools";
import {userAutomationActionsMenuItems} from "../resources/main";
import {useAutomationScripts} from "../actions/AutomationScriptsHook";
import {useCredentialManager} from "../actions/CredentialManagerHook";

const AutomationJobs = (props) => {
  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();
  //Data items for viewer and table.
  //Main table content hook. When duplicating just create a new hook and change the hook function at the end to populate table.
  const [{ isLoading: isLoadingMain, data: dataMain, error: errorMain }, {update: updateMain } ] = useAutomationJobs();
  const [{ isLoading: isLoadingApps, data: dataApps, error: errorApps }, {update: updateApps, deleteApplications: deleteApp} ] = useMFApps();
  const [{ isLoading: isLoadingServers, data: dataServers, error: errorServers }, {update: updateServers} ] = useGetServers();
  const [{ isLoading: isLoadingWaves, data: dataWaves, error: errorWaves }, { update: updateWaves }] = useMFWaves();
  const [{ isLoading: isLoadingScripts, data: dataScripts, error: errorScripts }, {update: updateScripts } ] = useAutomationScripts();
  const [{ isLoading: isLoadingSecrets, data: dataSecrets, error: errorSecrets }, { updateSecrets }] = useCredentialManager();

  const dataAll = {secret: {data: dataSecrets, isLoading: isLoadingSecrets, error: errorSecrets},script: {data: dataScripts, isLoading: isLoadingScripts, error: errorScripts},jobs: {data: dataMain, isLoading: isLoadingMain, error: errorMain},wave: {data: dataWaves, isLoading: isLoadingWaves, error: errorWaves}};

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState([]);
  const [focusItem, setFocusItem] = useState([]);

  //Add Job/Action state management.
  const [automationAction, setAutomationAction] = useState(undefined);
  const [preformingAction, setPreformingAction] = useState(false);

  //Viewer pane state management.
  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');
  const [action, setAction] = useState(['Add']);
  const [actions, setActions] = useState([]);

  //Get base path from the URL, all actions will use this base path.
  const basePath = '/automation/jobs'
  //Key for main item displayed in table.
  const itemIDKey = 'uuid';
  const schemaName = 'job';

  //Get schema for Automation jobs.
  // let schemaSSMAttribs = undefined;
  // let schemaSSM = [];

  // if (!props.schemaIsLoading) {
  //   schemaSSM = props.schema.automation.filter(function (entry) {
  //     return entry.schema_name === schemaName;
  //   });
  // }
  //
  // if (schemaSSM.length === 1) {
  //   schemaSSMAttribs = schemaSSM[0].attributes;
  // }

  //Modals
  const { show: showDeleteConfirmaton, hide: hideDeleteConfirmaton, RenderModal: DeleteModal } = useModal()

  function handleNotification(notification)
  {
    return props.updateNotification('add', notification)
  }

  async function handleRefreshClick(e) {
    e.preventDefault();
    await updateMain();
  }

  function handleAddItem()
  {
    navigate({
      pathname: basePath + '/add'
    })
    setAction('Add')
    setFocusItem({});
    setEditingItem(true);

  }

  function handleEditItem(selection = null)
  {
    if ( selectedItems.length === 1) {
      navigate({
        pathname: basePath + '/edit/' + selectedItems[0][itemIDKey]
      })
      setAction('Edit')
      setFocusItem(selectedItems[0]);
      setEditingItem(true);
    } else if ( selection ) {
      navigate({
        pathname: basePath + '/edit/' + selection[itemIDKey]
      })
      setAction('Edit');
      setFocusItem(selection);
      setEditingItem(true);
    }

  }

  async function handleViewerTabChange(tabselected)
  {
      setViewerCurrentTab(tabselected);
  }

  function handleResetScreen()
  {
    navigate({
      pathname: basePath
    });

    setAction('View');

    setEditingItem(false);
  }

  function handleItemSelectionChange(selection) {

    setSelectedItems(selection);

    //Reset URL to base table path.
    navigate({
      pathname: basePath
    })

  }

  function getCurrentApplicationWave() {

    if (selectedItems[0].wave_id) {
      if (selectedItems.length === 1) {
        let waves = dataWaves.filter(function (entry) {
          return entry.wave_id === selectedItems[0].wave_id;
        });

        if (waves.length === 1) {
          return waves[0];
        } else {
          return {};
        }
      }
    } else {
      return {};
    }

  }

  const ViewAutomationJob = (props) => {

    if (selectedItems.length === 1) {

      return (
        <AutomationJobView
            item={selectedItems[0]}
            schema={props.schema['job']}
            schemas={props.schema}
            dataAll={dataAll}
            handleTabChange={handleViewerTabChange}
            selectedTab={viewerCurrentTab}
          />
      );
    } else {
      return (null);
    }
  }

  async function handleActionsClick(e) {
    e.preventDefault();

    let action = e.detail.id;

    setFocusItem(selectedItems);
    setAutomationAction(action);
    setAction('Action');
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
          for (var i in keys){
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



        await updateMain();

      } catch (e) {
        console.log(e);
        if ('response' in e) {
          if(e.response != null && typeof e.response === 'object') {
            if ('data' in e.response) {
              handleNotification({
                id: notificationId,
                type: 'error',
                dismissible: true,
                header: "Perform wave action",
                content: apiAction[0].name + ' action failed: ' + e.response.data
              });
            }
          } else {
            handleNotification({
              id: notificationId,
              type: 'error',
              dismissible: true,
              header: "Perform wave action",
              content: apiAction[0].name + ' action failed: ' + e.message
            });
          }
        } else {
          handleNotification({
            id: notificationId,
            type: 'error',
            dismissible: true,
            header: "Perform wave action",
            content: apiAction[0].name + ' action failed: Unknown error occured',
          });
        }
      }
    }

    setPreformingAction(false);

  }

  //Update actions button options on schema change.
  useEffect( () => {

    if(!props.schemaIsLoading && props.isReady){

      setActions(userAutomationActionsMenuItems(props.schema, props.userEntityAccess));
    }
  },[props.schema, props.userEntityAccess]);

  useEffect( () => {
    let selected = [];

    if (!isLoadingMain) {
      if (params.id) {
        //URL parameter present.
        let item = dataMain.filter(function (entry) {
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
    }

  }, [dataMain]);


  //Detect changes to main data table content and if an item was previously selected and in the viewer, refresh the item
  //content.
  useEffect( () => {
    let selected = [];

    if (!isLoadingMain) {
      if (selectedItems.length == 1) {
        //Refresh selected item.
        let item = dataMain.filter(function (entry) {
          return entry[itemIDKey] === selectedItems[0][itemIDKey];
        });

        if (item.length === 1) {
          //Previous Item found in new data, reload into selected items.
          selected.push(item[0]);
          handleItemSelectionChange(selected);
        } else {
          //Item no longer available.
          handleItemSelectionChange(selected);
        }
      }
    }

  }, [dataMain]);

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
          <AutomationTools action={action} schema={props.schema[automationAction]} schemas={props.schema} schemaName={schemaName} userAccess={props.userEntityAccess} performingAction={preformingAction} selectedItems={focusItem} handleAction={handleAction} handleCancel={handleResetScreen} updateNotification={handleNotification}/>
        )
      default:
        return <SpaceBetween direction="vertical" size="xs">
          <ItemTable
            sendNotification={handleNotification}
            schema={props.schema['job']}
            schemaKeyAttribute={itemIDKey}
            schemaName={schemaName}
            dataAll={dataAll}
            items={dataMain}
            selectedItems={selectedItems}
            handleSelectionChange={handleItemSelectionChange}
            actionsButtonDisabled={false}
            selectionType={'single'}
            actionItems={actions}
            handleAction={handleActionsClick}
            isLoading={isLoadingMain}
            errorLoading={errorMain}
            handleRefreshClick={handleRefreshClick}
            userAccess={props.userEntityAccess}
          />
          <ViewAutomationJob {...props}/>
        </SpaceBetween>
    }

  }

  return provideContent(action);
};

export default AutomationJobs;
