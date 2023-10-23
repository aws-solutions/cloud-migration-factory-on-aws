// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import Admin from "../actions/admin";

import { Auth } from "@aws-amplify/auth";
import {
  FormField,
  ColumnLayout,
  Button,
  Container,
  Header,
  Alert,
  Tabs,
  SpaceBetween,
  StatusIndicator,
  Input,
  Box
} from '@awsui/components-react';

import SchemaAttributesTable from '../components/SchemaAttributesTable';
import { useModal } from '../actions/Modal';
import { useSchemaModal } from '../actions/SchemaAttributeModalHook';
import {capitalize, getNestedValuePath} from "../resources/main";
import ToolHelp from "../components/ToolHelp";
import ToolHelpEdit from "../components/ToolHelpEdit";

const AdminSchemaMgmt = (props) => {
  //Layout state management.
  const [editingSchemaInfoHelp, setEditingSchemaInfoHelp] = useState(false);
  const [editingSchemaInfoHelpTemp, setEditingSchemaInfoHelpTemp] = useState('');
  const [editingSchemaInfoHelpUpdate, setEditingSchemaInfoHelpUpdate] = useState(false);

  const [editingSchemaSettings, setEditingSchemaSettings] = useState(false);
  const [editingSchemaSettingsTemp, setEditingSchemaSettingsTemp] = useState('');
  const [editingSchemaSettingsUpdate, setEditingSchemaSettingsUpdate] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState([]);
  const [focusItem, setFocusItem] = useState([]);
  const [selectedTab, setSelectedTab] = useState('wave');
  const [action, setAction] = useState(['add']);
  const [schemaTabs, setSchemaTabs] = useState([]);

  const [selectedSubTab, setSelectedSubTab] = useState('attributes');

  //Modals
  const { show: showAmend, hide: hideAmend, RenderModal: AmendModal } = useSchemaModal()
  const { show: showDeleteConfirmaton, hide: hideDeleteConfirmaton, RenderModal: DeleteModal } = useModal()

  //Modals
  const { show: showCancelConfirmation, hide: hideCancelConfirmation, RenderModal: CancelEditModal } = useModal();


  function handleNotification(notification)
  {
    props.updateNotification('add', notification)
  }

  function handleAddItem()
  {
    setAction('add');
    showAmend();
    setFocusItem({});

  }

  function handleEditItem()
  {
    setAction('edit');
    showAmend();
    setFocusItem(selectedItems[0]);

  }

  function handleEditSchemaHelp(helpText)
  {
    setEditingSchemaInfoHelp(true);
    if (helpText == undefined){
      setEditingSchemaInfoHelpTemp({});
    } else {
      setEditingSchemaInfoHelpTemp(helpText);
    }

  }

  function handleUserInputEditSchemaHelp(key, update)
  {
    let tempUpdate = Object.assign({}, editingSchemaInfoHelpTemp);
    tempUpdate[key] = update
    setEditingSchemaInfoHelpTemp(tempUpdate);
    setEditingSchemaInfoHelpUpdate(true);
  }

  function handleCancelEditSchemaHelp(e)
  {
    e.preventDefault();
    setEditingSchemaInfoHelp(false);
    setEditingSchemaInfoHelpUpdate(false);
    setEditingSchemaInfoHelpTemp('');
    hideCancelConfirmation();
  }

  async function handleSaveSchemaHelp(e) {
    e.preventDefault();
    try {
      const session = await Auth.currentSession();
      const apiAdmin = new Admin(session);
      await apiAdmin.putSchema(selectedTab, {schema_name: selectedTab, help_content: editingSchemaInfoHelpTemp});

      handleNotification({
        type: 'success',
        dismissible: true,
        header: "Update schema help",
        content: "Schema updated successfully.",
      });

      setEditingSchemaInfoHelp(false);
      setEditingSchemaInfoHelpUpdate(false);
      setEditingSchemaInfoHelpTemp('');


      await props.reloadSchema();

    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        handleNotification({
          type: 'error',
          dismissible: true,
          header: "Save schema help.",
          content: e.response.data.cause
        });
      } else{

        handleNotification({
          type: 'error',
          dismissible: true,
          header: "Save schema help",
          content: 'Unknown error occurred',
        });
      }
    }

  }

  function handleEditSchemaSettings(schema)
  {
    setEditingSchemaSettings(true);
    if (schema == undefined){
      setEditingSchemaSettingsTemp({});
    } else {
      setEditingSchemaSettingsTemp(schema);
    }

  }

  function handleUserInputEditSchemaSettings(key, update)
  {
    let tempUpdate = Object.assign({}, setEditingSchemaSettingsTemp);
    tempUpdate[key] = update
    setEditingSchemaSettingsTemp(tempUpdate);
    setEditingSchemaSettingsUpdate(true);
  }

  function handleCancelEditSchemaSettings(e)
  {
    e.preventDefault();
    setEditingSchemaSettings(false);
    setEditingSchemaSettingsUpdate(false);
    setEditingSchemaSettingsTemp('');
    hideCancelConfirmation();
  }

  async function handleSaveSchemaSettings(e) {
    e.preventDefault();
    try {
      const session = await Auth.currentSession();
      const apiAdmin = new Admin(session);
      await apiAdmin.putSchema(selectedTab, {schema_name: selectedTab, friendly_name: editingSchemaSettingsTemp.friendly_name});

      handleNotification({
        type: 'success',
        dismissible: true,
        header: "Update schema settings",
        content: "Schema updated successfully.",
      });

      setEditingSchemaSettings(false);
      setEditingSchemaSettingsUpdate(false);
      setEditingSchemaSettingsTemp({});


      await props.reloadSchema();


    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        handleNotification({
          type: 'error',
          dismissible: true,
          header: "Save schema help.",
          content: e.response.data.cause
        });
      } else{

        handleNotification({
          type: 'error',
          dismissible: true,
          header: "Save schema help",
          content: 'Unknown error occurred',
        });
      }
    }

  }


  function handleItemSelectionChange(selection) {

    setSelectedItems(selection);

    if (selection.length !== 0)
    {
      setFocusItem(selection[0]);
    } else {
      setFocusItem({});
    }

  }

  async function handleSave(editItem, action) {
    try {
      if (action === 'edit') {
        const session = await Auth.currentSession();
        const apiAdmin = new Admin(session);

        await apiAdmin.putSchemaAttr(selectedTab, editItem, editItem.name)

        hideAmend();
        handleNotification({
          type: 'success',
          dismissible: true,
          header: "Update attribute",
          content: editItem.name + " updated successfully.",
        });

        await props.reloadSchema();

        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});
      }
      else {

        const session = await Auth.currentSession();
        const apiAdmin = new Admin(session);

        await apiAdmin.postSchemaAttr(selectedTab, editItem)

        hideAmend();
        handleNotification({
          type: 'success',
          dismissible: true,
          header: "Add attribute",
          content: editItem.name + " added successfully.",
        });

        await props.reloadSchema();
      }


    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response && 'message' in e.response.data) {
        hideAmend();
        handleNotification({
          type: 'error',
          dismissible: true,
          header: "Save attribute",
          content: e.response.data.message
        });

      } else{
        hideAmend();
        handleNotification({
          type: 'error',
          dismissible: true,
          header: "Save attribute",
          content: 'Unknown error occurred',
        });
      }

    }

  }

  async function handleDeleteItemClick(e) {
    e.preventDefault();
    showDeleteConfirmaton();
  }

  async function handleDeleteItem(e) {
    e.preventDefault();
    let currentItem = 0;

    await hideDeleteConfirmaton();

    try {
      const session = await Auth.currentSession();
      const apiAdmin = new Admin(session);

      await apiAdmin.delSchemaAttr(selectedTab,selectedItems[0].name);

      handleNotification({
            type: 'success',
            dismissible: true,
            header: 'Attribute deleted successfully',
            content: selectedItems[0].name + ' was deleted.'
          });

      //Unselect applications marked for deletion to clear apps.

      await props.reloadSchema();

      setSelectedItems([]);

    } catch (e) {
      console.log(e);
        handleNotification({
            type: 'error',
            dismissible: true,
            header: 'Attribute deletion failed',
            content: selectedItems[currentItem].name + ' failed to delete.'
          });
    }
  }

  function getDeleteHandler(selectedItems){

    if (selectedItems.length !== 0)
    {
      if (!selectedItems[0].system){
        return handleDeleteItemClick;
      } else {
        return undefined;
      }
    } else {
      return handleDeleteItemClick;
    }
  }

  //On schema metadata change reload tabs.
  useEffect( () => {
    let tabs = [];
    if(props.schema){
        //Load tabs from schema.
        for (const schema of props.schemaMetadata) {
          if (schema['schema_type'] === 'user') {
            tabs.push(
              {
                label: capitalize(schema['schema_name']),
                id: schema['schema_name'],
                content: <Tabs
                  activeTabId={selectedSubTab}
                  onChange={({ detail }) => setSelectedSubTab(detail.activeTabId)}
                  tabs={[{
                  label: 'Attributes',
                  id: 'attributes',
                  content:
                      <SchemaAttributesTable
                        items={props.schema[schema['schema_name']].attributes}
                        isLoading={!props.schema}
                        errorLoading={!props.schema ? 'Error reading schema' : undefined}
                        sendNotification={handleNotification}
                        selectedItems={selectedItems}
                        handleSelectionChange={handleItemSelectionChange}
                        handleAddItem={handleAddItem}
                        handleDeleteItem={getDeleteHandler(selectedItems)}
                        handleEditItem={handleEditItem}
                      />
                },
                {
                  label: 'Info Panel',
                  id: 'infopanel',
                  content:
                    <Container
                      className="custom-dashboard-container"
                      header={
                        <Header
                          variant="h2"
                          description="Define the content that will be provided to the user if they click the Info link next this table."
                          actions={
                            <SpaceBetween direction="horizontal" size="xs">
                              <Button variant={editingSchemaInfoHelp ? "primary" : undefined} disabled={!editingSchemaInfoHelp} onClick={showCancelConfirmation}>
                                Cancel
                              </Button>
                              <Button disabled={!editingSchemaInfoHelp} onClick={handleSaveSchemaHelp}>
                                Save
                              </Button>
                              <Button variant="primary" disabled={editingSchemaInfoHelp} onClick={event => handleEditSchemaHelp(getNestedValuePath(props.schema[schema['schema_name']], 'help_content'))}>
                                Edit
                              </Button>
                            </SpaceBetween>
                          }
                        >
                          Info panel guidance
                        </Header>
                      }
                    >
                      {editingSchemaInfoHelp
                        ?
                        <ColumnLayout columns={2}>
                          <ToolHelpEdit
                            editingSchemaInfoHelpTemp={editingSchemaInfoHelpTemp}
                            handleUserInputEditSchemaHelp={handleUserInputEditSchemaHelp}
                            />
                          <Container
                            key={'help_preview'}
                            header={
                              <Header
                                variant="h2"
                              >
                                Preview
                              </Header>
                            }
                          >
                            <ToolHelp
                              helpContent={editingSchemaInfoHelpTemp}
                            />
                          </Container>
                        </ColumnLayout>
                        :
                        <ToolHelp
                          helpContent={getNestedValuePath(props.schema[schema['schema_name']], 'help_content')}
                        />
                      }
                    </Container>
                  },
                    {
                      label: 'Schema Settings',
                      id: 'schema_settings',
                      content:
                        <Container
                          className="custom-dashboard-container"
                          header={
                            <Header
                              variant="h2"
                              actions={
                                <SpaceBetween direction="horizontal" size="xs">
                                  <Button variant={editingSchemaSettings ? "primary" : undefined} disabled={!editingSchemaSettings} onClick={showCancelConfirmation}>
                                    Cancel
                                  </Button>
                                  <Button disabled={!editingSchemaSettings} onClick={handleSaveSchemaSettings}>
                                    Save
                                  </Button>
                                  <Button variant="primary" disabled={editingSchemaSettings} onClick={event => handleEditSchemaSettings(props.schema[schema['schema_name']])}>
                                    Edit
                                  </Button>
                                </SpaceBetween>
                              }
                            >
                              General Schema Settings
                            </Header>
                          }
                        >
                          {editingSchemaSettings
                            ?
                            <>
                            <FormField
                              key={'schema_friendly_name'}
                              label={'Schema friendly name'}
                              description={'Schema name shown on the user interface.'}
                            >
                              <Input
                                onChange={event => handleUserInputEditSchemaSettings('friendly_name', event.detail.value)}
                                value={editingSchemaSettingsTemp.friendly_name ? editingSchemaSettingsTemp.friendly_name : ''}
                              />
                            </FormField>
                            </>
                            :
                            <SpaceBetween size={'xxxs'}>
                              <Box margin={{ bottom: 'xxxs' }} color="text-label">
                                {'Schema friendly name'}
                              </Box>
                              {getNestedValuePath(props.schema[schema['schema_name']], 'friendly_name') ? getNestedValuePath(props.schema[schema['schema_name']], 'friendly_name') : '-'}
                            </SpaceBetween>
                          }
                        </Container>
                    }]}
                />
              }
            )
          }
        }
        setSchemaTabs(tabs);
      }
  },[props.schemaMetadata, selectedItems, editingSchemaInfoHelp, editingSchemaInfoHelpTemp,selectedSubTab, editingSchemaSettings, editingSchemaSettingsTemp]);

  //Update help tools panel.
  useEffect(() => {
      props.setHelpPanelContent({
        header: 'Attributes',
        content_text: 'From this screen as administrator you can add, update and delete schema attributes.'
      })
  },[]);

  return (
    <div>
     {
          !props.schema ?
            <StatusIndicator type="loading">
              Loading schema...
            </StatusIndicator>
            :
            <Tabs
              activeTabId={selectedTab}
              onChange={({ detail }) => setSelectedTab(detail.activeTabId)}
              tabs={schemaTabs}
              // variant="container"
            />
        }
      <DeleteModal
        title={'Delete attribute'}
        onConfirmation={handleDeleteItem}
        >
        {selectedItems.length === 1
          ?
          <SpaceBetween size="l">
            <p>Are you sure you wish to delete the selected attribute?</p>
            <Alert
                type="warning"
              >
                No existing data stored in this attribute will be removed, it will just no longer be visible in the UI or avilable for new records.
              </Alert>
          </SpaceBetween>
          :
          <p>Are you sure you wish to delete the {selectedItems.length} selected atrributes? No existing data stored in this attribute will be removed, it will just no longer be visible in the UI or available for new records.</p>
        }
      </DeleteModal>
      <CancelEditModal
        title={'Cancel schema update'}
        onConfirmation={editingSchemaInfoHelp ? handleCancelEditSchemaHelp : handleCancelEditSchemaSettings}
      >
          <p>Are you sure you wish to cancel the updates to the schema?</p>
          {
            editingSchemaInfoHelpUpdate || editingSchemaSettingsUpdate ?
            <Alert
              type="warning"
            >
              There are unsaved updates that will be lost.
            </Alert>
            :
            undefined
          }
      </CancelEditModal>
      <AmendModal
        title={'Amend attribute'}
        onConfirmation={handleSave}
        attribute={focusItem}
        action={action}
        schema={props.schema}
        activeSchema={selectedTab}
      >
      </AmendModal>
    </div>
  );
};

export default AdminSchemaMgmt;
