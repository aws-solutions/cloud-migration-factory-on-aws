/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import { API } from "@aws-amplify/api";

export default class UserApiClient {
  public readonly apiName = "user";

  getNotifications() {
    return API.get(this.apiName, "/user/notifications", {});
  }

  getApps() {
    return API.get(this.apiName, "/user/app", {});
  }

  getWaves() {
    return API.get(this.apiName, "/user/wave", {});
  }

  getServers() {
    return API.get(this.apiName, "/user/server", {});
  }

  getAppServers(appId: string) {
    return API.get(this.apiName, "/user/server/appid/" + appId, {});
  }

  getDatabases() {
    return API.get(this.apiName, "/user/database", {});
  }

  getPipelines() {
    return API.get(this.apiName, "/user/pipeline", {});
  }

  getPipelineTemplates() {
    return API.get(this.apiName, "/user/pipeline_template", {});
  }

  getPipelineTemplate(template_id: string) {
    return API.get(this.apiName, "/user/pipeline_template/" + template_id, {});
  }

  getPipelineTemplateTasks() {
    return API.get(this.apiName, "/user/pipeline_template_task", {});
  }

  getTasks() {
    return API.get(this.apiName, "/user/task", {});
  }

  getTaskExecutions() {
    return API.get(this.apiName, "/user/task_execution", {});
  }

  getAppDatabases(app_id: string) {
    return API.get(this.apiName, "/user/database/appid/" + app_id, {});
  }

  deleteDatabase(database_id: string) {
    return API.del(this.apiName, "/user/database/" + database_id, {});
  }

  deleteApp(app_id: string) {
    return API.del(this.apiName, "/user/app/" + app_id, {});
  }

  deleteServer(server_id: string) {
    return API.del(this.apiName, "/user/server/" + server_id, {});
  }

  deletePipeline(pipeline_id: string) {
    return API.del(this.apiName, "/user/pipeline/" + pipeline_id, {});
  }

  deletePipelineTemplate(pipeline_template_id: string) {
    return API.del(this.apiName, "/user/pipeline_template/" + pipeline_template_id, {});
  }

  deletePipelineTemplateTask(pipeline_template_task_id: string) {
    return API.del(this.apiName, "/user/pipeline_template_task/" + pipeline_template_task_id, {});
  }

  postItem(item: any, schema: string) {
    let lSchema = schema;
    if (lSchema === "application") {
      lSchema = "app";
    }
    return API.post(this.apiName, "/user/" + lSchema + "/", { body: item });
  }

  postItems(items: any[], schema: string) {
    let lSchema = schema;
    if (lSchema === "application") {
      lSchema = "app";
    }
    return API.post(this.apiName, "/user/" + lSchema + "/", { body: items });
  }

  putItem(item_id: string, update: any, schema: string) {
    let lSchema = schema;
    if (lSchema === "application") {
      lSchema = "app";
    }
    return API.put("user", "/user/" + lSchema + "/" + item_id, { body: update });
  }

  deleteItem(server_id: string, schema: string) {
    let lSchema = schema;
    if (lSchema === "application") {
      lSchema = "app";
    }
    return API.del(this.apiName, "/user/" + lSchema + "/" + server_id, {});
  }
}
