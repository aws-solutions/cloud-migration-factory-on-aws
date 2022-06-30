import React, { useState } from 'react';

import ProgressModal from '../components/ProgressModal.jsx';

export const useProgressModal = () => {
  const [isVisible, setIsVisible] = useState(false)
  const [lprogress, setLProgress] = useState({status: '', percentageComplete: 0})

  const show = () => setIsVisible(true)
  const hide = () => setIsVisible(false)
  const setProgress =(progress) => setLProgress(progress)

  const RenderModal = (props: { children: React.ReactChild }) => (
    <React.Fragment>
      {isVisible && <ProgressModal title={props.title} confirmAction={props.onConfirmation} closeModal={hide} message={lprogress.status} complete={lprogress.percentageComplete} description={props.description} label={props.label}>{props.children}</ProgressModal>}
    </React.Fragment>
  )

  return {
    show,
    hide,
    setProgress,
    RenderModal,
  }
};
