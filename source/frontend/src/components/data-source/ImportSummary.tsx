import React from "react";
import { Box, Container, Header, SpaceBetween, StatusIndicator, ColumnLayout } from "@cloudscape-design/components";
import { DataValidationResult } from "../data-validation";

export interface ImportSummaryProps {
  readonly validationResult: DataValidationResult;
}

enum ValidationStatus {
  SUCCESS = "success",
  WARNING = "warning",
  ERROR = "error",
  PENDING = "pending",
}

/**
 * Component for displaying import summary statistics including total entities and validation status.
 */
const ImportSummary: React.FC<ImportSummaryProps> = ({ validationResult }) => {
  // Calculate import summary statistics
  const importSummary = React.useMemo(() => {
    const totalEntities = validationResult.entities.reduce((sum, entity) => {
      return sum + Object.keys(entity.data || {}).length;
    }, 0);

    const totalErrors =
      (validationResult.issues.deduplicationErrors?.length ?? 0) +
      (validationResult.issues.requiredAttributeErrors?.length ?? 0) +
      (validationResult.issues.validationErrors?.length ?? 0) +
      (validationResult.issues.crossReferenceErrors?.length ?? 0);

    const totalWarnings =
      (validationResult.issues.deduplicationWarnings?.length ?? 0) +
      (validationResult.issues.validationWarnings?.length ?? 0);

    let status = ValidationStatus.SUCCESS;
    if (totalErrors > 0) {
      status = ValidationStatus.ERROR;
    } else if (totalWarnings > 0) {
      status = ValidationStatus.WARNING;
    }

    return {
      totalEntities,
      totalErrors,
      totalWarnings,
      status,
    };
  }, [validationResult]);

  return (
    <Container header={<Header variant="h2">Import summary</Header>}>
      <ColumnLayout columns={2} variant="text-grid">
        <SpaceBetween size="xxs">
          <Box variant="awsui-key-label">Total entities</Box>
          <Box variant="awsui-value-large">{importSummary.totalEntities}</Box>
        </SpaceBetween>
        <SpaceBetween size="xxs">
          <Box variant="awsui-key-label">Validation status</Box>
          <StatusIndicator type={importSummary.status}>
            {importSummary.status === ValidationStatus.SUCCESS
              ? "No errors detected"
              : importSummary.status === ValidationStatus.WARNING
                ? "Warnings Present"
                : importSummary.status === ValidationStatus.ERROR
                  ? "Errors Found"
                  : "Pending"}
          </StatusIndicator>
        </SpaceBetween>
      </ColumnLayout>
    </Container>
  );
};

export default ImportSummary;
