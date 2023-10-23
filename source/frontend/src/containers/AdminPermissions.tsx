// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import Admin from "../actions/admin";

import { Auth } from "@aws-amplify/auth";
import {
  Tabs,
  SpaceBetween, StatusIndicator,
} from '@awsui/components-react';

import { useModal } from '../actions/Modal';
import {useAdminPermissions} from "../actions/AdminPermissionsHook";
import ItemTable from '../components/ItemTable';
import PermissionsView from "../components/PermissionsView";
import ItemAmend from "../components/ItemAmend";
import {useUserGroupsModal} from "../actions/UserGroupsModalHook";
import {useAmendItemModal} from "../actions/AmendItemModalHook";


const ViewPermissions = (props) => {
  //Viewer pane state management.
  const [viewerCurrentTab, setViewerCurrentTab] = useState('details');

  async function handleViewerTabChange(tabselected)
  {
    setViewerCurrentTab(tabselected);
  }

  if (props.selectedItems.length === 1 && (props.selectedTab === 'roles' || props.selectedTab === 'policies')) {

    return (
      <PermissionsView {...props}
                       item={props.selectedItems[0]}
                       itemType={props.selectedTab}
                       schema={props.selectedTab === 'roles' ? props.schema.role : props.schema.policy}
                       schemas={props.schema}
                       handleTabChange={handleViewerTabChange}
                       selectedTab={viewerCurrentTab}/>
    );
  } else {
    return null;
  }
}

