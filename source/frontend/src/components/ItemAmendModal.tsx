/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import {
  Modal,
} from "@cloudscape-design/components";
import { EntitySchema } from "../models/EntitySchema";
import ItemAmend from "./ItemAmend.tsx";

type Props = {
  title?: string;
  action: string;
  visible: boolean;
  userAccess: any;
  schemas: Record<string, EntitySchema>;
  activeSchemaName: string;
  closeModal: () => void;
  item: any;
  onConfirmation: (item: { name: string }, action: string) => Promise<void>;
};

const ItemAmendModal = ({
  item,
  closeModal,
  onConfirmation,
  title,
  action,
  schemas,
  activeSchemaName,
  userAccess,
  visible,
}: Props) => {

  return (
    <Modal
      onDismiss={closeModal}
      visible={visible}
      closeAriaLabel="Close"
      size="medium"
      header={title}
    >
      <ItemAmend
        action={action}
        item={item}
        handleSave={onConfirmation}
        handleCancel={closeModal}
        schemaName={activeSchemaName}
        schemas={schemas}
        userAccess={userAccess}
      />
    </Modal>
  );
};

export default ItemAmendModal;
