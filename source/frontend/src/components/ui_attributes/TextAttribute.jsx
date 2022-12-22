/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import {
Box,
Spinner
} from '@awsui/components-react';

// Attribute Display message content
const TextAttribute = ({label, children, loading, loadingText}) => {
  return <div>

            <Box margin={{ bottom: 'xxxs' }} color="text-label">
              {label}
            </Box>
            <div>{
              typeof children === 'string' || children instanceof String
              ?
                (loading && loading !== undefined)
                ?
                  (
                    <Spinner size="normal" />
                  )
                :
                  children
              :
                JSON.stringify(children)
             }
            </div>
          </div>;
};

export default TextAttribute;
