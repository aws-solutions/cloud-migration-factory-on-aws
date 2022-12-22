/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import {
  Modal,
  Button,
  SpaceBetween,
  Box,
  FormField,
  Input,
  RadioGroup,
  Spinner, Checkbox, Textarea
} from "@awsui/components-react";

type Props = {
  children: React.ReactChild,
  closeModal: () => void,
  confirmAction: () => void,
};

const CredentialManagerModal = React.memo(
  ({
    children,
    closeModal,
    confirmAction,
    title,
    attribute,
    action
  }: Props) => {
    const domEl = document.getElementById("modal-root");
    const [localAttr, setLocalAttr] = useState(attribute);
    const [isDisabled, setIsDisabled] = useState(true);
    const [showSpinner, setShowSpinner] = useState(false);

    useEffect(() => {
      if (localAttr.secretType) {
        if (localAttr.secretType === "CE" || localAttr.secretType === "OS") {
          if (
            localAttr.secretName &&
            localAttr.secretName.trim() !== "" &&
            localAttr.userName &&
            localAttr.userName.trim() !== "" &&
            localAttr.password &&
            localAttr.password.trim() !== ""
          ) {
            setIsDisabled(false);
          } else {
            setIsDisabled(true);
          }
        } else if (localAttr.secretType === "keyValue") {
          if (
            localAttr.secretName &&
            localAttr.secretName.trim() !== "" &&
            localAttr.secretKey &&
            localAttr.secretKey.trim() !== "" &&
            localAttr.secretValue &&
            localAttr.secretValue.trim() !== ""
          ) {
            setIsDisabled(false);
          } else {
            setIsDisabled(true);
          }
        } else if (localAttr.secretType === "plainText") {
          if (
            localAttr.secretName &&
            localAttr.secretName.trim() !== "" &&
            localAttr.plainText &&
            localAttr.plainText.trim() !== ""
          ) {
            setIsDisabled(false);
          } else {
            setIsDisabled(true);
          }
        }
      }
    }, [localAttr]);

    function handleUserInput(value) {
      let newAttr = Object.assign({}, localAttr);
      newAttr[value.field] = value.value;

      setLocalAttr(newAttr);
    }

    //Encodes value as base64.
    function handleUserInputBase64(value, base64) {
      let newAttr = Object.assign({}, localAttr);
      if (base64){
        let base64EncodeValue = btoa(value.value.replace(/\n/g, "\\n"))
        newAttr[value.field] = base64EncodeValue;
      } else {
        newAttr[value.field] = value.value;
      }

      setLocalAttr(newAttr);
    }

    function handleSave(e) {
      setShowSpinner(true);
      confirmAction(localAttr, action);
    }

    if (!domEl) return null;

    return ReactDOM.createPortal(
      <Modal
        onDismiss={closeModal}
        visible={true}
        closeAriaLabel="Close"
        size="medium"
        footer={
          (
            <Box float="right">
              <SpaceBetween direction="horizontal" size="xs">
                <Button onClick={closeModal} variant="link" disabled={showSpinner}>
                  Cancel
                </Button>
                <Button
                  onClick={handleSave}
                  variant="primary"
                  disabled={isDisabled || showSpinner}
                >
                  Save
                </Button>
              </SpaceBetween>
            </Box>
          )
        }
        header={title}
      >
        {
          showSpinner ?
            <Box margin="xxl" padding="xxl" textAlign="center">
              <Spinner size="normal" /> Saving secret...
            </Box> :
            <SpaceBetween size="l">
              <FormField label="Secret Type" description="">
                <RadioGroup
                  value={localAttr.secretType}
                  onChange={(event) =>
                    handleUserInput({
                      field: "secretType",
                      value: event.detail.value,
                    })
                  }
                  items={[
                    {
                      value: "OS",
                      label: "OS Credentials (Username / Password or Key)",
                      disabled: (action === 'edit' && localAttr.secretType !== 'OS') ? true : false
                    },
                    {
                      value: "keyValue",
                      label: "Secret key/value",
                      disabled: (action === 'edit' && localAttr.secretType !== 'keyValue') ? true : false
                    },
                    {
                      value: "plainText",
                      label: "Plaintext",
                      disabled: (action === 'edit' && localAttr.secretType !== 'plainText') ? true : false
                    },
                  ]}
                />
              </FormField>

              <FormField label="Secret Name" description="">
                <Input
                  value={localAttr.secretName}
                  onChange={(event) =>
                    handleUserInput({
                      field: "secretName",
                      value: event.detail.value
                    })
                  }
                  autoFocus
                  disabled={(action === 'edit') ? true : false}
                />
              </FormField>

              {localAttr.secretType === "OS" && (
                <>
                  <FormField label="User Name" description="">
                    <Input
                      value={localAttr.userName}
                      onChange={(event) =>
                        handleUserInput({
                          field: "userName",
                          value: event.detail.value,
                        })
                      }
                    />
                  </FormField>
                  <FormField label="" description="">
                    <Checkbox
                      checked={localAttr.isSSHKey?localAttr.isSSHKey:false}
                      onChange={(event) =>
                        handleUserInput({
                          field: "isSSHKey",
                          value: event.detail.checked,
                        })
                      }
                    >
                      SSH key used
                    </Checkbox>
                  </FormField>

                  {
                    localAttr.isSSHKey
                    ?
                      <FormField label="SSH Key" description="">
                        <Textarea
                          value={localAttr.password}
                          onChange={(event) =>
                                handleUserInputBase64({
                                  field: "password",
                                  value: event.detail.value,
                                }, false)}
                          type="password"
                        />
                      </FormField>
                    :
                      <FormField label="Password" description="">
                        <Input
                          value={localAttr.password}
                          onChange={
                              (event) =>
                                handleUserInput({
                                  field: "password",
                                  value: event.detail.value
                                })}
                          type="password"
                        />
                      </FormField>
                  }

                  <FormField label="Description" description="">
                    <Input
                      value={localAttr.description}
                      onChange={(event) =>
                        handleUserInput({
                          field: "description",
                          value: event.detail.value,
                        })
                      }
                    />
                  </FormField>

                  <FormField label="OS Type" description="">
                    <RadioGroup
                      value={localAttr.osType}
                      onChange={(event) =>
                        handleUserInput({
                          field: "osType",
                          value: event.detail.value,
                        })
                      }
                      items={[
                        { value: "Linux", label: "Linux" },
                        { value: "Windows", label: "Windows" },
                      ]}
                    />
                  </FormField>
                </>
              )}

              {localAttr.secretType === "keyValue" && (
                <>
                  <FormField label="Key" description="">
                    <Input
                      value={localAttr.secretKey}
                      onChange={(event) =>
                        handleUserInput({
                          field: "secretKey",
                          value: event.detail.value,
                        })
                      }
                    />
                  </FormField>

                  <FormField label="Value" description="">
                    <Input
                      value={localAttr.secretValue}
                      onChange={(event) =>
                        handleUserInput({
                          field: "secretValue",
                          value: event.detail.value,
                        })
                      }
                    />
                  </FormField>

                  <FormField label="Description" description="">
                    <Input
                      value={localAttr.description}
                      onChange={(event) =>
                        handleUserInput({
                          field: "description",
                          value: event.detail.value,
                        })
                      }
                    />
                  </FormField>
                </>
              )}

              {localAttr.secretType === "plainText" && (
                <>
                  <FormField label="Plaintext" description="">
                    <Input
                      value={localAttr.plainText}
                      onChange={(event) =>
                        handleUserInput({
                          field: "plainText",
                          value: event.detail.value,
                        })
                      }
                      type="password"
                    />
                  </FormField>

                  <FormField label="Description" description="">
                    <Input
                      value={localAttr.description}
                      onChange={(event) =>
                        handleUserInput({
                          field: "description",
                          value: event.detail.value,
                        })
                      }
                    />
                  </FormField>
                </>
              )}
            </SpaceBetween>
        }
        {children}
      </Modal>,
      domEl
    );
  }
);

export default CredentialManagerModal;
