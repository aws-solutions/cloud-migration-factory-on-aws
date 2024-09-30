// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from "react";

import {
  Button,
  Checkbox,
  Container,
  FormField,
  Grid,
  Header,
  Icon,
  Input,
  Link,
  SpaceBetween,
  Wizard,
} from "@cloudscape-design/components";

const AutomationScriptImport = (props) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [errorFile, setErrorFile] = useState(null);

  const [saving, setSaving] = useState(false);

  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [scriptDetails, setScriptDetails] = useState(props.item ? props.item : {});

  const hiddenFileInput = React.createRef();

  const maxFileUploadSizeBytes = 10485760;

  function handleAction(e) {
    setSaving(true);
    props.handleUpload(selectedFile, scriptDetails);
  }

  function handleUserInput(key, update) {
    let tempUpdate = Object.assign({}, scriptDetails);
    tempUpdate[key] = update;
    setScriptDetails(tempUpdate);
  }

  function getImportedFileStatusMessage(selectedFile, errorFile) {
    if (selectedFile && errorFile) {
      return errorFile;
    } else if (!selectedFile) {
      return "No file selected";
    } else {
      return null;
    }
  }

  async function handleUploadChange(e) {
    e.preventDefault();

    setSelectedFile(null);

    setSelectedFile(e.target.files[0]);
  }

  useEffect(() => {
    setErrorFile(null);

    if (selectedFile) {
      if (selectedFile.size > maxFileUploadSizeBytes) {
        setErrorFile("Upload size is restricted to " + maxFileUploadSizeBytes / 1048576 + " MBytes");
      }
    }
  }, [selectedFile]);

  return (
    <Wizard
      i18nStrings={{
        stepNumberLabel: (stepNumber) => `Step ${stepNumber}`,
        collapsedStepsLabel: (stepNumber, stepsCount) => `Step ${stepNumber} of ${stepsCount}`,
        cancelButton: "Cancel",
        previousButton: "Previous",
        nextButton: "Next",
        submitButton: "Upload",
        optional: "optional",
      }}
      onCancel={(e) => {
        props.cancelClick(e);
        setActiveStepIndex(0);
      }}
      onSubmit={(e) => {
        if (selectedFile && !errorFile) {
          handleAction(e);
        }
      }}
      onNavigate={({ detail }) => {
        //onClick={props.uploadClick} disabled={(props.errors > 0 || !props.selectedFile || props.committed)}

        switch (detail.requestedStepIndex) {
          case 0:
          case 1:
            if (!(selectedFile && errorFile)) {
              setActiveStepIndex(detail.requestedStepIndex);
            }
            break;
          case 2:
            if (!(selectedFile && !errorFile)) {
              setActiveStepIndex(detail.requestedStepIndex);
            }
            break;
          default:
            break;
        }
      }}
      activeStepIndex={activeStepIndex}
      isLoadingNextStep={selectedFile && !errorFile && !saving ? false : true}
      steps={[
        {
          title: "Select script package zip file",
          info: <Link variant="Info">Info</Link>,
          description: "Package should contain the package.yaml and script file and dependencies.",
          content: (
            <Container header={<Header variant="h2">Select script to package</Header>}>
              <FormField
                label={"Script package"}
                description={"Upload your script package."}
                errorText={getImportedFileStatusMessage(selectedFile, errorFile)}
              >
                <SpaceBetween direction="vertical" size="xs">
                  <input
                    ref={hiddenFileInput}
                    accept=".zip"
                    type="file"
                    name="file"
                    onChange={handleUploadChange}
                    style={{ display: "none" }}
                  />
                  <Button
                    iconName="upload"
                    onClick={() => {
                      hiddenFileInput.current.click();
                    }}
                  >
                    Select file
                  </Button>
                  {selectedFile && !errorFile ? (
                    <Grid gridDefinition={[{ colspan: 0.5 }, { colspan: 6 }]}>
                      <div>
                        <Icon name={"status-positive"} size="normal" variant="success" />
                      </div>
                      <div>
                        <h4>Filename: {selectedFile.name}</h4>
                        <h5>File size: {(selectedFile.size / 1024).toFixed(4)} KB</h5>
                      </div>
                    </Grid>
                  ) : null}
                </SpaceBetween>
              </FormField>
            </Container>
          ),
        },
        {
          title: "Enter Script Details",
          info: <Link variant="Info">Info</Link>,
          description: "Enter the details that this script will be referenced by.",
          content: (
            <Container header={<Header variant="h2">Select script to package</Header>}>
              <SpaceBetween direction={"vertical"} size={"xxl"}>
                <FormField
                  label={"Script Name"}
                  description={"Name of script used by user to select this script in the interface."}
                  errorText={
                    scriptDetails.script_name === "" ? "You must provide a name for the script to upload." : undefined
                  }
                >
                  <Input
                    value={scriptDetails.script_name}
                    onChange={(event) => handleUserInput("script_name", event.detail.value)}
                  />
                </FormField>
                {props.action === "Update" ? (
                  <Checkbox
                    checked={scriptDetails.__make_default}
                    onChange={(event) => handleUserInput("__make_default", event.detail.checked)}
                  >
                    Make default version.
                  </Checkbox>
                ) : undefined}
              </SpaceBetween>
            </Container>
          ),
        },
      ]}
    />
  );
};

export default AutomationScriptImport;
