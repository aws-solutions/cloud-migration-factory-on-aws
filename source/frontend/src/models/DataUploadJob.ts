/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  CrossReferenceError,
  DeduplicationError,
  RequiredAttributeError,
  ValidationError,
  ValidationIssues,
} from "../components/data-validation";

export interface DataUploadJob {
  readonly id: string;
  readonly status: "pending" | "complete" | "failed" | "in-progress" | "complete-with-warnings" | "superseded";
  readonly filename?: string;
  readonly uploaded_by: string;
  readonly file_size?: number;
  readonly total_entities: number;
  readonly data_source_id: string;
  readonly results_url?: string;
  _history: {
    createdBy: { userRef: string; email: string };
    createdTimestamp: string;
    lastModifiedBy?: { userRef: string; email: string };
    lastModifiedTimestamp?: string;
  };
}

export interface CreateUploadDataJobRequest {
  readonly updated_schemas: string[];
  readonly file_size: number;
  readonly total_entities: number;
  readonly filename: string;
  readonly data_source_id: string;
}

export interface CreateUploadDataJobResponse extends DataUploadJob {
  readonly presigned_url: string;
  readonly expiry: string;
  readonly s3_object_metadata: Record<string, string>;
}

export interface ListUploadDataJobsResponse {
  readonly items: DataUploadJob[];
  readonly next_token?: string;
}

export interface EntityApiResult {
  readonly entityName: string;
  readonly itemsSubmitted: number;
  readonly apiStatus: number;
  readonly success: boolean;
  readonly itemsCreated: number;
  readonly apiErrors: Record<string, unknown>;
}

export interface UploadJobSummary {
  readonly numberItemsCreated: number;
  readonly numberItemsFailedCreate: number;
  readonly numberItemsUpdated: number;
  readonly numberItemsFailedUpdate: number;
  readonly numberValidationIssues: number;
}

export interface DataUploadJobResult {
  readonly uploadId: string;
  readonly originalFile: string;
  readonly uploadedBy: string;
  readonly validationIssues: ValidationIssues;
  readonly createFailures: ProcessingFailures;
  readonly updateFailures: ProcessingFailures;
  readonly createdItems: ProcessingItems;
  readonly updatedItems: ProcessingItems;
  readonly summary: UploadJobSummary;
}

export interface FailureDetails {
  data: Record<string, unknown>;
  error_message: string;
}

export interface ProcessingFailures {
  [entityType: string]: Record<string, FailureDetails>;
}

export interface ProcessingItems {
  [entityType: string]: Array<Record<string, unknown>>;
}

export interface RawDataUploadJobResult {
  upload_id: string;
  original_file: string;
  uploaded_by: string;
  validation_issues?: {
    deduplicationErrors: DeduplicationError[];
    deduplicationWarnings: DeduplicationError[];
    validationErrors: ValidationError[];
    validationWarnings: ValidationError[];
    requiredAttributeErrors: RequiredAttributeError[];
    crossReferenceErrors: CrossReferenceError[];
  };
  create_failures: ProcessingFailures;
  update_failures: ProcessingFailures;
  created_items: ProcessingItems;
  updated_items: ProcessingItems;
}
