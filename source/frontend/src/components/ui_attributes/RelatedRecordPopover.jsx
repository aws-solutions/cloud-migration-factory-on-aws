/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
    Popover,
    SpaceBetween
} from '@awsui/components-react';
import AllViewerAttributes from "./AllViewerAttributes";
import Audit from "./Audit";

// Attribute Display message content
const RelatedRecordPopover = ({item, children, loading, loadingText, schema, schemas, dataAll}) => {
  return <Popover
      dismissAriaLabel="Close"
      fixedWidth
      header="Item detail"
      size="large"
      triggerType="text"
      content={
              <SpaceBetween size="l">
                  <AllViewerAttributes
                      schema={schema}
                      schemas={schemas}
                      item={item}
                      dataAll={dataAll}
                  />
                  <Audit item={item} expanded={true}/>
              </SpaceBetween>
      }
    >
  {children}
  </Popover>;
};

export default RelatedRecordPopover;
