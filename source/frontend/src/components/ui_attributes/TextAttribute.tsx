/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { Box, Spinner } from "@cloudscape-design/components";

interface TestAttributeParams {
  label: string;
  children: React.ReactNode;
  loading?: boolean;
}

// Attribute Display message content
const TextAttribute = ({ label, children, loading }: TestAttributeParams) => {
  function getBodyContent() {
    if (typeof children === "string" || children instanceof String) {
      if (loading) {
        return <Spinner size="normal" />;
      } else {
        return children;
      }
    } else {
      return JSON.stringify(children);
    }
  }

  return (
    <div>
      <Box margin={{ bottom: "xxxs" }} color="text-label">
        {label}
      </Box>
      <div>{getBodyContent()}</div>
    </div>
  );
};

export default TextAttribute;
