import React, { useState } from 'react';

import MFModal from '../components/Modal.jsx';

export const useModal = () => {
  const [isVisible, setIsVisible] = useState(false)

  const show = () => setIsVisible(true)
  const hide = () => setIsVisible(false)

  const RenderModal = (props: { children: React.ReactChild }) => (
    <React.Fragment>
      {isVisible && <MFModal title={props.title} noCancel={props.noCancel ? true : false} confirmAction={props.onConfirmation} closeModal={hide}>{props.children}</MFModal>}
    </React.Fragment>
  )

  return {
    show,
    hide,
    RenderModal,
  }
};
