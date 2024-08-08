/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useContext, useState } from "react";
import AdminApiClient from "../api_clients/adminApiClient";
import { SpaceBetween, StatusIndicator, Tabs } from "@awsui/components-react";

import { useAdminPermissions } from "../actions/AdminPermissionsHook";
import ItemTable from "../components/ItemTable";
import PermissionsView from "../components/PermissionsView";
import ItemAmend from "../components/ItemAmend";
import { ClickEvent } from "../models/Events";
import { NotificationContext } from "../contexts/NotificationContext";
import { EntitySchema } from "../models/EntitySchema";
import AmendItemModal from "../components/AmendItemModal";
import { CMFModal } from "../components/Modal";
import { UserGroupsModal } from "../components/UserGroupsModal";

type DetailsViewParams = {
  selectedItems: any[];
  selectedTab: string;
  schemas: Record<string, EntitySchema>;
};
const DetailsView = (props: DetailsViewParams) => {
  //Viewer pane state management.
  const [viewerCurrentTab, setViewerCurrentTab] = useState("details");

  if (props.selectedItems.length === 1 && (props.selectedTab === "roles" || props.selectedTab === "policies")) {
    return (
      <PermissionsView
        item={props.selectedItems[0]}
        itemType={props.selectedTab}
        schema={props.selectedTab === "roles" ? props.schemas.role : props.schemas.policy}
        schemas={props.schemas}
        handleTabChange={setViewerCurrentTab}
        selectedTab={viewerCurrentTab}
      />
    );
  } else {
    return null;
  }
};

