/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, {ReactNode} from 'react'
import {Box, Button, Modal, SpaceBetween} from '@awsui/components-react';

export type CMFModalProps = {
  header: ReactNode,
  visible: boolean,
  onDismiss: () => void,
  onConfirmation?: () => void,
  noCancel?: boolean
  children?: ReactNode,
}

// Wrapper for Modal component from @awsui/components-react to reduce duplication of defaults
export const CMFModal = ({children, onDismiss, visible, onConfirmation, header, noCancel}: CMFModalProps) => {
  if (!visible) return <></>; // if modal is not visible, don't render it. it makes unit testing harder when there are multiple invisible modals in the DOM.

  return (
    <Modal
      onDismiss={noCancel ? undefined : onDismiss}
      visible={true}
      closeAriaLabel="Close"
      size="medium"
      footer={onConfirmation ?
        (
          <Box float="right">
            <SpaceBetween direction="horizontal" size="xs">
              {noCancel ? undefined : <Button onClick={onDismiss} variant="link">Cancel</Button>}
              <Button onClick={onConfirmation} variant="primary">Ok</Button>
            </SpaceBetween>
          </Box>
        )
        :
        undefined
      }
      header={header}
    >
      {children}
    </Modal>
  );
};

