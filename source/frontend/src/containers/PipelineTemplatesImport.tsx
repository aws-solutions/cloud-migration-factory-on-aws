/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import { EntitySchema } from "../models/EntitySchema.ts";
import React, { useContext, useState } from "react";
import { Button, Container, Header, SpaceBetween } from "@cloudscape-design/components";
import ToolsApiClient from "../api_clients/toolsApiClient.ts";
import { useNavigate } from "react-router-dom";
import { NotificationContext } from "../contexts/NotificationContext.tsx";
import { FileContent, FileImportStep } from "../components/PipelineTemplateJsonFileImport.tsx";
import { apiActionErrorHandler, parsePUTResponseErrors } from "../resources/recordFunctions.ts";

export const PipelineTemplatesImport = (props: { schemas: Record<string, EntitySchema> }) => {
  const [committing, setCommitting] = useState(false);
  const navigate = useNavigate();
  const { addNotification } = useContext(NotificationContext);

  const [fileJSON, setFileJSON] = useState<FileContent | null>(null);

  const [activeStepIndex, setActiveStepIndex] = useState(0);

  async function submit() {
    setCommitting(true);
    const action = "Import";
    const schema = "Pipeline templates";
    const toolsApiClient = new ToolsApiClient();
    try {
      const response = await toolsApiClient.postPipelineTemplateImport(fileJSON);
      setCommitting(false);
      if (response["errors"]) {
        let errorsReturned = parsePUTResponseErrors(response["errors"]).join(",");
        addNotification({
          type: "error",
          dismissible: true,
          header: `${action} ${schema}`,
          content: errorsReturned,
        });
      } else {
        addNotification({
          type: "success",
          dismissible: true,
          header: `${action} ${schema}`,
          content: `${schema} imported successfully`,
        });
      }
      navigate({
        pathname: "/pipeline_templates",
      });
    } catch (e) {
      setCommitting(false);
      apiActionErrorHandler(action, schema, e, addNotification);
    }
  }

  return (
    <Container
      header={
        <Header
          variant="h1"
          description="Select a Cloud Migration Factory structured or formatted JSON, CSV (Lucid Diagram) or DrawIO file containing pipeline templates."
        >
          Select a file
        </Header>
      }
    >
      <SpaceBetween size="l">
        <FileImportStep setFileJSON={setFileJSON} acceptedFileTypes=".json, .csv, .drawio" />
      </SpaceBetween>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <SpaceBetween direction="horizontal" size="l">
          <Button onClick={() => navigate("/pipeline_templates")} variant="link">
            Cancel
          </Button>
          <Button onClick={submit} variant="primary" loading={committing} disabled={!fileJSON}>
            Submit
          </Button>
        </SpaceBetween>
      </div>
    </Container>
  );
};
