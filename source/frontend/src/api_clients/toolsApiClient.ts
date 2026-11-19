/* eslint-disable */
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import { API } from "@aws-amplify/api";
import {
  EntitySchema,
  HeaderData,
  ManageEntitiesPayload,
  MoveEntitiesPayload,
  OperationType,
  HeaderMappingResponse,
  WPMRuleGenerationType,
  WPMGroupingRule,
  WPMPrioritizingRule,
  CreateUploadDataJobRequest,
  CreateUploadDataJobResponse,
  ListUploadDataJobsResponse,
  DataUploadJob,
  DataUploadJobResult,
  RawDataUploadJobResult,
  CLEANUP_MAX_ENTITY_SIZE,
} from "../models";
import { EntityType } from "../utils/Constants";

export default class ToolsApiClient {
  private readonly apiName = "tools";

  postTool(apiPath: string, data: any) {
    return API.post(this.apiName, apiPath, { body: data });
  }

  postPipelineTemplateImport(data: any) {
    return this.postTool("/pipelines/templates", data);
  }

  getPipelineTemplatesExport() {
    return this.getTool("/pipelines/templates");
  }

  getPipelineTemplateExport(template_ids: string[]) {
    return API.get(this.apiName, "/pipelines/templates", {
      queryStringParameters: {
        pipeline_template_id: template_ids,
      },
    });
  }

  getTool(apiPath: string) {
    return API.get(this.apiName, apiPath, {});
  }

  getSSMJobs(maximumDays: number | undefined = undefined) {
    let daysToReturn = "";
    if (maximumDays !== undefined) {
      daysToReturn = "?maximumdays=" + maximumDays;
    }
    return API.get(this.apiName, "/ssm/jobs" + daysToReturn, {});
  }

  getSSMScripts() {
    return API.get(this.apiName, "/ssm/scripts", {});
  }

  getSSMScript(package_uuid: string, version: string, download = false) {
    if (download) {
      return API.get(this.apiName, "/ssm/scripts/" + package_uuid + "/" + version + "/download", {});
    } else {
      return API.get(this.apiName, "/ssm/scripts/" + package_uuid + "/" + version, {});
    }
  }

  postSSMScripts(data: any) {
    return API.post(this.apiName, "/ssm/scripts", { body: data });
  }

  putSSMScripts(data: any) {
    return API.put(this.apiName, "/ssm/scripts/" + data.package_uuid, { body: data });
  }

  getCredentials() {
    return API.get(this.apiName, "/credentialmanager", {});
  }

  /**
   * Recalculate the complexity & ranks of all the applications in CMF
   * @returns Promise that resolves to the API call result or rejects with the error
   */
  calculateAppRanks() {
    return API.post(this.apiName, "/wpm/calculate-app-ranks", {
      body: {},
    });
  }

  /**
   * Auto create WPM waves based on move groups
   * @param wpm_job_id WPM Job Id
   * @param move_group_ids Move group Ids
   * @returns Promise that resolves to the API call result or rejects with the error
   */
  createWPMWaves(wpm_job_id: string, move_group_ids: string[]) {
    return API.post(this.apiName, "/wpm/create-waves", {
      body: {
        wpm_job_id,
        move_group_ids,
      },
    });
  }

  /**
   * Manage entities in WPM
   * @param payload Entity management payload
   * @returns Promise that resolves to the API call result or rejects with the error
   */
  manageEntities(payload: ManageEntitiesPayload) {
    return API.post(this.apiName, "/manage-entities", {
      body: payload,
    });
  }

  /**
   * Cleanup entities in WPM
   * @param entity_type Entity type
   * @param entity_ids Entity Ids
   * @returns Promise that resolves to the API call result or rejects with the error
   */
  async cleanupEntities(entity_type: EntityType, entity_ids: string[]) {
    const batches: string[][] = [];

    // Split entity_ids into batches of CLEANUP_MAX_ENTITY_SIZE
    for (let i = 0; i < entity_ids.length; i += CLEANUP_MAX_ENTITY_SIZE) {
      batches.push(entity_ids.slice(i, i + CLEANUP_MAX_ENTITY_SIZE));
    }

    // Process each batch sequentially as manage-entities API does not really support parallel
    for (const batch of batches) {
      await this.manageEntities({
        operation: OperationType.CLEANUP,
        entity_type,
        entity_ids: batch,
      });
    }
  }

  /**
   * Maps headers to entity schema attributes for data import operations
   * @param headers Array of header data to be mapped
   * @param schemas Record of entity schemas keyed by schema name to map headers against
   * @returns Promise that resolves to header mapping response or rejects with error
   */
  getHeaders(headers: HeaderData[], schemas: Record<string, Partial<EntitySchema>>): Promise<HeaderMappingResponse> {
    return API.post(this.apiName, "/header-map", {
      body: {
        headers,
        schemas,
      },
    });
  }

  /**
   * Generates a rule based on user input using AI/ML capabilities
   * @param ruleGenerationType The type of the rule to be generated
   * @param userInput User's natural language input describing the desired rule
   * @returns Promise that resolves to the generated rule or rejects with error
   */
  generateRule(
    ruleGenerationType: WPMRuleGenerationType,
    userInput: string
  ): Promise<WPMGroupingRule | WPMPrioritizingRule> {
    return API.post(this.apiName, "/generate-rule", {
      body: {
        rule_type: ruleGenerationType,
        user_input: userInput,
      },
    });
  }

  /**
   * Create a new job for uploading data entities
   * @param body Data object to be sent in the request body
   * @returns Promise that resolves to presigned URL response or rejects with error
   */
  createUploadDataJob(body: CreateUploadDataJobRequest): Promise<CreateUploadDataJobResponse> {
    return API.post(this.apiName, "/wpm/upload-data-entities", {
      body,
    });
  }

