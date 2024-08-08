import { CancelableEventHandler, NonCancelableCustomEvent } from "@awsui/components-react/internal/events";
import {
  Alert,
  Button,
  ButtonDropdown,
  ButtonDropdownProps,
  Container,
  FormField,
  Header,
  Icon,
  Link,
  Select,
  SpaceBetween,
  Wizard,
} from "@awsui/components-react";
import React, { useContext } from "react";
import { ToolsContext } from "../../contexts/ToolsContext";
import IntakeFormTable from "../IntakeFormTable";
import ImportOverview from "./ImportOverview";
import { CompletionNotification } from "../../models/CompletionNotification";
import { ImportCompletion } from "./ImportCompletion";

type ImportIntakeWizardParams = {
  errors: number;
  committing: boolean;
  committed: boolean;
  cancelClick: (arg0: NonCancelableCustomEvent<{}>) => void;
  uploadClick: (arg0: NonCancelableCustomEvent<{}>) => void;
  errorMessage: string | null;
  exportClick: CancelableEventHandler<ButtonDropdownProps.ItemClickDetails> | undefined;
  uploadChange: React.ChangeEventHandler<HTMLInputElement> | undefined;
  selectedFile: { name: any; size: number };
  sheetNames: any[];
  selectedSheetName: any;
  sheetChange: (arg0: string | undefined) => void;
  warnings: number;
  informational: number;
  items: any;
  summary: { attributeMappings: any; hasUpdates: any };
  schema: any;
  dataAll: any;
  importProgressStatus: CompletionNotification;
  outputCommitErrors: any[];
};