const AdminPermissions = (props) => {

  const [{ isLoading: permissionsIsLoading, data: permissionsData, error: permissionsError}, { update: permissionsUpdate }] = useAdminPermissions();

  const allData = {policy: {data: permissionsData.policies, isLoading: permissionsIsLoading, error: permissionsError}, roles: {data: permissionsData.roles, isLoading: permissionsIsLoading, error: permissionsError}, groups: {data: permissionsData.groups, isLoading: permissionsIsLoading, error: permissionsError}}

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState([]);
  const [focusItem, setFocusItem] = useState([]);
  const [selectedTab, setSelectedTab] = useState('roles');
  const [action, setAction] = useState(['add']);



  //Modals
  const { show: showDeleteConfirmation, hide: hideDeleteConfirmation, RenderModal: DeleteModal } = useModal()
  const { show: showGroupDeleteConfirmation, hide: hideGroupDeleteConfirmation, RenderModal: GroupDeleteModal } = useModal()
  const { show: showAddGroups,  RenderModal: AddGroupsModal } = useUserGroupsModal()
  const { show: showRemoveGroups, RenderModal: RemoveGroupsModal } = useUserGroupsModal()
  const { show: showAddGroup, RenderModal: AddGroupModal } = useAmendItemModal()

  function getPermissions(isLoading, permissionsData, key){
    if (isLoading){
      return []
    } else {
      return permissionsData[key]
    }
  }

  function displayAdminPolicy(editingItem){
    if (!editingItem) {
      return <Tabs
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
                  items={getPermissions(permissionsIsLoading, permissionsData, 'roles')}
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
                  selectedItems={selectedItems}
                  selectedTab={selectedTab}
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
                  items={getPermissions(permissionsIsLoading, permissionsData, 'policies')}
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
                  selectedItems={selectedItems}
                  selectedTab={selectedTab}
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
                  schema={props.schema.group}
                  schemaKeyAttribute={'group_name'}
                  schemaName={'group'}
                  dataAll={permissionsData.groups}
                  items={getPermissions(permissionsIsLoading, permissionsData, 'groups')}
                  isLoading={permissionsIsLoading}
                  errorLoading={permissionsError}
                  handleRefreshClick={handleRefreshClick}
                  handleAddItem={handleAddGroupClick}
                  handleDeleteItem={handleDeleteGroupClick}
                  handleSelectionChange={handleItemSelectionChange}
                  selectionType={'single'}
                  selectedItems={selectedItems}
                />
                <ViewPermissions
                  schema={props.schema}
                  selectedItems={selectedItems}
                  selectedTab={selectedTab}
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
                  description={'Users must be created through Amazon Cognito or a federated IDP.'}
                  schema={props.schema.user}
                  schemaKeyAttribute={'userRef'}
                  schemaName={'user'}
                  dataAll={permissionsData.users}
                  items={permissionsIsLoading ? [] : permissionsData.users}
                  isLoading={permissionsIsLoading}
                  errorLoading={permissionsError}
                  handleRefreshClick={handleRefreshClick}
                  actionsButtonDisabled={false}
                  handleAction={handleActionClick}
                  actionItems={[{
                    id: 'add_group',
                    text: 'Add users to group',
                    description: 'Add users to group.',
                    disabled: selectedItems.length === 0 ? true : false
                  },
                    {
                      id: 'remove_group',
                      text: 'Remove users to group',
                      description: 'Remove users to group.',
                      disabled: selectedItems.length === 0 ? true : false
                    }]}
                  handleSelectionChange={handleItemSelectionChange}
                  selectionType={'multi'}
                  selectedItems={selectedItems}
                />
                <ViewPermissions
                  schema={props.schema}
                  selectedItems={selectedItems}
                  selectedTab={selectedTab}
                />
              </SpaceBetween>
          }
        ]}
      />
    }else {
      return <ItemAmend action={action} schemaName={selectedTab === 'roles' ? 'role' : 'policy'}
                        schemas={props.schema} userAccess={props.userEntityAccess} item={focusItem}
                        handleSave={handleSave} handleCancel={handleResetScreen}
                        updateNotification={handleNotification}/>

    }
  }

  function handleNotification(notification)
  {
    return props.updateNotification('add', notification)
  }

  function handleAddItem()
  {
    setAction('add');
    setFocusItem({});
    setEditingItem(true);

  }

  async function handleAddGroupClick(e) {
    e.preventDefault();
    showAddGroup();
  }

  async function handleDeleteGroupClick(e) {
    e.preventDefault();
    showGroupDeleteConfirmation();
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

  async function handleDeleteItemClick(e) {
    e.preventDefault();
    showDeleteConfirmation();
  }

  async function handleRefreshClick(e) {

    await permissionsUpdate();

  }

  async function handleActionClick(e) {
    e.preventDefault();

    let action = e.detail.id;

    if(action === 'add_group'){
      await addUsersToGroupsClick()
    } else if (action === 'remove_group'){
      await removeUsersFromGroupsClick()
    }
  }

  async function addUsersToGroups(groups) {

    if (!groups.selectedGroups){
      return;
    }
    let notificationId = null;

    try {
      notificationId = handleNotification({
        type: 'success',
        loading: true,
        dismissible: false,
        header: "Update users",
        content: "Adding selected users to groups: " + groups.selectedGroups.map(group => group.value),
      });

      let users = [];
      for (const user of selectedItems) {
        users.push({'username': user['userRef'], 'addGroups': groups.selectedGroups.map(group => group.value)})
      }

      const session = await Auth.currentSession();
      const apiAdmin = await new Admin(session);
      await apiAdmin.putUsers(users);

      permissionsUpdate();

      handleNotification({
        id: notificationId,
        type: 'success',
        dismissible: true,
        header: "Update users",
        content: "Users added to groups: " + groups.selectedGroups.map(group => group.value),
      });

      setSelectedItems([]);

    } catch (e) {
      console.log(e);
      if ('response' in e) {
        if(e.response != null && typeof e.response === 'object') {
          if ('data' in e.response) {
            handleNotification({
              id: notificationId,
              type: 'error',
              dismissible: true,
              header: "Update users",
              content: 'Add to group failed: ' + e.response.data
            });
          }
        } else {
          handleNotification({
            id: notificationId,
            type: 'error',
            dismissible: true,
            header: "Update users",
            content: 'Add to group failed: ' + e.message
          });
        }
      } else {
        handleNotification({
          id: notificationId,
          type: 'error',
          dismissible: true,
          header: "Update users",
          content: 'Add to group failed.',
        });
      }
    }

  }

  async function addUsersToGroupsClick() {
    await showAddGroups();
  }

  async function removeUsersFromGroups(groups) {

    if (!groups.selectedGroups){
      return;
    }
    let notificationId = null;

    try {
      notificationId = handleNotification({
        type: 'success',
        loading: true,
        dismissible: false,
        header: "Update users",
        content: "Removing selected users from groups: " + groups.selectedGroups.map(group => group.value),
      });

      let users = [];
      for (const user of selectedItems) {
        users.push({'username': user['userRef'], 'removeGroups': groups.selectedGroups.map(group => group.value)})
      }

      const session = await Auth.currentSession();
      const apiAdmin = await new Admin(session);
      await apiAdmin.putUsers(users);

      permissionsUpdate();

      handleNotification({
        id: notificationId,
        type: 'success',
        dismissible: true,
        header: "Update users",
        content: "Users removed from groups: " + groups.selectedGroups.map(group => group.value),
      });

      setSelectedItems([]);

    } catch (e) {
      console.log(e);
      if ('response' in e) {
        if(e.response != null && typeof e.response === 'object') {
          if ('data' in e.response) {
            handleNotification({
              id: notificationId,
              type: 'error',
              dismissible: true,
              header: "Update users",
              content: 'Remove from group failed: ' + e.response.data
            });
          }
        } else {
          handleNotification({
            id: notificationId,
            type: 'error',
            dismissible: true,
            header: "Update users",
            content: 'Remove from group failed: ' + e.message
          });
        }
      } else {
        handleNotification({
          id: notificationId,
          type: 'error',
          dismissible: true,
          header: "Update users",
          content: 'Remove from group failed.',
        });
      }
    }

  }

  async function createGroup(group) {

    if (!group.group_name){
      return;
    }
    let notificationId = null;

    try {
      notificationId = handleNotification({
        type: 'success',
        loading: true,
        dismissible: false,
        header: "Add group",
        content: "Adding new group: " + group.group_name,
      });

      const session = await Auth.currentSession();
      const apiAdmin = await new Admin(session);
      await apiAdmin.postGroups([group]);

      permissionsUpdate();

      handleNotification({
        id: notificationId,
        type: 'success',
        dismissible: true,
        header: "Add group",
        content: "New group added: " + group.group_name,
      });

      setSelectedItems([]);

    } catch (e) {
      console.log(e);
      if ('response' in e) {
        if(e.response != null && typeof e.response === 'object') {
          if ('data' in e.response) {
            handleNotification({
              id: notificationId,
              type: 'error',
              dismissible: true,
              header: "Add group",
              content: 'Add group failed: ' + e.response.data
            });
          }
        } else {
          handleNotification({
            id: notificationId,
            type: 'error',
            dismissible: true,
            header: "Add group",
            content: 'Add group failed: ' + e.message
          });
        }
      } else {
        handleNotification({
          id: notificationId,
          type: 'error',
          dismissible: true,
          header: "Add group",
          content: 'Add group failed.',
        });
      }
    }

  }

  async function removeUsersFromGroupsClick() {
    await showRemoveGroups();
  }

  async function handleDeleteItem(e) {
    e.preventDefault();
    let currentItem = 0;
    let notifcationHeader = 'Group'

    await hideDeleteConfirmation();
    await hideGroupDeleteConfirmation();

    try {
      const session = await Auth.currentSession();
      const apiAdmin = new Admin(session);

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

      if (selectedTab === 'groups') {
        notifcationHeader = 'Group'
        await apiAdmin.delGroup(selectedItems[0].group_name);
        handleNotification({
          type: 'success',
          dismissible: true,
          header: notifcationHeader + ' deleted successfully',
          content: selectedItems[0].group_name + ' was deleted.'
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

  return (
    <div>
      {props.schemaIsLoading ?
        <StatusIndicator type="loading">
          Loading schema...
        </StatusIndicator>
        :
          displayAdminPolicy(editingItem)
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
      <GroupDeleteModal
        title={'Delete group'}
        onConfirmation={handleDeleteItem}
      >
        {selectedItems.length === 1
          ?
          <SpaceBetween size="l">
            <p>Are you sure you wish to delete the selected group?</p>
          </SpaceBetween>
          :
          <p>Are you sure you wish to delete the {selectedItems.length} selected groups?</p>
        }
      </GroupDeleteModal>
      <AddGroupsModal
        title={'Select groups to add'}
        onConfirmation={addUsersToGroups}
        groups={permissionsData.groups.map(group => group.group_name)}
      >
      </AddGroupsModal>
      <RemoveGroupsModal
        title={'Select groups to remove'}
        onConfirmation={removeUsersFromGroups}
        groups={permissionsData.groups.map(group => group.group_name)}
      >
      </RemoveGroupsModal>
      <AddGroupModal
        title={'New group'}
        schemas={props.schema}
        schemaName={'group'}
        userAccess={props.userEntityAccess}
        onConfirmation={createGroup}
      />
    </div>
  );
};

export default AdminPermissions;