  /**
   * Get upload status for data entities
   * @param uploadId The upload ID to check status for
   * @returns Promise that resolves to upload status or rejects with error
   */
  getUploadDataJob(uploadId: string): Promise<DataUploadJob> {
    return API.get(this.apiName, `/wpm/upload-data-entities/${uploadId}`, {});
  }

  /**
   * List uploads in the system
   * @param limit Maximum number of uploads to return (default: 50, max: 100)
   * @param nextToken Optional pagination token for retrieving next page
   * @returns Promise that resolves to list of uploads or rejects with error
   */
  listUploadDataJobs(limit: number = 50, nextToken?: string): Promise<ListUploadDataJobsResponse> {
    const queryParams: Record<string, any> = { limit };
    if (nextToken) {
      queryParams.next_token = nextToken;
    }

    return API.get(this.apiName, "/wpm/upload-data-entities", {
      queryStringParameters: queryParams,
    });
  }

  /**
   * List all uploads in the system by paginating through all pages
   * @returns Promise that resolves to array of all upload jobs or rejects with error
   */
  async listAllUploadDataJobs(): Promise<DataUploadJob[]> {
    const allJobs: DataUploadJob[] = [];
    let nextToken: string | undefined;

    do {
      const response = await this.listUploadDataJobs(100, nextToken);
      allJobs.push(...response.items);
      nextToken = response.next_token;
    } while (nextToken);

    return allJobs;
  }

  /**
   * Upload JSON data to a presigned URL
   * @param presignedUrl The presigned URL to upload to
   * @param jsonData The JSON data to upload
   * @param metadata Optional metadata to include as S3 object metadata
   * @returns Promise that resolves to upload result or rejects with error
   */
  async uploadJsonToPresignedUrl(presignedUrl: string, jsonData: unknown, metadata?: Record<string, string>) {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // Add metadata as S3 headers (x-amz-meta-*)
    if (metadata) {
      Object.entries(metadata).forEach(([key, value]) => {
        // S3 metadata keys must be lowercase and contain only letters, numbers, and hyphens
        const safeKey = key.toLowerCase().replace(/[^a-z0-9-]/g, "-");
        headers[`x-amz-meta-${safeKey}`] = String(value);
      });
    }

    const response = await fetch(presignedUrl, {
      method: "PUT",
      headers,
      body: JSON.stringify(jsonData),
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
    }

    return {
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
    };
  }

  /**
   * Fetch JSON data from a presigned URL
   * @template T The expected type of the JSON response
   * @param presignedUrl The presigned URL to fetch from
   * @param timeoutMs Optional timeout in milliseconds (default: 30000)
   * @returns Promise that resolves to the typed JSON data or rejects with error
   */
  async getJsonFromPresignedUrl<T = unknown>(presignedUrl: string, timeoutMs: number = 30000): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(presignedUrl, {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Failed to fetch data: ${response.status} ${response.statusText}`);
      }

      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new Error(`Expected JSON content, but received: ${contentType}`);
      }

      try {
        return await response.json();
      } catch (error) {
        throw new Error(`Failed to parse JSON response: ${error instanceof Error ? error.message : "Unknown error"}`);
      }
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Request timed out after ${timeoutMs}ms`);
      }
      throw error;
    }
  }

  /**
   * Get detailed results for a data upload job from a presigned URL
   * @param presignedUrl The presigned URL to fetch the job results from
   * @returns Promise that resolves to the detailed upload job results or rejects with error
   */
  async getDataUploadJobResults(presignedUrl: string): Promise<DataUploadJobResult> {
    const rawData = await this.getJsonFromPresignedUrl<RawDataUploadJobResult>(presignedUrl);

    // Validate required fields
    if (!rawData || typeof rawData !== "object") {
      throw new Error("Invalid response data: expected object");
    }

    // Calculate summary from processing results
    const numberItemsCreated = Object.values(rawData.created_items).reduce((sum, items) => sum + items.length, 0);
    const numberItemsUpdated = Object.values(rawData.updated_items).reduce((sum, items) => sum + items.length, 0);
    const numberItemsFailedCreate = Object.values(rawData.create_failures).reduce(
      (sum, failures) => sum + Object.keys(failures).length,
      0
    );
    const numberItemsFailedUpdate = Object.values(rawData.update_failures).reduce(
      (sum, failures) => sum + Object.keys(failures).length,
      0
    );

    const validationIssues = rawData.validation_issues;
    const numberValidationIssues = validationIssues
      ? validationIssues.deduplicationErrors.length +
      validationIssues.deduplicationWarnings.length +
      validationIssues.validationErrors.length +
      validationIssues.validationWarnings.length +
      validationIssues.requiredAttributeErrors.length +
      validationIssues.crossReferenceErrors.length
      : 0;

    return {
      uploadId: rawData.upload_id,
      originalFile: rawData.original_file,
      uploadedBy: rawData.uploaded_by,
      validationIssues: {
        deduplicationErrors: validationIssues?.deduplicationErrors ?? [],
        deduplicationWarnings: validationIssues?.deduplicationWarnings ?? [],
        validationErrors: validationIssues?.validationErrors ?? [],
        validationWarnings: validationIssues?.validationWarnings ?? [],
        requiredAttributeErrors: validationIssues?.requiredAttributeErrors ?? [],
        crossReferenceErrors: validationIssues?.crossReferenceErrors ?? [],
      },
      createdItems: rawData.created_items,
      createFailures: rawData.create_failures,
      updatedItems: rawData.updated_items,
      updateFailures: rawData.update_failures,
      summary: {
        numberItemsCreated,
        numberItemsFailedCreate,
        numberItemsUpdated,
        numberItemsFailedUpdate,
        numberValidationIssues,
      },
    };
  }
}
