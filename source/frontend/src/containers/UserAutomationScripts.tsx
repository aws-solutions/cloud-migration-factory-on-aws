/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useContext, useEffect, useState} from 'react';
import {useLocation, useNavigate, useParams} from "react-router-dom";
import {toBase64} from '../resources/main'

import {
  Alert,
  Button,
  Container,
  FormField,
  Header,
  Input,
  Select,
  SpaceBetween,
  StatusIndicator
} from '@awsui/components-react';


import AutomationScriptView from '../components/AutomationScriptView'
import {useAutomationScripts} from "../actions/AutomationScriptsHook";
import AutomationScriptsTable from '../components/AutomationScriptsTable';
import AutomationScriptImport from "../components/AutomationScriptImport";
import ToolsAPI from "../api_clients/toolsApiClient";
import {ClickEvent} from "../models/Events";
import {OptionDefinition} from "@awsui/components-react/internal/components/option/interfaces";
import {NotificationContext} from "../contexts/NotificationContext";
import {EntitySchema} from "../models/EntitySchema";

const ViewAutomationScript = (props: { selectedItems: any[]; dataAll: any; schema: EntitySchema }) => {

  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');

  if (props.selectedItems.length === 1) {

    return (
      <AutomationScriptView
        schema={props.schema}
        item={props.selectedItems[0]}
        dataAll={props.dataAll}
        handleTabChange={setViewerCurrentTab}
        selectedTab={viewerCurrentTab}
      />
    );
  } else {
    return null;
  }
}

