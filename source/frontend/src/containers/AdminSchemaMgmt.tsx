/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useContext, useEffect, useState} from 'react';
import AdminApiClient from "../api_clients/adminApiClient";
import {
  Alert,
  Box,
  Button,
  ColumnLayout,
  Container,
  FormField,
  Header,
  Input,
  SpaceBetween,
  StatusIndicator,
  Tabs
} from '@awsui/components-react';

import SchemaAttributesTable from '../components/SchemaAttributesTable';
import {capitalize, getNestedValuePath} from "../resources/main";
import ToolHelp from "../components/ToolHelp";
import ToolHelpEdit from "../components/ToolHelpEdit";
import {HelpContent, Tag} from "../models/HelpContent";
import {NotificationContext} from "../contexts/NotificationContext";
import {EntitySchema, SchemaMetaData} from "../models/EntitySchema";
import {ToolsContext} from "../contexts/ToolsContext";
import SchemaAttributeAmendModal from "../components/SchemaAttributeAmendModal";
import {CMFModal} from "../components/Modal";

type AdminSchemaMgmtParams = {
  reloadSchema: () => any;
  schemas: Record<string, EntitySchema>;
  schemaMetadata: SchemaMetaData[];
};
const AdminSchemaMgmt = (props: AdminSchemaMgmtParams) => {
  const {addNotification} = useContext(NotificationContext);
  const {setHelpPanelContent} = useContext(ToolsContext);

  //Layout state management.
  const [editingSchemaInfoHelp, setEditingSchemaInfoHelp] = useState(false);
  const [editingSchemaInfoHelpTemp, setEditingSchemaInfoHelpTemp] = useState<HelpContent | undefined>(undefined);
  const [editingSchemaInfoHelpUpdate, setEditingSchemaInfoHelpUpdate] = useState(false);

  const [editingSchemaSettings, setEditingSchemaSettings] = useState(false);
  const [editingSchemaSettingsTemp, setEditingSchemaSettingsTemp] = useState<Record<string, any>>({});
  const [editingSchemaSettingsUpdate, setEditingSchemaSettingsUpdate] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [focusItem, setFocusItem] = useState<any>([]);
  const [selectedTab, setSelectedTab] = useState('wave');
  const [action, setAction] = useState<string>('add');
  const [schemaTabs, setSchemaTabs] = useState<any[]>([]);

  const [selectedSubTab, setSelectedSubTab] = useState('attributes');

  //Modals
  const [schemaModalVisible, setSchemaModalVisible] = useState(false);
  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);
  const [isCancelConfirmationModalVisible, setCancelConfirmationModalVisible] = useState(false);

  function handleAddItem() {
    setAction('add');
    setSchemaModalVisible(true);
    setFocusItem({});
  }

  function handleEditItem() {
    setAction('edit');
    setSchemaModalVisible(true);
    setFocusItem(selectedItems[0]);
  }

  function handleEditSchemaHelp(helpText?: HelpContent) {
    setEditingSchemaInfoHelp(true);
    setEditingSchemaInfoHelpTemp(helpText);
  }

  function handleUserInputEditSchemaHelp(key: 'header' | 'content' | 'content_links' | 'content_html', update: string | Tag[]) {
    let tempUpdate: HelpContent = Object.assign({}, editingSchemaInfoHelpTemp);
    // @ts-ignore
    tempUpdate[key] = update
    setEditingSchemaInfoHelpTemp(tempUpdate);
    setEditingSchemaInfoHelpUpdate(true);
  }

  function handleCancelEditSchemaHelp() {
    setEditingSchemaInfoHelp(false);
    setEditingSchemaInfoHelpUpdate(false);
    setEditingSchemaInfoHelpTemp(undefined);
    setCancelConfirmationModalVisible(false);
  }

  async function handleSaveSchemaHelp() {
    try {
      const apiAdmin = new AdminApiClient();
      await apiAdmin.putSchema(
        selectedTab,
        {schema_name: selectedTab, help_content: editingSchemaInfoHelpTemp}
      );

      addNotification({
        type: 'success',
        dismissible: true,
        header: "Update schema help",
        content: "Schema updated successfully.",
      })

      setEditingSchemaInfoHelp(false);
      setEditingSchemaInfoHelpUpdate(false);
      setEditingSchemaInfoHelpTemp(undefined);


      await props.reloadSchema();

    } catch (e: any) {
      console.log(e);
        addNotification({
          type: 'error',
          dismissible: true,
          header: "Save schema help",
          content: e.response?.data?.cause ?? 'Unknown error occurred',
        })
    }

  }

  function handleEditSchemaSettings(schema: object | undefined) {
    setEditingSchemaSettings(true);
    if (schema == undefined) {
      setEditingSchemaSettingsTemp({});
    } else {
      setEditingSchemaSettingsTemp(schema);
    }

  }

  function handleUserInputEditSchemaSettings(key: string, update: string) {
    let tempUpdate: Record<string, any> = Object.assign({}, setEditingSchemaSettingsTemp);
    tempUpdate[key] = update
    setEditingSchemaSettingsTemp(tempUpdate);
    setEditingSchemaSettingsUpdate(true);
  }

  function handleCancelEditSchemaSettings() {
    setEditingSchemaSettings(false);
    setEditingSchemaSettingsUpdate(false);
    setEditingSchemaSettingsTemp({});
    setCancelConfirmationModalVisible(false);
  }

  async function handleSaveSchemaSettings(e: {
    preventDefault: () => void;
  }) {
    e.preventDefault();
    try {
      const apiAdmin = new AdminApiClient();
      await apiAdmin.putSchema(selectedTab, {schema_name: selectedTab, friendly_name: editingSchemaSettingsTemp.friendly_name});

      addNotification({
        type: 'success',
        dismissible: true,
        header: "Update schema settings",
        content: "Schema updated successfully.",
      })

      setEditingSchemaSettings(false);
      setEditingSchemaSettingsUpdate(false);
      setEditingSchemaSettingsTemp({});

      await props.reloadSchema();


    } catch (e: any) {
      console.log(e);
      addNotification({
        type: 'error',
        dismissible: true,
        header: "Save schema help",
        content: e.response?.data?.cause || 'Unknown error occurred',
      });
    }
  }


  function handleItemSelectionChange(selection: Array<any>) {

    setSelectedItems(selection);

    if (selection.length !== 0) {
      setFocusItem(selection[0]);
    } else {
      setFocusItem({});
    }

  }

  const handleSave = async (editItem: {
    name: string;
  }, action: string) => {
    try {
      if (action === 'edit') {
        const apiAdmin = new AdminApiClient();

        await apiAdmin.putSchemaAttr(selectedTab, editItem, editItem.name)

        setSchemaModalVisible(false);
        addNotification({
          type: 'success',
          dismissible: true,
          header: "Update attribute",
          content: editItem.name + " updated successfully.",
        })

        await props.reloadSchema();

        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});
      } else {
        const apiAdmin = new AdminApiClient();

        await apiAdmin.postSchemaAttr(selectedTab, editItem)

        setSchemaModalVisible(false);
        addNotification({
          type: 'success',
          dismissible: true,
          header: "Add attribute",
          content: editItem.name + " added successfully.",
        })

        await props.reloadSchema();
      }


    } catch (e: any) {
      console.log(e);

      setSchemaModalVisible(false);
      addNotification({
        type: 'error',
        dismissible: true,
        header: "Save attribute",
        content: e.response.data?.message || 'Unknown error occurred',
      })
    }
  };

  async function handleDeleteItem() {
    let currentItem = 0;

    setDeleteConfirmationModalVisible(false);

    try {
      const apiAdmin = new AdminApiClient();

      await apiAdmin.delSchemaAttr(selectedTab, selectedItems[0].name);

      addNotification({
        type: 'success',
        dismissible: true,
        header: 'Attribute deleted successfully',
        content: selectedItems[0].name + ' was deleted.'
      })

      //Unselect applications marked for deletion to clear apps.

      await props.reloadSchema();

      setSelectedItems([]);

    } catch (e: any) {
      console.log(e);
      addNotification({
        type: 'error',
        dismissible: true,
        header: 'Attribute deletion failed',
        content: selectedItems[currentItem].name + ' failed to delete.'
      })
    }
  }

  function getDeleteHandler(selectedItems: any[]) {

    if (selectedItems.length !== 0) {
      if (!selectedItems[0].system) {
        return async function () {
          setDeleteConfirmationModalVisible(true);
        };
      } else {
        return undefined;
      }
    } else {
      return async function () {
        setDeleteConfirmationModalVisible(true);
      };
    }
  }

  //On schema metadata change reload tabs.
  useEffect(() => {
    let tabs = [];
    if (props.schemas) {
      //Load tabs from schema.
      for (const schema of props.schemaMetadata) {
        const schemaName = schema['schema_name'];
        if (schema['schema_type'] === 'user') {
          const currentSchema = props.schemas[schemaName];
          const currentHelpContent: HelpContent | undefined = getNestedValuePath(currentSchema, 'help_content');
          tabs.push(
            {
              label: capitalize(schemaName),
              id: schemaName,
              content: <Tabs
                activeTabId={selectedSubTab}
                onChange={({detail}) => setSelectedSubTab(detail.activeTabId)}
                tabs={[{
                  label: 'Attributes',
                  id: 'attributes',
                  content:
                    <SchemaAttributesTable
                      items={currentSchema.attributes}
                      isLoading={!props.schemas}
                      error={!props.schemas ? 'Error reading schema' : undefined}
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
                                <Button variant={editingSchemaInfoHelp ? "primary" : undefined}
                                        disabled={!editingSchemaInfoHelp}
                                        onClick={() => setCancelConfirmationModalVisible(true)}>
                                  Cancel
                                </Button>
                                <Button disabled={!editingSchemaInfoHelp} onClick={handleSaveSchemaHelp}>
                                  Save
                                </Button>
                                <Button variant="primary" disabled={editingSchemaInfoHelp}
                                        onClick={() => handleEditSchemaHelp(currentHelpContent ?? {})}>
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
                              <ToolHelp helpContent={editingSchemaInfoHelpTemp}/>
                            </Container>
                          </ColumnLayout>
                          :
                          <ToolHelp
                            helpContent={currentHelpContent}
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
                                <Button variant={editingSchemaSettings ? "primary" : undefined}
                                        disabled={!editingSchemaSettings}
                                        onClick={() => setCancelConfirmationModalVisible(true)}>
                                  Cancel
                                </Button>
                                <Button disabled={!editingSchemaSettings} onClick={handleSaveSchemaSettings}>
                                  Save
                                </Button>
                                <Button variant="primary" disabled={editingSchemaSettings}
                                        onClick={() => handleEditSchemaSettings(currentSchema)}>
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
                            <Box margin={{bottom: 'xxxs'}} color="text-label">
                              {'Schema friendly name'}
                            </Box>
                            {getNestedValuePath(currentSchema, 'friendly_name') ? getNestedValuePath(currentSchema, 'friendly_name') : '-'}
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
  }, [
    props.schemaMetadata, selectedItems, editingSchemaInfoHelp, editingSchemaInfoHelpTemp, selectedSubTab, editingSchemaSettings, editingSchemaSettingsTemp]);

  // Must be wrapped in useEffect, because React can't update a different component while this component is rendered.
  useEffect(() => {
    //Update help tools panel.
    setHelpPanelContent({
      header: 'Attributes',
      content_text: 'From this screen as administrator you can add, update and delete schema attributes.'
    });
  }, []);

  const alert = editingSchemaInfoHelpUpdate || editingSchemaSettingsUpdate ?
    <Alert type="warning"> There are unsaved updates that will be lost. </Alert>
    : <></>;

  return (
    <div>
      {
        !props.schemas ?
          <StatusIndicator type="loading">
            Loading schema...
          </StatusIndicator>
          :
          <Tabs
            activeTabId={selectedTab}
            onChange={({detail}) => setSelectedTab(detail.activeTabId)}
            tabs={schemaTabs}
          />
      }

      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={'Delete attribute'}
      >
        {selectedItems.length === 1
          ?
          <SpaceBetween size="l">
            <p>Are you sure you wish to delete the selected attribute?</p>
            <Alert
              type="warning"
            >
              No existing data stored in this attribute will be removed, it will just no longer be visible in the UI or
              avilable for new records.
            </Alert>
          </SpaceBetween>
          :
          <p>Are you sure you wish to delete the {selectedItems.length} selected atrributes? No existing data stored in
            this attribute will be removed, it will just no longer be visible in the UI or available for new
            records.</p>
        }
      </CMFModal>

      <CMFModal
        onDismiss={() => setCancelConfirmationModalVisible(false)}
        visible={isCancelConfirmationModalVisible}
        onConfirmation={editingSchemaInfoHelp ? handleCancelEditSchemaHelp : handleCancelEditSchemaSettings}
        header={'Cancel schema update'}
      >
        <p>Are you sure you wish to cancel the updates to the schema?</p>
        {alert}
      </CMFModal>

      {schemaModalVisible ? <SchemaAttributeAmendModal
        title={'Amend attribute'}
        onConfirmation={handleSave}
        closeModal={() => setSchemaModalVisible(false)}
        attribute={focusItem}
        action={action}
        schemas={props.schemas}
        activeSchemaName={selectedTab}/> : <></>
      }
    </div>
  );
};

export default AdminSchemaMgmt;
