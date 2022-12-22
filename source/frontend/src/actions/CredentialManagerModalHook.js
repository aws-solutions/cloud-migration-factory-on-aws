/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';

import CredentialManagerModal from '../components/CredentialManagerModal';

export const useCredentialManagerModal = () => {
  const [isVisible, setIsVisible] = useState(false)

  const show = () => setIsVisible(true)
  const hide = () => setIsVisible(false)

  const RenderModal = (props: { children: React.ReactChild }) => (
    <React.Fragment>
      {isVisible && <CredentialManagerModal title={props.title} confirmAction={props.onConfirmation} closeModal={hide} attribute={props.attribute} action={props.action}>{props.children}</CredentialManagerModal>}
    </React.Fragment>
  )

  return {
    show,
    hide,
    RenderModal,
  }
};
