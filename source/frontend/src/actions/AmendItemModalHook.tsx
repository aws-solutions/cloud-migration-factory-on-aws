// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import AmendItemModal from "../components/AmendItemModal";

export const useAmendItemModal = () => {
  const [isVisible, setIsVisible] = useState(false)


  const show = () => setIsVisible(true);
  const hide = () => setIsVisible(false)

  const RenderModal = (props: { children: React.ReactChild }) => (
    <React.Fragment>
      {isVisible && <AmendItemModal title={props.title} confirmAction={(modalSelections) => props.onConfirmation(modalSelections)} closeModal={hide} userAccess={props.userAccess} schemas={props.schemas} schemaName={props.schemaName} item={props.item ? props.item : {}} action={props.action}>{props.children}</AmendItemModal>}
    </React.Fragment>
  )

  return {
    show,
    hide,
    RenderModal,
  }
};
