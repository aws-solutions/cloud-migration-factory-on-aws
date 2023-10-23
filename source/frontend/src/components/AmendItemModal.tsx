// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {useEffect, useState} from 'react';
import ReactDOM from 'react-dom'
import {
  Modal,
  Button,
  SpaceBetween,
  Box
} from '@awsui/components-react';
import {setNestedValuePath} from "../resources/main";
import AllAttributes from "./ui_attributes/AllAttributes";

type Props = {
  children: React.ReactChild,
  closeModal: () => void,
  confirmAction: () => void
};

const AmendItemModal = React.memo(({ children, closeModal , confirmAction, title, item, schemas, schemaName, userAccess, action}: Props) => {
  const domEl = document.getElementById('modal-root')
  const [localObject, setLocalObject] = useState(item);
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState([]);
  const [validForm, setFormValidation] = useState(false);

  function handleUserInput (value){

    let newAttr = Object.assign({}, localObject);
    setNestedValuePath(newAttr, value.field, value.value);

    setLocalObject(newAttr);

  }

  async function handleSave (e){

    setSaving(true);

    closeModal();

    confirmAction(localObject, action);

  }

  function handleUpdateFormErrors (newErrors){
    setFormErrors(newErrors);
  }

  useEffect(() => {
    if (formErrors.length === 0){
      setFormValidation(true);
    } else {
      setFormValidation(false);
    }
  }, [formErrors]);

  if (!domEl) return null

  return ReactDOM.createPortal(
    <Modal
      onDismiss={confirmAction ? closeModal : undefined}
      visible={true}
      closeAriaLabel="Close"
      size="medium"
      footer={confirmAction ?
            (
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={closeModal} variant="link">Cancel</Button>
                  <Button onClick={handleSave} disabled={!validForm} loading={saving} variant="primary">Add</Button>
                </SpaceBetween>
              </Box>
          )
          :
          undefined
      }
      header={title}
    >
      <SpaceBetween size="l">
        <AllAttributes
          schema={schemas[schemaName]}
          schemaName={schemaName}
          schemas={schemas}
          userAccess={userAccess}
          item={localObject}
          handleUserInput={handleUserInput}
          hideAudit={true}
          handleUpdateValidationErrors={handleUpdateFormErrors}
        />
      </SpaceBetween>
      {children}
    </Modal>,
    domEl
  )
});

export default AmendItemModal;
