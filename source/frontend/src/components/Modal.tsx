// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react'
import ReactDOM from 'react-dom'
import {
  Modal,
  Button,
  SpaceBetween,
  Box
} from '@awsui/components-react';

type Props = {
  children: React.ReactChild,
  closeModal: () => void,
  confirmAction: () => void
}

const MFModal = React.memo(({ children, closeModal , confirmAction, title, noCancel}: Props) => {
  const domEl = document.getElementById('modal-root')

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
                  {noCancel ? undefined : <Button onClick={closeModal} variant="link">Cancel</Button>}
                  <Button onClick={confirmAction} variant="primary">Ok</Button>
                </SpaceBetween>
              </Box>
          )
          :
          undefined
      }
      header={title}
    >
      {children}
    </Modal>,
    domEl
  )
});

export default MFModal;
