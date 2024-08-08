/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from "react";
import { Box, Button, FormField, Modal, Multiselect, SpaceBetween } from "@awsui/components-react";
import { setNestedValuePath } from "../resources/main";

type UserGroupsModalProps = {
  groups: string[];
  header: string;
  visible: boolean;
  closeModal: () => void;
  onConfirmation: (attribute: any) => void;
};

export const UserGroupsModal = ({ closeModal, onConfirmation, header, groups, visible }: UserGroupsModalProps) => {
  const [localObject, setLocalObject] = useState<any>({});
  const [saving, setSaving] = useState(false);

  function handleUserInput(value: { field: any; value: any }) {
    let newAttr = Object.assign({}, localObject);
    setNestedValuePath(newAttr, value.field, value.value);

    setLocalObject(newAttr);
  }

  async function handleSave() {
    setSaving(true);
    closeModal();
    onConfirmation(localObject);
  }

  if (!visible) return <></>;

  return (
    <Modal
      onDismiss={closeModal}
      visible={true}
      closeAriaLabel="Close"
      size="medium"
      footer={
        <Box float="right">
          <SpaceBetween direction="horizontal" size="xs">
            <Button onClick={closeModal} variant="link">
              Cancel
            </Button>
            <Button onClick={handleSave} loading={saving} variant="primary">
              Update
            </Button>
          </SpaceBetween>
        </Box>
      }
      header={header}
    >
      <SpaceBetween size="l">
        <FormField label="Group selection" description="Select the groups to amend">
          <Multiselect
            selectedOptions={localObject.selectedGroups ? localObject.selectedGroups : []}
            onChange={(event) =>
              handleUserInput({
                field: "selectedGroups",
                value: event.detail.selectedOptions != null ? event.detail.selectedOptions : [],
              })
            }
            options={groups.map((item) => ({ value: item, label: item }))}
            selectedAriaLabel={"selected"}
            filteringType="auto"
          />
        </FormField>
      </SpaceBetween>
    </Modal>
  );
};
