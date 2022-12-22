/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Flashbar } from '@awsui/components-react';

// Flash message content
const FlashMessage = (props) => {
  return <Flashbar items={props.notifications} />;
};

export default FlashMessage;
