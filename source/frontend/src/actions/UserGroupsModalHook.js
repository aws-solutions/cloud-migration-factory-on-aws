/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';

import UserGroupsModal from "../components/UserGroupsModal";

export const useUserGroupsModal = () => {
  const [isVisible, setIsVisible] = useState(false)


  const show = () => setIsVisible(true);
  const hide = () => setIsVisible(false)

  const RenderModal = (props: { children: React.ReactChild }) => (
    <React.Fragment>
      {isVisible && <UserGroupsModal title={props.title} confirmAction={(modalSelections) => props.onConfirmation(modalSelections)} closeModal={hide} groups={props.groups} action={props.action}>{props.children}</UserGroupsModal>}
    </React.Fragment>
  )

  return {
    show,
    hide,
    RenderModal,
  }
};
