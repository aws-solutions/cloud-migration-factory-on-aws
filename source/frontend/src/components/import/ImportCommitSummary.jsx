/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  ExpandableSection
 } from '@awsui/components-react';


const ImportCommitSummary = (props) => {

  //{itemType: 'Server', error: newItem.server_name ? newItem.server_name + " - " + e.message : e.message, item: newItem})
  function formatErrors(){

    let allErrors = [];

    allErrors = props.items.map((errorItem, indx) => {
      return <ExpandableSection key={errorItem.itemType + " - " + errorItem.error} header={errorItem.itemType + " - " + errorItem.error}>{".   Data sent: " + errorItem.newItem}</ExpandableSection>
    });

    return allErrors;
  }

  return formatErrors;
};

export default ImportCommitSummary;
