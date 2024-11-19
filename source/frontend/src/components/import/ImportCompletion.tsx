import React, {ReactNode} from "react";
import {EntitySchema} from "../../models/EntitySchema";
import {
  Alert,
  Button,
  Container,
  ExpandableSection,
  Form,
  Header,
  ProgressBar,
  SpaceBetween,
} from "@cloudscape-design/components";
import ImportOverview from "./ImportOverview";

type ImportCompletionParams = {
  cancelClick: (arg0: CustomEvent) => void;
  setActiveStepIndex: (arg0: number) => void;
  committed: any;
  committing: any;
  importProgress: {
    percentageComplete: number;
    status: ReactNode;
  };
  commitErrors: any[];
  summary: { hasUpdates: any };
  schema: EntitySchema;
  dataAll: any;
};
export const ImportCompletion = (props: ImportCompletionParams) => {
  return (
    <Form
      header={<Header variant="h1">{" Intake form upload status."}</Header>}
      actions={
        // located at the bottom of the form
        <SpaceBetween direction="horizontal" size="xs">
          <Button
            onClick={(e) => {
              props.cancelClick(e);
              props.setActiveStepIndex(0);
            }}
            disabled={!props.committed}
            variant="primary"
          >
            New Upload
          </Button>
        </SpaceBetween>
      }
      errorText={null}
    >
      <Container header={<Header variant="h2">Intake form upload status.</Header>}>
        <SpaceBetween direction="vertical" size="l">
          {!props.committed ? (
            <SpaceBetween size={"xxs"}>
              <Alert
                visible={!props.committed && props.committing}
                dismissAriaLabel="Close alert"
                header="Uploading..."
              >
                Intake data is being uploaded. If you navigate away from this page then errors will not be visible until
                the import job has completed, and will be displayed in the notification bar. It is recommended that you
                do not make changes to the data records that are included in the intake upload until it has completed.
              </Alert>
              <ProgressBar
                status={props.importProgress.percentageComplete >= 100 ? "success" : "in-progress"}
                value={props.importProgress.percentageComplete}
                additionalInfo={props.importProgress.status}
                label={"Upload progress"}
              />
            </SpaceBetween>
          ) : null}
          <Alert
            visible={props.commitErrors.length > 0}
            dismissAriaLabel="Close alert"
            type="error"
            header={"Errors returned during upload of " + props.commitErrors.length + " records."}
          >
            {props.commitErrors.map((errorItem) => (
              <ExpandableSection
                key={errorItem.itemType + " - " + errorItem.error}
                header={errorItem.itemType + " - " + errorItem.error}
              >
                {JSON.stringify(errorItem.item)}
              </ExpandableSection>
            ))}
          </Alert>
          <Alert
            visible={!props.summary.hasUpdates}
            dismissAriaLabel="Close alert"
            type="success"
            header={
              "Nothing to upload! The contents of the selected import file match the data currently in Migration Factory."
            }
          >
            If this is not what you expected please check you loaded the correct file.
          </Alert>
          <Alert
            visible={props.commitErrors.length === 0 && props.committed}
            dismissAriaLabel="Close alert"
            type="success"
            header={"Intake file upload completed successfully."}
          ></Alert>
          <ExpandableSection header={"Record Overview"}>
            <ImportOverview items={props.summary} schemas={props.schema} dataAll={props.dataAll} />
          </ExpandableSection>
        </SpaceBetween>
      </Container>
    </Form>
  );
};
