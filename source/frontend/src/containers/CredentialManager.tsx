// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import {
    SpaceBetween
} from '@awsui/components-react';

import CredentialManagerTable from '../components/CredentialManagerTable';
import { useCredentialManager } from '../actions/CredentialManagerHook';
import { useModal } from '../actions/Modal';
import { useCredentialManagerModal } from '../actions/CredentialManagerModalHook';
import Admin from "../actions/admin";
import {parsePUTResponseErrors} from "../resources/recordFunctions";

const CredentialManager = (props) => {
    const [modalTitle, setModalTitle] = useState('');
    const [{ isLoading: secretDataIsLoading, data: secretData, error: secretDataErrorLoading }, { getSecretList }] = useCredentialManager();

    // Main table state management
    const [selectedItems, setSelectedItems] = useState([]);
    const [focusItem, setFocusItem] = useState({});
    const [action, setAction] = useState('');

    //Modals
    const { show: showCredentialManagerModal, hide: hideCredentialManagerModal, RenderModal: CredentialManagerModal } = useCredentialManagerModal();
    const { show: showDeleteConfirmaton, hide: hideDeleteConfirmaton, RenderModal: DeleteModal } = useModal();

    function apiActionErrorHandler(action, e){
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
            header: action + " secret " + selectedItems[0].Name,
            content: (response)
        });
    }


    function handleNotification(notification) {
        props.updateNotification('add', notification)
    }

    function handleItemSelectionChange(selection) {
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
        showCredentialManagerModal();
        setFocusItem({ secretType: "OS", osType: "Linux" });
    }

    async function handleDeleteItemClick(e) {
        e.preventDefault();
        setModalTitle('Delete secret');
        showDeleteConfirmaton();
    }

    async function handleEditItem() {
        setModalTitle('Edit secret');
        setAction('edit');
        showCredentialManagerModal();

        if (selectedItems[0].data.SECRET_TYPE === 'OS') {
            setFocusItem({ ...selectedItems[0], secretName: selectedItems[0].Name, secretType: selectedItems[0].data.SECRET_TYPE, userName: selectedItems[0].data.USERNAME, password: selectedItems[0].data.PASSWORD, osType: selectedItems[0].data.OS_TYPE, description: selectedItems[0].Description, isSSHKey: selectedItems[0].data.IS_SSH_KEY });
        } else if (selectedItems[0].data.SECRET_TYPE === 'keyValue') {
            setFocusItem({ ...selectedItems[0], secretName: selectedItems[0].Name, secretType: selectedItems[0].data.SECRET_TYPE, secretKey: selectedItems[0].data.SECRET_KEY, secretValue: selectedItems[0].data.SECRET_VALUE, description: selectedItems[0].Description });
        } else if (selectedItems[0].data.SECRET_TYPE === 'plainText') {
            setFocusItem({ ...selectedItems[0], secretName: selectedItems[0].Name, secretType: selectedItems[0].data.SECRET_TYPE, plainText: selectedItems[0].data.SECRET_STRING, description: selectedItems[0].Description });
        }
    }

    async function handleDeleteItem(e) {
        e.preventDefault();

        hideDeleteConfirmaton();

        try {
            const secretFormData = {
                secretName: selectedItems[0].Name,
                secretType: selectedItems[0].data.SECRET_TYPE
            }

            const AdminApi = await Admin.initializeCurrentSession();
            await AdminApi.deleteCredential(secretFormData);

            hideCredentialManagerModal();

            handleNotification({
                type: 'success',
                dismissible: true,
                header: action + ' secret',
                content: selectedItems[0].Name + " secret was deleted successfully.",
            });

            getSecretList();
        } catch (e) {
            apiActionErrorHandler(action, e);
        }

        setSelectedItems([]);
        setFocusItem({});
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

    async function saveNewRecord(secretData){
        let secretFormData = {
            secretName: secretData.secretName,
            secretType: secretData.secretType,
            description: (secretData.description !== undefined && secretData.description.trim() !== '') ? secretData.description : 'Secret for Migration Factory'
        };

        hideCredentialManagerModal();

        try {
            if (secretData.secretType === 'OS') {
                if (secretData.isSSHKey) {
                    //base64 encode key
                    secretData.password = btoa(secretData.password.replace(/\n/g, "\\n"))
                }
                secretFormData.user = secretData.userName;
                secretFormData.password = secretData.password;
                secretFormData.osType = secretData.osType;
                secretFormData.isSSHKey = secretData.isSSHKey;
            } else if (secretData.secretType === 'keyValue') {
                secretFormData.secretKey = secretData.secretKey;
                secretFormData.secretValue = secretData.secretValue;
            } else if (secretData.secretType === "plainText") {
                secretFormData.secretString = secretData.plainText;
            }

            if (secretFormData){
                try {
                    const AdminApi = await Admin.initializeCurrentSession();
                    await AdminApi.addCredential(secretFormData)
                } catch (e) {
                    apiActionErrorHandler(action,e);
                }

                handleNotification({
                    type: 'success',
                    dismissible: true,
                    header: action + ' secret',
                    content: secretFormData.secretName + ' secret was added successfully.',
                });
                getSecretList();
            }

        } catch (e) {
            console.log(e);
        }

        //This is needed to ensure the item in selectApps reflects new updates
        setSelectedItems([]);
        setFocusItem({});
    }

    async function saveUpdatedRecord(secretData){
        let secretFormData = {
            secretName: secretData.secretName,
            secretType: secretData.secretType,
            description: secretData.description}

        hideCredentialManagerModal();

        try {
            if (secretData.secretType === 'OS') {

                if (secretData.password === '*********') {
                    // password not updated so do not include in update.
                    delete secretData.password;
                } else {
                    if (secretData.isSSHKey) {
                        //base64 encode key.
                        secretData.password = btoa(secretData.password.replace(/\n/g, "\\n"))
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

            try {
                const AdminApi = await Admin.initializeCurrentSession();
                await AdminApi.updateCredential(secretFormData)
            } catch (e) {
                apiActionErrorHandler(action,e);
            }

            handleNotification({
                type: 'success',
                dismissible: true,
                header: action + ' secret',
                content: secretFormData.secretName + ' secret was saved successfully.',
            });
            getSecretList();
        } catch (e) {
            console.log(e);
        }

        setSelectedItems([]);
        setFocusItem({});
    }

    async function handleSave(secretData, action) {
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
                  errorLoading={secretDataErrorLoading}
                  sendNotification={handleNotification}
                  selectedItems={selectedItems}
                  handleSelectionChange={handleItemSelectionChange}
                  handleAddItem={handleAddItem}
                  handleDeleteItem={getDeleteHandler(selectedItems)}
                  handleEditItem={handleEditItem}
                  handleRefresh={getSecretList}
                />

            </SpaceBetween>
            <CredentialManagerModal
              title={modalTitle}
              onConfirmation={handleSave}
              attribute={focusItem}
              action={action}
            />
            <DeleteModal
              title={modalTitle}
              onConfirmation={handleDeleteItem}
            >
                <p>Are you sure you wish to delete the selected secret</p>
            </DeleteModal>
          </>
    );
}

export default CredentialManager;
