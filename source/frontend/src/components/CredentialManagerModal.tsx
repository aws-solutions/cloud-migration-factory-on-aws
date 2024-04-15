/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from "react";
import {
  Box,
  Button,
  Checkbox,
  FormField,
  Input,
  Modal,
  RadioGroup,
  SpaceBetween,
  Spinner,
  Textarea
} from "@awsui/components-react";

type CredentialManagerModalProps = {
  title: string;
  closeModal: () => void,
  onConfirmation: (attribute: any, action?: string) => void,
  attribute: any,
  action: string
}

const CredentialManagerModal = (
  {
    closeModal,
    onConfirmation,
    title,
    attribute,
    action
  }: CredentialManagerModalProps
) => {
  const [localAttr, setLocalAttr] = useState(attribute);
  const [isDisabled, setIsDisabled] = useState(true);
  const [showSpinner, setShowSpinner] = useState(false);

  function updateForCEorOS() {
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
  }

  function updateForKeyValue() {
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
  }

  function updateForPlainText() {
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

  useEffect(() => {
    if (localAttr.secretType) {
      if (localAttr.secretType === "CE" || localAttr.secretType === "OS") {
        updateForCEorOS();
      } else if (localAttr.secretType === "keyValue") {
        updateForKeyValue();
      } else if (localAttr.secretType === "plainText") {
        updateForPlainText();
      }
    }
  }, [localAttr]);

  function handleUserInput(value: {
    field: any;
    value: any;
  }) {
    let newAttr = Object.assign({}, localAttr);
    newAttr[value.field] = value.value;

    setLocalAttr(newAttr);
  }

  //Encodes value as base64.
  function handleUserInputBase64(
    value: {
      field: any;
      value: any;
    }, base64: boolean
  ) {
    let newAttr = Object.assign({}, localAttr);
    if (base64) {
      newAttr[value.field] = btoa(value.value.replace(/\n/g, "\\n"));
    } else {
      newAttr[value.field] = value.value;
    }

    setLocalAttr(newAttr);
  }

  function handleSave() {
    setShowSpinner(true);
    if (onConfirmation) onConfirmation(localAttr, action);
  }

  return (<Modal
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
            <Spinner size="normal"/> Saving secret...
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
                    disabled: (action === 'edit' && localAttr.secretType !== 'OS')
                  },
                  {
                    value: "keyValue",
                    label: "Secret key/value",
                    disabled: (action === 'edit' && localAttr.secretType !== 'keyValue')
                  },
                  {
                    value: "plainText",
                    label: "Plaintext",
                    disabled: (action === 'edit' && localAttr.secretType !== 'plainText')
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
                disabled={(action === 'edit')}
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
                    checked={localAttr.isSSHKey ? localAttr.isSSHKey : false}
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
                      {value: "Linux", label: "Linux"},
                      {value: "Windows", label: "Windows"},
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
    </Modal>
  )
};

export default CredentialManagerModal;
