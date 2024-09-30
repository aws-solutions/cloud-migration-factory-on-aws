/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import { API } from "@aws-amplify/api";

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
    return API.get(
      this.apiName,
      '/pipelines/templates',
      {
        queryStringParameters: {
            pipeline_template_id: template_ids
          }
      }
    );
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
}