type AutomationScriptsParams = {
  userEntityAccess: { [x: string]: { create: any; }; };
  schemas: Record<string, EntitySchema>;
  schemaIsLoading?: boolean;
};
const AutomationScripts = (props: AutomationScriptsParams) => {
  const {addNotification} = useContext(NotificationContext);
  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();
  //Data items for viewer and table.
  //Main table content hook. When duplicating just create a new hook and change the hook function at the end to populate table.
  const [{isLoading: isLoadingMain, data: dataMain, error: errorMain}, {update: updateMain}] = useAutomationScripts();

  const dataAll = {jobs: {data: dataMain, isLoading: isLoadingMain, error: errorMain}};

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [focusItem, setFocusItem] = useState<any>([]);

  //Viewer pane state management.

  const [action, setAction] = useState('Add');

  const [newDefaultVersion, setNewDefaultVersion] = useState<string | undefined>('');

  //Get base path from the URL, all actions will use this base path.
  const basePath = '/automation/scripts'
  //Key for main item displayed in table.
  const itemIDKey = 'package_uuid';

  async function handleRefreshClick() {
    await updateMain();
    refreshSelectedItems();
  }

  function refreshSelectedItems() {
    // Search for previously selected items, and update based on refreshed data.
    let updatedItems = []
    if (selectedItems.length > 0) {
      for (const selectedItem of selectedItems) {
        const findResult = dataMain.find((item: { [x: string]: any; }) => item[itemIDKey] === selectedItem[itemIDKey])

        if (findResult) {
          updatedItems.push(findResult);
        }
      }
      handleItemSelectionChange(updatedItems);
    }

    setFocusItem(selectedItems.length === 1 ? selectedItems[0] : {});
  }

  function handleAddItem() {
    navigate({
      pathname: basePath + '/add'
    })
    setAction('Add')
    setFocusItem({});
    setEditingItem(true);

  }

  function handleUpdateItem() {
    navigate({
      pathname: basePath + '/add'
    })
    setAction('Update')
    setFocusItem(selectedItems.length === 1 ? selectedItems[0] : {});
    setEditingItem(true);

  }

  async function handleAction(e: ClickEvent) {
    e.preventDefault();

    let action = e.detail.id;

    if (action === 'new_version') {
      handleUpdateItem()
    } else if (action === 'change_default') {
      setAction('UpdateDefault');
      setFocusItem(selectedItems[0]);
      setNewDefaultVersion(selectedItems[0].default)
      setEditingItem(true);
    } else if (action === 'download_default_version') {
      setFocusItem(selectedItems[0]);
      await handleDownloadVersion()
    } else if (action === 'download_latest_version') {
      setFocusItem(selectedItems[0]);
      await downloadScriptVersion({'package_uuid': selectedItems[0].package_uuid, 'script_name': selectedItems[0].script_name, 'default': selectedItems[0].latest})
    }
  }

  async function handleUpload(selectedFile: { name: string; }, details: { script_name: any; package_uuid: any; __make_default: any; default: any; }) {

    const result = await toBase64(selectedFile).catch(e => Error(e));
    if (result instanceof Error) {
      console.log('Error: ', result.message);
      return;
    }

    let newItem: any = {
      "script_name": details.script_name,
      "script_file": result
    };
    let notificationId;

    try {
      notificationId = addNotification({
        type: 'success',
        loading: true,
        dismissible: false,
        header: "Uploading script",
        content: "Uploading script - " + selectedFile.name,
      });

      const apiTools = new ToolsAPI();
      if (action === 'Add') {
        await apiTools.postSSMScripts(newItem);
      } else if (action === 'Update') {
        newItem.action = 'update_package';
        newItem.package_uuid = details.package_uuid;
        newItem.__make_default = details.__make_default;
        const response = await apiTools.putSSMScripts(newItem);

        console.log(response)
      } else if (action === 'ChangeDefault') {
        if (details.__make_default) {
          newItem.action = 'update_default';
          delete newItem.script_file;
          newItem.default = details.default
          await apiTools.putSSMScripts(newItem);
        }
      } else {
        addNotification({
          id: notificationId,
          type: 'error',
          dismissible: true,
          header: "Uploading script",
          content: 'Invalid action supplied.'
        })
        return;
      }

      addNotification({
        id: notificationId,
        type: 'success',
        dismissible: true,
        header: "Uploading script",
        content: selectedFile.name + " script upload successfully.",
      })

      updateMain();
    } catch (e: any) {
      console.log(e);
      if ('response' in e) {
        if (e.response != null && typeof e.response === 'object') {
          if ('data' in e.response) {
            addNotification({
              id: notificationId,
              type: 'error',
              dismissible: true,
              header: "Uploading script",
              content: selectedFile.name + ' script upload failed: ' + JSON.stringify(e.response.data)
            })
          }
        } else {
          addNotification({
            id: notificationId,
            type: 'error',
            dismissible: true,
            header: "Uploading script",
            content: selectedFile.name + ' script upload failed: ' + e.message
          })
        }
      } else {
        addNotification({
          id: notificationId,
          type: 'error',
          dismissible: true,
          header: "Uploading script",
          content: selectedFile.name + ' script upload failed: Unknown error occurred',
        })
      }
    }
    //
    // setSelectedFile(e.target.files[0])

    //TODO Deal with file

    handleResetScreen();
  }


  async function handleChangeVersion() {

    let newItem: any = {
      "package_uuid": focusItem.package_uuid,
      "script_name": focusItem.script_name,
      "default": newDefaultVersion
    };
    let notificationId;

    try {
      notificationId = addNotification({
        type: 'success',
        loading: true,
        dismissible: false,
        header: "Change script default version",
        content: "Changing script default version - " + focusItem.script_name,
      });

      const apiTools = new ToolsAPI();
      newItem.action = 'update_default';
      await apiTools.putSSMScripts(newItem);

      addNotification({
        id: notificationId,
        type: 'success',
        dismissible: true,
        header: "Change script default version",
        content: focusItem.script_name + " script default version changed to use version " + newDefaultVersion + ".",
      })

      setSelectedItems([]);

      updateMain();
    } catch (e: any) {
      console.log(e);
      if ('response' in e) {
        if (e.response != null && typeof e.response === 'object') {
          if ('data' in e.response) {
            addNotification({
              id: notificationId,
              type: 'error',
              dismissible: true,
              header: "Change script default version",
              content: focusItem.script_name + ' script version change failed: ' + e.response.data
            })
          }
        } else {
          addNotification({
            id: notificationId,
            type: 'error',
            dismissible: true,
            header: "Change script default version",
            content: focusItem.script_name + ' script version change failed: ' + e.message
          })
        }
      } else {
        addNotification({
          id: notificationId,
          type: 'error',
          dismissible: true,
          header: "Uploading script",
          content: focusItem.script_name + ' script version change failed.',
        })
      }
    }
    //
    // setSelectedFile(e.target.files[0])

    //TODO Deal with file

    handleResetScreen();
  }

  function downloadZIP(script: { script_file: any; script_name: string; script_version: string; }) {
    const linkSource = `data:application/zip;base64,${script.script_file}`;
    const downloadLink = document.createElement("a");
    let fileName = script.script_name;
    if (fileName.endsWith('.zip')) {
      fileName = script.script_name.replace('.zip', '_v' + script.script_version + '.zip');
    } else {
      fileName = script.script_name + '_v' + script.script_version + '.zip';
    }

    downloadLink.href = linkSource;
    downloadLink.download = fileName;
    downloadLink.click();
  }

  async function handleDownloadVersion() {

    await downloadScriptVersion(selectedItems[0]);

  }

  async function downloadScriptVersion(script: { package_uuid: any; script_name: any; default: any; }) {

    let notificationId;

    try {
      notificationId = addNotification({
        type: 'success',
        loading: true,
        dismissible: false,
        header: "Download script",
        content: "Downloading script default version - " + script.script_name,
      });

      const apiTools = new ToolsAPI();
      const response = await apiTools.getSSMScript(script.package_uuid, script.default, true);

      downloadZIP(response)

      addNotification({
        id: notificationId,
        type: 'success',
        dismissible: true,
        header: "Download script",
        content: script.script_name + " script downloaded.",
      })

      setSelectedItems([]);

    } catch (e: any) {
      console.log(e);
      if ('response' in e) {
        if (e.response != null && typeof e.response === 'object') {
          if ('data' in e.response) {
            addNotification({
              id: notificationId,
              type: 'error',
              dismissible: true,
              header: "Download script",
              content: script.script_name + ' script download failed: ' + e.response.data
            })
          }
        } else {
          addNotification({
            id: notificationId,
            type: 'error',
            dismissible: true,
            header: "Download script",
            content: script.script_name + ' script download failed: ' + e.message
          })
        }
      } else {
        addNotification({
          id: notificationId,
          type: 'error',
          dismissible: true,
          header: "Download script",
          content: script.script_name + ' script download failed.',
        })
      }
    }

  }


  function handleEditItem(selection = null) {
    if (selectedItems.length === 1) {
      navigate({
        pathname: basePath + '/edit/' + selectedItems[0][itemIDKey]
      })
      setAction('Edit')
      setFocusItem(selectedItems[0]);
      setEditingItem(true);
    } else if (selection) {
      navigate({
        pathname: basePath + '/edit/' + selection[itemIDKey]
      })
      setAction('Edit');
      setFocusItem(selection);
      setEditingItem(true);
    }

  }


  function handleResetScreen() {
    navigate({
      pathname: basePath
    })
    setEditingItem(false);
  }

  function handleItemSelectionChange(selection: Array<any>) {

    setSelectedItems(selection);

    //Reset URL to base table path.
    navigate({
      pathname: basePath
    })

  }

  function displayScriptScreen() {
    if (editingItem) {
      return displayEditScreen(action)
    } else {
      return displayViewScreen()
    }
  }

  function displayViewScreen() {
    return <SpaceBetween direction="vertical" size="xs">
      <AutomationScriptsTable
        userAccess={props.userEntityAccess}
        schema={schemaSSMAttribs}
        schemaName={'script'}
        schemaKeyAttribute={itemIDKey}
        dataAll={dataAll}
        items={dataMain}
        selectedItems={selectedItems}
        handleSelectionChange={handleItemSelectionChange}
        isLoading={isLoadingMain}
        errorLoading={errorMain}
        handleRefreshClick={handleRefreshClick}
        handleAddItem={handleAddItem}
        handleActionSelection={handleAction}
        actionsButtonDisabled={isActionsDisabled()}
        actionItems={[{
          id: 'change_default',
          text: 'Change default version',
          description: 'Change default version used.',
          disabled: false
        },
          {
            id: 'new_version',
            text: 'Add new version',
            description: 'Add a new version of the script.',
            disabled: false
          },
          {
            id: 'download_default_version',
            text: 'Download default version',
            description: 'Download default version of the script.',
            disabled: false
          },
          {
            id: 'download_latest_version',
            text: 'Download latest version',
            description: 'Download latest version of the script.',
            disabled: false
          }]}
      />
      <ViewAutomationScript
        schema={schemaSSMAttribs}
        selectedItems={selectedItems}
        dataAll={dataAll}

      />
    </SpaceBetween>
  }

  function displayEditScreen(action: string) {
    switch (action) {
      case 'Add':
      case 'Update': {
        return <AutomationScriptImport
          action={action}
          schema={schemaSSMAttribs}
          item={focusItem}
          handleUpload={handleUpload}
          cancelClick={handleResetScreen}
        />
      }
      case 'UpdateDefault': {
        return displayUpdatedDefault();
      }
      default:
        return undefined;
    }
  }

  function isActionsDisabled() {
    if (props.userEntityAccess['script'] && props.userEntityAccess['script'].create && selectedItems.length === 1) {
      return false;
    }

    return true;
  }

  function displayUpdatedDefault() {
    return <SpaceBetween direction={'vertical'} size={'xxl'}>
      <Container
        className="custom-dashboard-container"
        header={
          <Header
            variant="h2"
          >
            Change default script version
          </Header>
        }
      >
        <SpaceBetween size={'xxl'} direction={'vertical'}>
          <FormField
            key={'script_name'}
            label={'Script Name'}
          >
            <Input
              onChange={undefined}
              value={focusItem.script_name}
              disabled={true}
            />
          </FormField>
          <FormField
            key={'script_desc'}
            label={'Script Description'}
          >
            <Input
              onChange={undefined}
              value={focusItem.script_description}
              disabled={true}
            />
          </FormField>
          <SpaceBetween size={'xs'} direction={'vertical'}>
            <FormField
              key={'script_version'}
              label={'Script Default Version'}
              description={'The default version will be used for all jobs initiated from the console.'}
            >
              <Select
                selectedOption={{
                  label: newDefaultVersion,
                  value: newDefaultVersion
                }}
                onChange={event => setNewDefaultVersion(event.detail.selectedOption.value)}
                loadingText={"Loading values..."}
                options={getVersions()}
                selectedAriaLabel={'Selected'}
                placeholder={"Select version"}
              />
            </FormField>
            <Button iconName={'download'}
                    onClick={e => downloadScriptVersion({'package_uuid': focusItem.package_uuid, 'script_name': focusItem.script_name, 'default': newDefaultVersion})}>Download
              selected version</Button>
          </SpaceBetween>
        </SpaceBetween>
      </Container>
      {newDefaultVersion !== focusItem.default ?
        <Alert
          dismissAriaLabel="Close alert"
          type="warning"
        >
          {newDefaultVersion !== focusItem.default ? 'Saving will change default script to use version ' + newDefaultVersion + ' instead of version ' + focusItem.default + ' for all automation future jobs.' : ''}
        </Alert>
        :
        undefined}
      <SpaceBetween direction={'horizontal'} size={'xxs'}>
        <Button variant={'primary'} onClick={handleResetScreen} disabled={false}>Cancel</Button>
        <Button onClick={handleChangeVersion}
                disabled={newDefaultVersion !== focusItem.default ? false : true}>Save</Button>

      </SpaceBetween>
    </SpaceBetween>
  }

  useEffect(() => {
    let selected = [];

    if (!isLoadingMain) {

      let item = dataMain.filter((entry: { [x: string]: string | undefined; }) => entry[itemIDKey] === params.id);

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
      refreshSelectedItems();
    }

  }, [dataMain]);

  const schemaSSMAttribs: EntitySchema = props.schemas['script'];

  const getVersions = (): OptionDefinition[] => {
    const versions: OptionDefinition[] = [];

    for (let versionNum = 1; versionNum <= focusItem.latest; versionNum++) {
      if (focusItem.default == versionNum) {
        versions.push({'label': `${versionNum} DEFAULT`, 'value': `${versionNum}`});
      } else {
        versions.push({'label': `${versionNum}`, 'value': `${versionNum}`});
      }

    }
    return versions;
  }

  return (
    <div>
      {props.schemaIsLoading ?
        <StatusIndicator type="loading">
          Loading schema...
        </StatusIndicator>
        :
        displayScriptScreen()
      }
    </div>
  );
};

export default AutomationScripts;
