// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import ReactDOM from 'react-dom'
import {
  Modal,
  Button,
  SpaceBetween,
  Box,
  FormField,
  Multiselect,
} from '@awsui/components-react';
import {setNestedValuePath} from "../resources/main";

type Props = {
  children: React.ReactChild,
  closeModal: () => void,
  confirmAction: () => void
};

const UserGroupsModal = React.memo(({ children, closeModal , confirmAction, title, groups , action}: Props) => {
  const domEl = document.getElementById('modal-root')
  const [localObject, setLocalObject] = useState({});
  const [saving, setSaving] = useState(false);


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
                  <Button onClick={handleSave} loading={saving} variant="primary">Update</Button>
                </SpaceBetween>
              </Box>
          )
          :
          undefined
      }
      header={title}
    >
      <SpaceBetween size="l">
        <FormField
          label="Group selection"
          description="Select the groups to amend"
        >

          <Multiselect
            selectedOptions={localObject.selectedGroups ? localObject.selectedGroups : []}
            onChange={event => handleUserInput({
              field: 'selectedGroups',
              value: event.detail.selectedOptions != null ? event.detail.selectedOptions : [],
            })}
            options={groups.map(item => ({'value': item, 'label': item}))}
            selectedAriaLabel={'selected'}
            filteringType="auto"
          />
        </FormField>
        </SpaceBetween>
      {children}
    </Modal>,
    domEl
  )
});

export default UserGroupsModal;
