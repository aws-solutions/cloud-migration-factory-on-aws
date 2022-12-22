/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';

import SchemaAttributeAmendModal from '../components/SchemaAttributeAmendModal.jsx';

export const useSchemaModal = () => {
  const [isVisible, setIsVisible] = useState(false)

  const show = () => setIsVisible(true)
  const hide = () => setIsVisible(false)

  const RenderModal = (props: { children: React.ReactChild }) => (
    <React.Fragment>
      {isVisible && <SchemaAttributeAmendModal title={props.title} confirmAction={props.onConfirmation} closeModal={hide} attribute={props.attribute} action={props.action} schema={props.schema} activeSchema={props.activeSchema}>{props.children}</SchemaAttributeAmendModal>}
    </React.Fragment>
  )

  return {
    show,
    hide,
    RenderModal,
  }
};
