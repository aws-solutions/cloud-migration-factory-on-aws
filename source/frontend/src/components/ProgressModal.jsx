/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import ReactDOM from 'react-dom'
import {
  Modal,
  Button,
  SpaceBetween,
  Box,
  ProgressBar
} from '@awsui/components-react';

type Props = {
  children: React.ReactChild,
  closeModal: () => void,
  confirmAction: () => void
};

const ProgressModal = React.memo(({ children, closeModal , confirmAction, title, message, complete, description, label}: Props) => {
  const domEl = document.getElementById('modal-root')

  if (!domEl) return null

  return ReactDOM.createPortal(
    <Modal
      onDismiss={confirmAction ? closeModal : undefined}
      visible={true}
      closeAriaLabel="Hide"
      size="medium"
      footer={confirmAction ?
            (
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Button onClick={closeModal} variant="link">Hide</Button>
                </SpaceBetween>
              </Box>
          )
          :
          undefined
      }
      header={title}
    >
      <SpaceBetween size="l">
        <ProgressBar
          status={complete === 100 ? "success" : "in-progress"}
          value={complete}
          additionalInfo={message}
          description={description}
          label={label}
        />
      </SpaceBetween>
      {children}
    </Modal>,
    domEl
  )
});

export default ProgressModal;
