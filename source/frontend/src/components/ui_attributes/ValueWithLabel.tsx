import { Box } from "@cloudscape-design/components";
import React, { ReactNode } from "react";

export const ValueWithLabel = ({ label, children }: { label: string; children: ReactNode }) => (
  <div>
    <Box margin={{ bottom: "xxxs" }} color="text-label">
      {label}
    </Box>
    <div>{children}</div>
  </div>
);
