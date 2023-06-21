/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
  SpaceBetween,
  ExpandableSection
 } from '@awsui/components-react';


const ImportChangeSummary = (props) => {

  return <SpaceBetween size="l">
      <ExpandableSection header={"Waves [Create " + props.items.wave.Create.length + " - Update " + props.items.wave.Update.length  + " - No Change " + props.items.wave.NoChange.length + "]"}>
      </ExpandableSection>
      <ExpandableSection header={"Applications [Create " + props.items.application.Create.length + " - Update " + props.items.application.Update.length  + " - No Change " + props.items.application.NoChange.length + "]"}>
      </ExpandableSection>
      <ExpandableSection header={"Servers [Create " + props.items.server.Create.length + " - Update " + props.items.server.Update.length  + " - No Change " + props.items.server.NoChange.length + "]"}>
      </ExpandableSection>
    </SpaceBetween>
};

export default ImportChangeSummary;
