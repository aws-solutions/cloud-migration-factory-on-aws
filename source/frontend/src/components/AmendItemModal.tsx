/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { ReactNode, useEffect, useState } from "react";
import { Box, Button, Modal, SpaceBetween } from "@cloudscape-design/components";
import { setNestedValuePath } from "../resources/main";
import AllAttributes from "./ui_attributes/AllAttributes";
import { EntitySchema } from "../models/EntitySchema";
import { UserAccess } from "../models/UserAccess";

export type AmendItemModalProps = {
  title: string;
  onConfirmation: (localObject: any) => void;
  closeModal: () => void;
  item: any;
  schemas: Record<string, EntitySchema>;
  schemaName: string;
  userAccess: UserAccess;
  children?: ReactNode;
};

const AmendItemModal = ({
  children,
  closeModal,
  onConfirmation,
  title,
  item,
  schemas,
  schemaName,
  userAccess,
}: AmendItemModalProps) => {
  const [localObject, setLocalObject] = useState(item);
  const [saving, setSaving] = useState(false);
  const [formErrors, setFormErrors] = useState<any[]>([]);
  const [validForm, setFormValidation] = useState(false);

  function handleUserInput(value: Array<{ field: any; value: any }>) {
    let newAttr = Object.assign({}, localObject);
    setNestedValuePath(newAttr, value[0].field, value[0].value);

    setLocalObject(newAttr);
  }

  async function handleSave() {
    setSaving(true);
    closeModal();
    onConfirmation(localObject);
  }

  useEffect(() => {
    if (formErrors.length === 0) {
      setFormValidation(true);
    } else {
      setFormValidation(false);
    }
  }, [formErrors]);

  const schema = schemas[schemaName];
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
            <Button onClick={handleSave} disabled={!validForm} loading={saving} variant="primary">
              Add
            </Button>
          </SpaceBetween>
        </Box>
      }
      header={title}
    >
      <SpaceBetween size="l">
        <AllAttributes
          schema={schema}
          schemaName={schemaName}
          schemas={schemas}
          userAccess={userAccess}
          item={localObject}
          handleUserInput={handleUserInput}
          hideAudit={true}
          handleUpdateValidationErrors={setFormErrors}
        />
      </SpaceBetween>
      {children}
    </Modal>
  );
};

export default AmendItemModal;
