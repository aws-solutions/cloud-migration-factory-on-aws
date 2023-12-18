/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useContext, useState} from 'react';
import {SpaceBetween} from '@awsui/components-react';

import CredentialManagerTable from '../components/CredentialManagerTable';
import {useCredentialManager} from '../actions/CredentialManagerHook';
import AdminApiClient from "../api_clients/adminApiClient";
import {parsePUTResponseErrors} from "../resources/recordFunctions";
import {NotificationContext} from "../contexts/NotificationContext";
import CredentialManagerModal from "../components/CredentialManagerModal";
import {CMFModal} from "../components/Modal";

type SecretFormData = {
  secretName: string;
  secretType: string;
  description?: string;
  password?: string;
  isSSHKey: boolean;
  userName: string;
  osType: string;
  secretKey: string;
  secretValue: string;
  plainText: string
};
const CredentialManager = () => {
  const {addNotification} = useContext(NotificationContext);

  const [modalTitle, setModalTitle] = useState('');
  const [{
    isLoading: secretDataIsLoading,
    data: secretData,
    error: secretDataErrorLoading
  }, {getSecretList}] = useCredentialManager();

  // Main table state management
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [focusItem, setFocusItem] = useState({});
  const [action, setAction] = useState('');

  //Modals
  const [isCredentialManagerModalVisible, setCredentialManagerModalVisible] = useState(false)
  const [isDeleteConfirmationModalVisible, setDeleteConfirmationModalVisible] = useState(false);

  const adminApiClient = new AdminApiClient();

  function apiActionErrorHandler(action: string, secretName: string, e: any) {
    console.error(e);
    let response = '';
    //Check if errors key exists from Lambda errors.
    if (e.response.data?.errors) {
      response = parsePUTResponseErrors(e.response.data.errors).join(', ');
    } else {
      response = e.response.data?.cause || 'Unknown error occurred.';
    }

    addNotification({
      type: 'error',
      dismissible: true,
      header: action + " secret " + secretName,
      content: (response)
    })
  }

  function handleItemSelectionChange(selection: React.SetStateAction<any[]>) {
    setSelectedItems(selection);

    if (selectedItems.length !== 0) {
      setFocusItem(selectedItems[0]);
    } else {
      setFocusItem({});
    }
  }

  function handleAddItem() {
    setModalTitle('Create secret');
    setAction('add');
    setCredentialManagerModalVisible(true);
    setFocusItem({secretType: "OS", osType: "Linux"});
  }

  async function handleEditItem() {
    setModalTitle('Edit secret');
    setAction('edit');
    setCredentialManagerModalVisible(true);

    if (selectedItems[0].data.SECRET_TYPE === 'OS') {
      setFocusItem({
        ...selectedItems[0],
        secretName: selectedItems[0].Name,
        secretType: selectedItems[0].data.SECRET_TYPE,
        userName: selectedItems[0].data.USERNAME,
        password: selectedItems[0].data.PASSWORD,
        osType: selectedItems[0].data.OS_TYPE,
        description: selectedItems[0].Description,
        isSSHKey: selectedItems[0].data.IS_SSH_KEY
      });
    } else if (selectedItems[0].data.SECRET_TYPE === 'keyValue') {
      setFocusItem({
        ...selectedItems[0],
        secretName: selectedItems[0].Name,
        secretType: selectedItems[0].data.SECRET_TYPE,
        secretKey: selectedItems[0].data.SECRET_KEY,
        secretValue: selectedItems[0].data.SECRET_VALUE,
        description: selectedItems[0].Description
      });
    } else if (selectedItems[0].data.SECRET_TYPE === 'plainText') {
      setFocusItem({
        ...selectedItems[0],
        secretName: selectedItems[0].Name,
        secretType: selectedItems[0].data.SECRET_TYPE,
        plainText: selectedItems[0].data.SECRET_STRING,
        description: selectedItems[0].Description
      });
    }
  }

  async function handleDeleteItem() {
    setDeleteConfirmationModalVisible(false);

    try {
      const secretFormData = {
        secretName: selectedItems[0].Name,
        secretType: selectedItems[0].data.SECRET_TYPE
      }

      await adminApiClient.deleteCredential(secretFormData);

      setCredentialManagerModalVisible(false);

      addNotification({
        type: 'success',
        dismissible: true,
        header: action + ' secret',
        content: selectedItems[0].Name + " secret was deleted successfully.",
      })

      await getSecretList();
    } catch (e: any) {
      apiActionErrorHandler(action, selectedItems[0].Name, e);
    }

    setSelectedItems([]);
    setFocusItem({});
  }

  function getDeleteHandler(selectedItems: any[]) {
    if (selectedItems.length !== 0 && selectedItems[0].system)
      return undefined;

    return async function () {
      setDeleteConfirmationModalVisible(true);
    };
  }

  async function saveNewRecord(secretData: {
    secretName: any;
    secretType: string;
    description: string | undefined;
    isSSHKey: any;
    password?: string;
    userName: any;
    osType: any;
    secretKey: any;
    secretValue: any;
    plainText: any;
  }) {
    setCredentialManagerModalVisible(false);

    let secretFormData = buildSecretFormData(secretData);

    //This is needed to ensure the item in selectApps reflects new updates
    setSelectedItems([]);
    setFocusItem({});

    try {
      await adminApiClient.addCredential(secretFormData)
    } catch (e: any) {
      apiActionErrorHandler(action, secretData.secretName, e);
    }

    addNotification({
      type: 'success',
      dismissible: true,
      header: action + ' secret',
      content: secretFormData.secretName + ' secret was added successfully.',
    })
    await getSecretList();


  }

  function buildSecretFormData(secretData: SecretFormData) {
    let secretFormData: any = {
      secretName: secretData.secretName,
      secretType: secretData.secretType,
      description: secretData.description ?? "Secret for Migration Factory"
    }

    if (secretData.secretType === 'OS') {

      if (secretData.password === '*********') {
        // password not updated so do not include in update.
        delete secretData.password;
      } else {
        if (secretData.isSSHKey) {
          //base64 encode key.
          secretData.password = btoa(secretData.password!.replace(/\n/g, "\\n"))
        }
      }
      secretFormData.user = secretData.userName;
      secretFormData.password = secretData.password ? secretData.password : undefined;
      secretFormData.osType = secretData.osType;
      secretFormData.isSSHKey = secretData.isSSHKey;
    } else if (secretData.secretType === 'keyValue') {
      secretFormData.secretKey = secretData.secretKey;
      secretFormData.secretValue = secretData.secretValue;
    } else if (secretData.secretType === "plainText") {
      secretFormData.secretString = secretData.plainText;
    }
    return secretFormData;
  }

  async function saveUpdatedRecord(secretData: {
    secretName: any;
    secretType: string;
    description: any;
    password?: string;
    isSSHKey: any;
    userName: any;
    osType: any;
    secretKey: any;
    secretValue: any;
    plainText: any;
  }) {
    setCredentialManagerModalVisible(false);

    let secretFormData = buildSecretFormData(secretData);

    //This is needed to ensure the item in selectApps reflects new updates
    setSelectedItems([]);
    setFocusItem({});

    try {
      await adminApiClient.updateCredential(secretFormData)
    } catch (e: any) {
      apiActionErrorHandler(action, secretData.secretName, e);
    }

    addNotification({
      type: 'success',
      dismissible: true,
      header: action + ' secret',
      content: secretFormData.secretName + ' secret was saved successfully.',
    })

  }

  async function handleSave(secretData: {
    secretName: any;
    secretType: string;
    description: any;
    isSSHKey: any;
    password?: string;
    userName: any;
    osType: any;
    secretKey: any;
    secretValue: any;
    plainText: any;
  }, action: string) {
    if (action === 'add') {
      await saveNewRecord(secretData);
    } else if (action === 'edit') {
      await saveUpdatedRecord(secretData);
    }

    await getSecretList()
  }

  return (
    <>
      <SpaceBetween direction="vertical" size="xs">
        <CredentialManagerTable
          items={secretData}
          isLoading={secretDataIsLoading}
          selectedItems={selectedItems}
          handleSelectionChange={handleItemSelectionChange}
          handleAddItem={handleAddItem}
          handleDeleteItem={getDeleteHandler(selectedItems)}
          handleEditItem={handleEditItem}
          handleRefresh={getSecretList}
        />

      </SpaceBetween>
      {isCredentialManagerModalVisible ?
        <CredentialManagerModal
          title={modalTitle}
          onConfirmation={(secretData) => handleSave(secretData, action)}
          attribute={focusItem}
          action={action}
          closeModal={() => setCredentialManagerModalVisible(false)}
        /> : <></>}
      <CMFModal
        onDismiss={() => setDeleteConfirmationModalVisible(false)}
        visible={isDeleteConfirmationModalVisible}
        onConfirmation={handleDeleteItem}
        header={'Delete secret'}
      >
        <p>Are you sure you wish to delete the selected secret?</p>
      </CMFModal>
    </>
  );
}

export default CredentialManager;