type AdminPermissionsParams = {
  schemas: Record<string, EntitySchema>;
  userEntityAccess: any;
  reloadPermissions: () => any;
  schemaIsLoading?: boolean;
};
type PermissionsData = {
  [x: string]: any;
  roles?: any[];
  policies?: any[];
  groups?: any[];
  users?: any[];
};
const AdminPermissions = (props: AdminPermissionsParams) => {
  const { addNotification } = useContext(NotificationContext);

  const [
    { isLoading: permissionsIsLoading, data: permissionsData, error: permissionsError },
    { update: permissionsUpdate },
  ] = useAdminPermissions();

  const allData = {
    policy: { data: permissionsData.policies, isLoading: permissionsIsLoading, error: permissionsError },
    roles: { data: permissionsData.roles, isLoading: permissionsIsLoading, error: permissionsError },
    groups: { data: permissionsData.groups, isLoading: permissionsIsLoading, error: permissionsError },
  };

  //Layout state management.
  const [editingItem, setEditingItem] = useState(false);

  //Main table state management.
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [focusItem, setFocusItem] = useState<any>([]);

  // ATTN: read selected tab from URL, set to URL on tab change
  const [selectedTab, setSelectedTab] = useState("roles");
  const [action, setAction] = useState("add");

  //Modals
  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);
  const [isGroupDeleteConfirmationModalVisible, setGroupDeleteConfirmationModalVisible] = useState(false);

  // ATTN: explore if it's cleaner to merge these two states into one and parametrize the Modal
  const [isAddUserToGroupModalVisible, setAddUserToGroupModalVisible] = useState(false);
  const [isRemoveUserFromGroupModalVisible, setRemoveUserFromGroupModalVisible] = useState(false);

  const [isAmendItemModalVisible, setAmendItemModalVisible] = useState(false);

  function getPermissions(isLoading: boolean, permissionsData: PermissionsData, key: string) {
    if (isLoading) {
      return [];
    } else {
      return permissionsData[key];
    }
  }

  function displayAdminPolicy(editingItem: boolean) {
    if (!editingItem) {
      return (
        <Tabs
          activeTabId={selectedTab}
          onChange={({ detail }) => handleTabChange(detail.activeTabId)}
          tabs={[
            {
              label: "Roles",
              id: "roles",
              content: (
                <SpaceBetween direction="vertical" size="xs">
                  <ItemTable
                    schema={props.schemas.role}
                    schemaKeyAttribute={"role_id"}
                    schemaName={"role"}
                    dataAll={allData}
                    items={getPermissions(permissionsIsLoading, permissionsData, "roles")}
                    selectedItems={selectedItems}
                    handleSelectionChange={handleItemSelectionChange}
                    isLoading={permissionsIsLoading}
                    errorLoading={permissionsError}
                    handleRefreshClick={handleRefreshClick}
                    handleAddItem={handleAddItem}
                    handleDeleteItem={async function () {
                      setDeleteConfirmationModalVisible(true);
                    }}
                    handleEditItem={handleEditItem}
                    selectionType={"single"}
                  />
                  <DetailsView schemas={props.schemas} selectedItems={selectedItems} selectedTab={selectedTab} />
                </SpaceBetween>
              ),
            },
            {
              label: "Policies",
              id: "policies",
              content: (
                <SpaceBetween direction="vertical" size="xs">
                  <ItemTable
                    schema={props.schemas.policy}
                    schemaKeyAttribute={"policy_id"}
                    schemaName={"policie"}
                    dataAll={allData}
                    items={getPermissions(permissionsIsLoading, permissionsData, "policies")}
                    selectedItems={selectedItems}
                    handleSelectionChange={handleItemSelectionChange}
                    isLoading={permissionsIsLoading}
                    errorLoading={permissionsError}
                    handleRefreshClick={handleRefreshClick}
                    handleAddItem={handleAddItem}
                    handleDeleteItem={async function () {
                      setDeleteConfirmationModalVisible(true);
                    }}
                    handleEditItem={handleEditItem}
                    selectionType={"single"}
                  />
                  <DetailsView schemas={props.schemas} selectedItems={selectedItems} selectedTab={selectedTab} />
                </SpaceBetween>
              ),
            },
            {
              label: "Groups",
              id: "groups",
              content: (
                <SpaceBetween direction="vertical" size="xs">
                  <ItemTable
                    schema={props.schemas.group}
                    schemaKeyAttribute={"group_name"}
                    schemaName={"group"}
                    dataAll={permissionsData.groups}
                    items={getPermissions(permissionsIsLoading, permissionsData, "groups")}
                    isLoading={permissionsIsLoading}
                    errorLoading={permissionsError}
                    handleRefreshClick={handleRefreshClick}
                    handleAddItem={async function () {
                      setAmendItemModalVisible(true);
                    }}
                    handleDeleteItem={async function () {
                      setGroupDeleteConfirmationModalVisible(true);
                    }}
                    handleSelectionChange={handleItemSelectionChange}
                    selectionType={"single"}
                    selectedItems={selectedItems}
                  />
                  <DetailsView schemas={props.schemas} selectedItems={selectedItems} selectedTab={selectedTab} />
                </SpaceBetween>
              ),
            },
            {
              label: "Users",
              id: "users",
              content: (
                <SpaceBetween direction="vertical" size="xs">
                  <ItemTable
                    description={"Users must be created through Amazon Cognito or a federated IDP."}
                    schema={props.schemas.user}
                    schemaKeyAttribute={"userRef"}
                    schemaName={"user"}
                    dataAll={permissionsData.users}
                    items={permissionsIsLoading ? [] : permissionsData.users}
                    isLoading={permissionsIsLoading}
                    errorLoading={permissionsError}
                    handleRefreshClick={handleRefreshClick}
                    actionsButtonDisabled={false}
                    handleAction={handleActionClick}
                    actionItems={[
                      {
                        id: "add_group",
                        text: "Add users to group",
                        description: "Add users to group.",
                        disabled: selectedItems.length === 0,
                      },
                      {
                        id: "remove_group",
                        text: "Remove users to group",
                        description: "Remove users to group.",
                        disabled: selectedItems.length === 0,
                      },
                    ]}
                    handleSelectionChange={handleItemSelectionChange}
                    selectionType={"multi"}
                    selectedItems={selectedItems}
                  />
                  <DetailsView schemas={props.schemas} selectedItems={selectedItems} selectedTab={selectedTab} />
                </SpaceBetween>
              ),
            },
          ]}
        />
      );
    } else {
      return (
        <ItemAmend
          action={action}
          schemaName={selectedTab === "roles" ? "role" : "policy"}
          schemas={props.schemas}
          userAccess={props.userEntityAccess}
          item={focusItem}
          handleSave={handleSave}
          handleCancel={function () {
            setEditingItem(false);
          }}
        />
      );
    }
  }

  function handleAddItem() {
    setAction("add");
    setFocusItem({});
    setEditingItem(true);
  }

  function handleEditItem() {
    setAction("edit");
    setFocusItem(selectedItems[0]);
    setEditingItem(true);
  }

  function handleItemSelectionChange(selection: any[]) {
    setSelectedItems(selection);
    setFocusItem(selectedItems[0] ?? {});
  }

  async function handleSave(
    editItem: {
      policy_name: string;
      role_name: string;
    },
    action: string
  ) {
    let newItem = Object.assign({}, editItem);
    let notificationHeader = "policy";

    try {
      if (action === "edit" && selectedTab === "policies") {
        const apiAdmin = new AdminApiClient();

        await apiAdmin.putPolicy(newItem);

        addNotification({
          type: "success",
          dismissible: true,
          header: "Update " + notificationHeader,
          content: editItem.policy_name + " updated successfully.",
        });

        //Update permissions for user UI.
        await permissionsUpdate();

        setEditingItem(false);
        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});

        //Reload actual permissions for current user.
        await props.reloadPermissions();
      } else if (action === "edit" && selectedTab === "roles") {
        notificationHeader = "role";
        const apiAdmin = new AdminApiClient();

        await apiAdmin.putRole(newItem);

        addNotification({
          type: "success",
          dismissible: true,
          header: "Update " + notificationHeader,
          content: editItem.role_name + " updated successfully.",
        });

        //Update permissions for user UI.
        await permissionsUpdate();

        setEditingItem(false);
        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});

        //Reload actual permissions for current user.
        await props.reloadPermissions();
      } else if (action === "add" && selectedTab === "roles") {
        notificationHeader = "role";
        const apiAdmin = new AdminApiClient();

        await apiAdmin.postRole(newItem);

        addNotification({
          type: "success",
          dismissible: true,
          header: "Update " + notificationHeader,
          content: editItem.role_name + " updated successfully.",
        });

        //Update permissions for user UI.
        await permissionsUpdate();

        setEditingItem(false);
        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});

        //Reload actual permissions for current user.
        await props.reloadPermissions();
      } else if (action === "add" && selectedTab === "policies") {
        const apiAdmin = new AdminApiClient();

        await apiAdmin.postPolicy(newItem);

        addNotification({
          type: "success",
          dismissible: true,
          header: "Update " + notificationHeader,
          content: editItem.policy_name + " updated successfully.",
        });

        //Update permissions for user UI.
        await permissionsUpdate();

        setEditingItem(false);
        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});

        //Reload actual permissions for current user.
        await props.reloadPermissions();
      } else {
        setEditingItem(false);
      }
    } catch (e: any) {
      console.log(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: "Save " + notificationHeader,
        content: e.response?.data || "Unknown error occurred",
      });
    }
  }

  async function handleTabChange(tabselected: any) {
    setSelectedTab(tabselected);
    setSelectedItems([]);
  }

  async function handleRefreshClick() {
    await permissionsUpdate();
  }

  function handleActionClick(e: ClickEvent) {
    const action = e.detail.id;

    if (action === "add_group") {
      setAddUserToGroupModalVisible(true);
    } else if (action === "remove_group") {
      setRemoveUserFromGroupModalVisible(true);
    }
  }

  async function addUsersToGroups(groups: { selectedGroups: Array<any> }) {
    let notificationId;

    try {
      notificationId = addNotification({
        type: "success",
        loading: true,
        dismissible: false,
        header: "Update users",
        content: "Adding selected users to groups: " + groups.selectedGroups.map((group) => group.value),
      });

      let users = [];
      for (const user of selectedItems) {
        users.push({ username: user["userRef"], addGroups: groups.selectedGroups.map((group) => group.value) });
      }

      await new AdminApiClient().putUsers(users);

      await permissionsUpdate();

      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: "Update users",
        content: "Users added to groups: " + groups.selectedGroups.map((group) => group.value),
      });

      setSelectedItems([]);
    } catch (e: any) {
      console.log(e);
      addNotification({
        id: notificationId,
        type: "error",
        dismissible: true,
        header: "Update users",
        content: "Add to group failed: " + e.response?.data || e.message,
      });
    }
  }

  async function removeUsersFromGroups(groups: { selectedGroups: Array<any> }) {
    let notificationId;

    try {
      notificationId = addNotification({
        type: "success",
        loading: true,
        dismissible: false,
        header: "Update users",
        content: "Removing selected users from groups: " + groups.selectedGroups.map((group) => group.value),
      });

      let users = [];
      for (const user of selectedItems) {
        users.push({ username: user["userRef"], removeGroups: groups.selectedGroups.map((group) => group.value) });
      }

      await new AdminApiClient().putUsers(users);

      await permissionsUpdate();

      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: "Update users",
        content: "Users removed from groups: " + groups.selectedGroups.map((group) => group.value),
      });

      setSelectedItems([]);
    } catch (e: any) {
      console.log(e);
      addNotification({
        id: notificationId,
        type: "error",
        dismissible: true,
        header: "Update users",
        content: "Remove from group failed: " + e.response?.data || e.message || "",
      });
    }
  }

  async function createGroup(group: { group_name: string }) {
    let notificationId;

    try {
      notificationId = addNotification({
        type: "success",
        loading: true,
        dismissible: false,
        header: "Add group",
        content: "Adding new group: " + group.group_name,
      });

      await new AdminApiClient().postGroups({ groups: [group] });

      await permissionsUpdate();

      addNotification({
        id: notificationId,
        type: "success",
        dismissible: true,
        header: "Add group",
        content: "New group added: " + group.group_name,
      });

      setSelectedItems([]);
    } catch (e: any) {
      console.log(e);
      if (e.response?.data) {
        addNotification({
          id: notificationId,
          type: "error",
          dismissible: true,
          header: "Add group",
          content: "Add group failed: " + e.response?.data || e.message || "",
        });
      }
    }
  }

  async function handleDeleteItem() {
    let currentItem = 0;
    let notifcationHeader = "Group";

    setDeleteConfirmationModalVisible(false);
    setGroupDeleteConfirmationModalVisible(false);

    try {
      const apiAdmin = new AdminApiClient();

      if (selectedTab === "roles") {
        await apiAdmin.delRole(selectedItems[0].role_id);
        addNotification({
          type: "success",
          dismissible: true,
          header: notifcationHeader + " deleted successfully",
          content: selectedItems[0].role_name + " was deleted.",
        });
      }

      if (selectedTab === "policies") {
        notifcationHeader = "Policy";
        await apiAdmin.delPolicy(selectedItems[0].policy_id);
        addNotification({
          type: "success",
          dismissible: true,
          header: notifcationHeader + " deleted successfully",
          content: selectedItems[0].policy_name + " was deleted.",
        });
      }

      if (selectedTab === "groups") {
        notifcationHeader = "Group";
        await apiAdmin.delGroup(selectedItems[0].group_name);
        addNotification({
          type: "success",
          dismissible: true,
          header: notifcationHeader + " deleted successfully",
          content: selectedItems[0].group_name + " was deleted.",
        });
      }

      await permissionsUpdate();
      setSelectedItems([]);
    } catch (e: any) {
      console.log(e);
      addNotification({
        type: "error",
        dismissible: true,
        header: notifcationHeader + " deletion failed",
        content: selectedItems[currentItem].role_id || selectedItems[currentItem].policy_id + " failed to delete.",
      });
    }
  }

  return (
    <div>
      {props.schemaIsLoading ? (
        <StatusIndicator type="loading">Loading schema...</StatusIndicator>
      ) : (
        displayAdminPolicy(editingItem)
      )}

      <CMFModal
        onConfirmation={handleDeleteItem}
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        header={"Delete policy"}
      >
        {selectedItems.length === 1 ? (
          // ATTN: the text '... policy ...' is used even for Role, is this a bug?
          <SpaceBetween size="l">
            <p>Are you sure you wish to delete the selected policy?</p>
          </SpaceBetween>
        ) : (
          <p>Are you sure you wish to delete the {selectedItems.length} selected policies?</p>
        )}
      </CMFModal>
      <CMFModal
        onConfirmation={handleDeleteItem}
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isGroupDeleteConfirmationModalVisible}
        header={"Delete group"}
      >
        {selectedItems.length === 1 ? (
          <SpaceBetween size="l">
            <p>Are you sure you wish to delete the selected group?</p>
          </SpaceBetween>
        ) : (
          <p>Are you sure you wish to delete the {selectedItems.length} selected groups?</p>
        )}
      </CMFModal>
      <UserGroupsModal
        header={"Select groups to add"}
        visible={isAddUserToGroupModalVisible}
        onConfirmation={addUsersToGroups}
        groups={permissionsData.groups.map((group) => group.group_name)}
        closeModal={() => setAddUserToGroupModalVisible(false)}
      />
      <UserGroupsModal
        header={"Select groups to remove"}
        visible={isRemoveUserFromGroupModalVisible}
        onConfirmation={removeUsersFromGroups}
        groups={permissionsData.groups.map((group) => group.group_name)}
        closeModal={() => setRemoveUserFromGroupModalVisible(false)}
      />
      {isAmendItemModalVisible ? (
        <AmendItemModal
          title={"Add group"}
          onConfirmation={createGroup}
          closeModal={() => setAmendItemModalVisible(false)}
          userAccess={props.userEntityAccess}
          schemas={props.schemas}
          schemaName={"group"}
          item={{}}
        />
      ) : (
        <></>
      )}
    </div>
  );
};

export default AdminPermissions;
