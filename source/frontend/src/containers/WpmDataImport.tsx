/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import { Box, ContentLayout, Header } from "@cloudscape-design/components";
import { useNavigate } from "react-router-dom";
import DataImportTable from "../components/data-source/DataImportTable";

const WpmDataImport = () => {
  const navigate = useNavigate();

  const handleAddJob = () => {
    // Navigate to upload form or open modal
    navigate("/wave-planning/data-import/add");
  };

  return (
    <ContentLayout
      header={
        <Box>
          <Header variant="h1" description="View upload jobs & import new data sets into the system">
            Data import
          </Header>
        </Box>
      }
    >
      <DataImportTable onAddJob={handleAddJob} />
    </ContentLayout>
  );
};

export default WpmDataImport;
