import React, { useState, useEffect } from 'react';
import { Auth } from "aws-amplify";
import {
    SpaceBetween
} from '@awsui/components-react';

import CredentialManagerTable from '../components/CredentialManagerTable';
import { useCredentialManager } from '../actions/CredentialManagerHook';
import { useModal } from '../actions/Modal.js';
import { useCredentialManagerModal } from '../actions/CredentialManagerModalHook.js';

const CredentialManager = (props) => {
    const [decodedJwt, setDecodedJwt] = useState({});
    const [jwt, setJwt] = useState('');
    const [modalTitle, setModalTitle] = useState('');
    const [{ isLoading: secretDataIsLoading, data: secretData, error: secretDataErrorLoading }, { getSecretList }] = useCredentialManager();

    // Main table state management
    const [selectedItems, setSelectedItems] = useState([]);
    const [focusItem, setFocusItem] = useState({});
    const [action, setAction] = useState('');

    //Modals
    const { show: showCredentialManagerModal, hide: hideCredentialManagerModal, RenderModal: CredentialManagerModal } = useCredentialManagerModal();
    const { show: showDeleteConfirmaton, hide: hideDeleteConfirmaton, RenderModal: DeleteModal } = useModal();

    async function decodeJwt(token) {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace('-', '+').replace('_', '/');
        const decodedJwt = JSON.parse(window.atob(base64));
        setDecodedJwt(decodedJwt);
    }

    async function getToken() {
        try {
            const session = await Auth.currentSession();
            const token = session.idToken.jwtToken;
            setJwt(token);

        } catch (e) {
            console.log(e);
        }
    }


    useEffect(() => {
        getToken();
    }, []);

    useEffect(() => {
        if (jwt !== '') {
            decodeJwt(jwt);
        }
    }, [jwt]);

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

    async function fetchApi(method, formData, apiEndpoint, action, token) {

        let response = null;

        const requestPayload = {
            method: method,
            headers: {
                Authorization: token
            },
            body: JSON.stringify(formData)
        };

        try {
            response = await fetch(apiEndpoint, requestPayload);
        } catch (e) {
            console.log(e);
            handleNotification({
                type: 'error',
                dismissible: true,
                header: action + ' secret',
                content: action + ' secret  ' + selectedItems[0].Name + '  API call was unsuccessful. This is probably due to a change performed on the Secret outside of CMF, please refresh the credentials list and try again.',
            });
        }

        hideCredentialManagerModal();

        if (method === 'POST') {
            if (response.status === 200) {
                handleNotification({
                    type: 'success',
                    dismissible: true,
                    header: action + ' secret',
                    content: formData.secretName + ' secret was added successfully.',
                });
                getSecretList();
            } else if (response.status === 202) {
                handleNotification({
                    type: 'error',
                    dismissible: true,
                    header: action + ' secret',
                    content: formData.secretName + ' secret is already exist',
                });
            } else {
                handleNotification({
                    type: 'error',
                    dismissible: true,
                    header: action + ' secret',
                    content: await response.text(),
                });
            }
        } else if (method === 'DELETE') {
            if (response.status === 200) {
                handleNotification({
                    type: 'success',
                    dismissible: true,
                    header: action + ' secret',
                    content: selectedItems[0].Name + " secret was deleted successfully.",
                });
                getSecretList();
            } else {
                handleNotification({
                    type: 'error',
                    dismissible: true,
                    header: action + ' secret',
                    content: selectedItems[0].Name + ' secret was failed to delete.',
                });
            }
        } else if (method === 'PUT') {
            if (response.status === 200) {
                handleNotification({
                    type: 'success',
                    dismissible: true,
                    header: action + ' secret',
                    content: selectedItems[0].Name + " secret was updated successfully.",
                });
                getSecretList();
            } else {
                handleNotification({
                    type: 'error',
                    dismissible: true,
                    header: action + ' secret',
                    content: await response.text(),
                });
            }
        }
    }

    async function handleEditItem() {
        setModalTitle('Edit secret');
        setAction('edit');
        showCredentialManagerModal();

        if (selectedItems[0].data.SECRET_TYPE === 'OS') {
            console.log(selectedItems[0])
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

            await fetchApi('DELETE', secretFormData, window.env.API_ADMIN + '/admin/credentialmanager', 'Delete', jwt);

        } catch (e) {
            console.log(e);
        }

        setSelectedItems([]);
        setFocusItem({});
    }

    async function handleSave(secretData, action) {
        if (action === 'add') {
            try {
                if (secretData.secretType === 'OS') {
                    if (secretData.isSSHKey)
                      //base64 encode key
                        secretData.password = btoa(secretData.password.replace(/\n/g, "\\n"))
                    const secretFormData = {
                        secretName: secretData.secretName,
                        user: secretData.userName,
                        password: secretData.password,
                        secretType: secretData.secretType,
                        osType: secretData.osType,
                        isSSHKey: secretData.isSSHKey,
                        description: (secretData.description !== undefined && secretData.description.trim() !== '') ? secretData.description : 'Secret for Migration Factory'
                    }

                    await fetchApi('POST', secretFormData, window.env.API_ADMIN + '/admin/credentialmanager', 'Add', jwt);
                } else if (secretData.secretType === 'keyValue') {
                    const secretFormData = {
                        secretName: secretData.secretName,
                        secretKey: secretData.secretKey,
                        secretValue: secretData.secretValue,
                        secretType: secretData.secretType,
                        description: (secretData.description !== undefined && secretData.description.trim() !== '') ? secretData.description : 'Secret for Migration Factory'
                    }

                    await fetchApi('POST', secretFormData, window.env.API_ADMIN + '/admin/credentialmanager', 'Add', jwt);
                } else if (secretData.secretType === "plainText") {
                    const secretFormData = {
                        secretName: secretData.secretName,
                        secretString: secretData.plainText,
                        secretType: "plainText",
                        description: (secretData.description !== undefined && secretData.description.trim() !== '') ? secretData.description : 'Secret for Migration Factory'
                    }

                    await fetchApi('POST', secretFormData, window.env.API_ADMIN + '/admin/credentialmanager', 'Add', jwt);
                }
            } catch (e) {
                console.log(e);
            }

            //This is needed to ensure the item in selectApps reflects new updates
            setSelectedItems([]);
            setFocusItem({});
        } else if (action === 'edit') {
            try {
                if (secretData.secretType === 'OS') {
                    if (secretData.isSSHKey)
                        //base64 encode key
                        secretData.password = btoa(secretData.password.replace(/\n/g, "\\n"))
                    const secretFormData = {
                        secretName: secretData.secretName,
                        user: secretData.userName,
                        password: secretData.password,
                        secretType: secretData.secretType,
                        osType: secretData.osType,
                        description: secretData.description,
                        isSSHKey: secretData.isSSHKey
                    }

                    await fetchApi('PUT', secretFormData, window.env.API_ADMIN + '/admin/credentialmanager', 'Update', jwt);
                } else if (secretData.secretType === 'keyValue') {
                    const secretFormData = {
                        secretName: secretData.secretName,
                        secretKey: secretData.secretKey,
                        secretValue: secretData.secretValue,
                        secretType: secretData.secretType,
                        description: secretData.description
                    }

                    await fetchApi('PUT', secretFormData, window.env.API_ADMIN + '/admin/credentialmanager', 'Update', jwt);
                } else if (secretData.secretType === "plainText") {
                    const secretFormData = {
                        secretName: secretData.secretName,
                        secretString: secretData.plainText,
                        secretType: "plainText",
                        description: secretData.description
                    }

                    await fetchApi('PUT', secretFormData, window.env.API_ADMIN + '/admin/credentialmanager', 'Update', jwt);
                }
            } catch (e) {
                console.log(e);
            }

            setSelectedItems([]);
            setFocusItem({});
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
                  handleDeleteItem={selectedItems.length !== 0 ? !selectedItems[0].system ? handleDeleteItemClick : undefined : handleDeleteItemClick}
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
