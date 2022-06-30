import React, { useState } from 'react';
import Admin from "../actions/admin";

import { Auth } from "aws-amplify";
import {
  Tabs,
  SpaceBetween, StatusIndicator,
} from '@awsui/components-react';

import { useModal } from '../actions/Modal.js';
import {useAdminPermissions} from "../actions/AdminPermissionsHook.js";
import ItemTable from '../components/ItemTable.jsx';
import PermissionsView from "../components/PermissionsView";
import ItemAmend from "../components/ItemAmend";

const AdminPolicy = (props) => {

  const [{ isLoading: permissionsIsLoading, data: permissionsData, error: permissionsError}, { update: permissionsUpdate }] = useAdminPermissions();

  const allData = {policy: {data: permissionsData.policies, isLoading: permissionsIsLoading, error: permissionsError}, roles: {data: permissionsData.roles, isLoading: permissionsIsLoading, error: permissionsError}, groups: {data: permissionsData.groups, isLoading: permissionsIsLoading, error: permissionsError}}

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState([]);
  const [focusItem, setFocusItem] = useState([]);
  const [selectedTab, setSelectedTab] = useState('roles');
  const [action, setAction] = useState(['add']);

  //Viewer pane state management.
  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');

  //Modals
  const { show: showDeleteConfirmaton, hide: hideDeleteConfirmaton, RenderModal: DeleteModal } = useModal()

  function handleNotification(notification)
  {
    props.updateNotification('add', notification)
  }

  function handleAddItem()
  {
    setAction('add');
    setFocusItem({});
    setEditingItem(true);

  }

  function handleEditItem()
  {
    setAction('edit');
    setFocusItem(selectedItems[0]);
    setEditingItem(true);

  }

  function handleResetScreen()
  {
    setEditingItem(false);
  }

  function handleItemSelectionChange(selection) {

    setSelectedItems(selection);

    if (selectedItems.length !== 0)
    {
      setFocusItem(selectedItems[0]);
    } else {
      setFocusItem({});
    }

  }

  async function handleSave(editItem, action) {

    //const { history } = this.props;
    //if(history) history.goBack();

    let newItem = Object.assign({}, editItem);
    let notificationHeader = 'policy';

    try {
      if (action === 'edit' && selectedTab === 'policies') {
        const session = await Auth.currentSession();
        const apiAdmin = new Admin(session);

        await apiAdmin.putPolicy(newItem);

        handleNotification({
          type: 'success',
          dismissible: true,
          header: "Update " + notificationHeader,
          content: editItem.policy_name + " updated successfully.",
        });

        //Update permissions for user UI.
        await permissionsUpdate()

        setEditingItem(false);
        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});

        //Reload actual permissions for current user.
        await props.reloadPermissions();

      } else if (action === 'edit' && selectedTab === 'roles') {
        notificationHeader = 'role'
        const session = await Auth.currentSession();
        const apiAdmin = new Admin(session);

        await apiAdmin.putRole(newItem);

        handleNotification({
          type: 'success',
          dismissible: true,
          header: "Update " + notificationHeader,
          content: editItem.role_name + " updated successfully.",
        });

        //Update permissions for user UI.
        await permissionsUpdate()

        setEditingItem(false);
        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});

        //Reload actual permissions for current user.
        await props.reloadPermissions();
      } else if (action === 'add' && selectedTab === 'roles') {
        notificationHeader = 'role'
        const session = await Auth.currentSession();
        const apiAdmin = new Admin(session);

        await apiAdmin.postRole(newItem);

        handleNotification({
          type: 'success',
          dismissible: true,
          header: "Update " + notificationHeader,
          content: editItem.role_name + " updated successfully.",
        });

        //Update permissions for user UI.
        await permissionsUpdate()

        setEditingItem(false);
        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});

        //Reload actual permissions for current user.
        await props.reloadPermissions();
      } else if (action === 'add' && selectedTab === 'policies') {
        notificationHeader = 'policy'
        const session = await Auth.currentSession();
        const apiAdmin = new Admin(session);

        await apiAdmin.postPolicy(newItem);

        handleNotification({
          type: 'success',
          dismissible: true,
          header: "Update " + notificationHeader,
          content: editItem.policy_name + " updated successfully.",
        });

        //Update permissions for user UI.
        await permissionsUpdate()

        setEditingItem(false);
        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});

        //Reload actual permissions for current user.
        await props.reloadPermissions();
      } else {
        setEditingItem(false);
      }


    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        handleNotification({
          type: 'error',
          dismissible: true,
          header: "Save " + notificationHeader,
          content: e.response.data
        });
      } else{

        handleNotification({
          type: 'error',
          dismissible: true,
          header: "Save " + notificationHeader,
          content: 'Unknown error occurred',
        });
      }
    }

  }

  async function handleTabChange(tabselected)
  {
    setSelectedTab(tabselected);
    setSelectedItems([]);
  }

  async function handleViewerTabChange(tabselected)
  {
    setViewerCurrentTab(tabselected);
  }

  async function handleDeleteItemClick(e) {
    e.preventDefault();
    showDeleteConfirmaton();
  }

  async function handleRefreshClick(e) {

    await permissionsUpdate();

  }

  async function handleDeleteItem(e) {
    e.preventDefault();
    let currentItem = 0;
    let notifcationHeader = 'Role'

    await hideDeleteConfirmaton();

    try {
      const session = await Auth.currentSession();
      const apiAdmin = new Admin(session);
      //await apiUser.deleteApp(selectedItems[item].app_id);

      if (selectedTab === 'roles') {
        await apiAdmin.delRole(selectedItems[0].role_id);
        handleNotification({
          type: 'success',
          dismissible: true,
          header: notifcationHeader + ' deleted successfully',
          content: selectedItems[0].role_name + ' was deleted.'
        });
        }

      if (selectedTab === 'policies') {
        notifcationHeader = 'Policy'
      await apiAdmin.delPolicy(selectedItems[0].policy_id);
        handleNotification({
          type: 'success',
          dismissible: true,
          header: notifcationHeader + ' deleted successfully',
          content: selectedItems[0].policy_name + ' was deleted.'
        });
      }

      permissionsUpdate();
      setSelectedItems([]);

    } catch (e) {
      console.log(e);
        handleNotification({
            type: 'error',
            dismissible: true,
            header: notifcationHeader + ' deletion failed',
            content: selectedItems[currentItem].role_id ? selectedItems[currentItem].role_id : selectedItems[currentItem].policy_id + ' failed to delete.'
          });
    }
  }

  const ViewPermissions = (props) => {

    const [selectedItemsViewer, lsetSelectedItemsViewer] = useState([]);

    if (selectedItems.length === 1) {

      return (
        <PermissionsView {...props}
          item={selectedItems[0]}
          itemType={selectedTab}
          schema={selectedTab === 'roles' ? props.schema.role : props.schema.policy}
          schemas={props.schema}
          handleTabChange={handleViewerTabChange}
          selectedTab={viewerCurrentTab}/>
      );
    } else {
      return (null);
    }
  }

  return (
    <div>
      {props.schemaIsLoading ?
        <StatusIndicator type="loading">
          Loading schema...
        </StatusIndicator>
        :
          !editingItem
          ?
          <Tabs
            activeTabId={selectedTab}
            onChange={({detail}) => handleTabChange(detail.activeTabId)}
            tabs={[
              {
                label: "Roles",
                id: "roles",
                content:
                  <SpaceBetween direction="vertical" size="xs">
                    <ItemTable
                      schema={props.schema.role}
                      schemaKeyAttribute={'role_id'}
                      schemaName={'role'}
                      dataAll={allData}
                      items={permissionsIsLoading ? [] : permissionsData.roles}
                      selectedItems={selectedItems}
                      handleSelectionChange={handleItemSelectionChange}
                      isLoading={permissionsIsLoading}
                      errorLoading={permissionsError}
                      handleRefreshClick={handleRefreshClick}
                      handleAddItem={handleAddItem}
                      handleDeleteItem={handleDeleteItemClick}
                      handleEditItem={handleEditItem}
                      selectionType={'single'}
                    />
                    <ViewPermissions
                      schema={props.schema}
                    />
                  </SpaceBetween>
              },
              {
                label: "Policies",
                id: "policies",
                content:
                  <SpaceBetween direction="vertical" size="xs">
                    <ItemTable
                      schema={props.schema.policy}
                      schemaKeyAttribute={'policy_id'}
                      schemaName={'policie'}
                      dataAll={allData}
                      items={permissionsIsLoading ? [] : permissionsData.policies}
                      selectedItems={selectedItems}
                      handleSelectionChange={handleItemSelectionChange}
                      isLoading={permissionsIsLoading}
                      errorLoading={permissionsError}
                      handleRefreshClick={handleRefreshClick}
                      handleAddItem={handleAddItem}
                      handleDeleteItem={handleDeleteItemClick}
                      handleEditItem={handleEditItem}
                      selectionType={'single'}
                    />
                    <ViewPermissions
                      schema={props.schema}
                    />
                  </SpaceBetween>
              }
              ,
              {
                label: "Groups",
                id: "groups",
                content:
                  <SpaceBetween direction="vertical" size="xs">
                    <ItemTable
                      description={'User access groups must be managed through Amazon Cognito.'}
                      schema={props.schema.group}
                      schemaKeyAttribute={'group_name'}
                      schemaName={'group'}
                      dataAll={permissionsData.groups}
                      items={permissionsIsLoading ? [] : permissionsData.groups}
                      isLoading={permissionsIsLoading}
                      errorLoading={permissionsError}
                      handleRefreshClick={handleRefreshClick}
                    />
                    <ViewPermissions
                      schema={props.schema}
                    />
                  </SpaceBetween>
              }
              ,
              {
                label: "Users",
                id: "users",
                content:
                  <SpaceBetween direction="vertical" size="xs">
                    <ItemTable
                      description={'Users must be managed through Amazon Cognito.'}
                      schema={props.schema.user}
                      schemaKeyAttribute={'userRef'}
                      schemaName={'user'}
                      dataAll={permissionsData.users}
                      items={permissionsIsLoading ? [] : permissionsData.users}
                      isLoading={permissionsIsLoading}
                      errorLoading={permissionsError}
                      handleRefreshClick={handleRefreshClick}
                    />
                    <ViewPermissions
                      schema={props.schema}
                    />
                  </SpaceBetween>
              }
            ]}
          />
          :
          <ItemAmend action={action} schemaName={selectedTab === 'roles' ? 'role' : 'policy'}
                     schemas={props.schema} userAccess={props.userEntityAccess}  item={focusItem} handleSave={handleSave} handleCancel={handleResetScreen}
                     updateNotification={handleNotification}/>
        }
      <DeleteModal
        title={'Delete policy'}
        onConfirmation={handleDeleteItem}
        >
        {selectedItems.length === 1
          ?
          <SpaceBetween size="l">
            <p>Are you sure you wish to delete the selected policy?</p>
          </SpaceBetween>
          :
          <p>Are you sure you wish to delete the {selectedItems.length} selected policies?</p>
        }
      </DeleteModal>
    </div>
  );
};

export default AdminPolicy;