const getSelectedFile = (props: ImportIntakeWizardParams) => {
  return props.selectedFile ? (
    <SpaceBetween size={"xxl"} direction={"vertical"}>
      <SpaceBetween size={"xxs"} direction={"vertical"}>
        <SpaceBetween size={"xxs"} direction={"horizontal"}>
          <Icon
            name={props.errorMessage ? "status-negative" : "status-positive"}
            size="normal"
            variant={props.errorMessage ? "error" : "success"}
          />
          <>Filename: {props.selectedFile.name}</>
        </SpaceBetween>
        <SpaceBetween size={"xxs"} direction={"horizontal"}>
          File size: {(props.selectedFile.size / 1024).toFixed(4)} KB
        </SpaceBetween>
      </SpaceBetween>
      {props.sheetNames.length > 0 ? (
        <SpaceBetween size={"xxs"} direction={"vertical"}>
          Select Excel sheet to import from.
          <Select
            selectedOption={{ label: props.selectedSheetName, value: props.selectedSheetName }}
            options={props.sheetNames.map((item) => {
              return { label: item, value: item };
            })}
            onChange={(e) => {
              props.sheetChange(e.detail.selectedOption.value);
            }}
          />
        </SpaceBetween>
      ) : null}
    </SpaceBetween>
  ) : null;
};
export const ImportIntakeWizard = (props: ImportIntakeWizardParams) => {
  const { setHelpPanelContent } = useContext(ToolsContext);

  const [activeStepIndex, setActiveStepIndex] = React.useState(0);

  const hiddenFileInput: any = React.createRef();

  const helpContent = {
    header: "Import",
    content_text:
      "From here you can import an intake form for to create or update records with the Waves, Applications and Servers.",
  };

  const importCompletion = (
    <ImportCompletion
      schema={props.schema}
      dataAll={props.dataAll}
      cancelClick={props.cancelClick}
      committing={props.committing}
      summary={props.summary}
      commitErrors={props.outputCommitErrors}
      committed={props.committed}
      importProgress={props.importProgressStatus}
      setActiveStepIndex={setActiveStepIndex}
    />
  );

  const getIntakeForm = () => {
    return (
      <FormField
        label={"Intake Form"}
        description={"Upload your intake form to load new data into Migration Factory."}
        errorText={props.errorMessage}
      >
        <SpaceBetween direction="vertical" size="xs">
          <input
            ref={hiddenFileInput}
            accept=".csv,.xlsx"
            type="file"
            name="file"
            onChange={props.uploadChange}
            style={{ display: "none" }}
          />
          <Button
            variant="primary"
            iconName="upload"
            onClick={() => {
              hiddenFileInput.current.click();
            }}
          >
            Select file
          </Button>
          {getSelectedFile(props)}
        </SpaceBetween>
      </FormField>
    );
  };

  const getSteps = () => {
    return [
      {
        title: "Select import file",
        info: (
          <Link variant="info" onFollow={() => setHelpPanelContent(helpContent, false)}>
            Info
          </Link>
        ),
        description: (
          <SpaceBetween size={"xl"} direction={"vertical"}>
            Intake forms should be in CSV/UTF8 or Excel/xlsx format.
          </SpaceBetween>
        ),
        content: (
          <SpaceBetween size={"xl"} direction={"vertical"}>
            <SpaceBetween size={"s"} direction={"horizontal"}>
              Download a template intake form.
              <ButtonDropdown
                items={[
                  {
                    id: "download_req",
                    text: "Template with only required attributes",
                    description: "Download template with required only.",
                  },
                  {
                    id: "download_all",
                    text: "Template with all attributes",
                    description: "Download template with all attributes.",
                  },
                ]}
                onItemClick={props.exportClick}
              >
                Actions
              </ButtonDropdown>
            </SpaceBetween>
            <Container header={<Header variant="h2">Select file to commit</Header>}>{getIntakeForm()}</Container>
          </SpaceBetween>
        ),
      },
      {
        title: "Review changes",
        content: (
          <Container header={<Header variant="h2">Pre-upload validation</Header>}>
            {props.selectedFile ? (
              <SpaceBetween direction="vertical" size="l">
                <Alert
                  visible={props.errors > 0}
                  dismissAriaLabel="Close alert"
                  type="error"
                  header={"Your intake form has " + props.errors + " validation errors."}
                >
                  Please see table below for details of the validation errors, you cannot import this file until
                  resolved.
                </Alert>
                <Alert
                  visible={props.warnings > 0}
                  dismissAriaLabel="Close alert"
                  type="info"
                  header={"Your intake form has " + props.warnings + " validation warnings."}
                >
                  Please see table below for details of the validation warnings, you can import this file with these
                  warnings.
                </Alert>
                <Alert
                  visible={props.informational > 0}
                  dismissAriaLabel="Close alert"
                  type="info"
                  header={"Your intake form has " + props.informational + " informational validation messages."}
                >
                  Please see table below for details of the validation messages.
                </Alert>

                <IntakeFormTable
                  items={props.items}
                  isLoading={false}
                  errorLoading={null}
                  schema={props.summary.attributeMappings ? props.summary.attributeMappings : []}
                />
              </SpaceBetween>
            ) : null}
          </Container>
        ),
      },
      {
        title: "Upload data",
        content: <ImportOverview items={props.summary} schemas={props.schema} dataAll={props.dataAll} />,
      },
    ];
  };

  const onNavigateHandler = (arg0: any) => {
    const detail = arg0.detail;
    switch (detail.requestedStepIndex) {
      case 0:
        setActiveStepIndex(detail.requestedStepIndex);
        break;
      case 1:
        if (!props.errorMessage) {
          setActiveStepIndex(detail.requestedStepIndex);
        }
        break;
      case 2:
        if (!(props.errorMessage || props.errors > 0)) {
          setActiveStepIndex(detail.requestedStepIndex);
        }
        break;
      default:
        break;
    }
  };

  return props.committing ? (
    importCompletion
  ) : (
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
        props.uploadClick(e);
      }}
      onNavigate={onNavigateHandler}
      activeStepIndex={activeStepIndex}
      steps={getSteps()}
    />
  );
};
