/* eslint-disable @typescript-eslint/no-explicit-any */
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import { API } from "@aws-amplify/api";
import { DataSourceEntityResponse, DataSourceEntityUpdateResponse, RuleEntityResponse } from "./userApiClientModels";
import { DataSource } from "../models/DataSource";
import { Schemas } from "../utils/Constants";
import { WPMRuleData } from "../models";

// Define more specific types for better type safety
export type EntityId = string;
export type SchemaType = string;

export interface Entity {
  [key: string]: any;
}

export interface ApiResponse<T> {
  data: T;
  statusCode: number;
}

/**
 * Client for interacting with the User API
 *
 * This class provides methods for interacting with various resources in the Migration Factory
 * including apps, servers, databases, waves, pipelines, and tasks.
 */
export default class UserApiClient {
  public readonly apiName = "user";
  private cache = new Map<string, { data: any; timestamp: number }>();
  private readonly CACHE_TTL = 60000; // 1 minute cache TTL
  private readonly DEFAULT_OPTIONS = {};

  // ===== ORIGINAL METHODS (PRESERVED FOR BACKWARD COMPATIBILITY) =====

  /**
   * Get user notifications
   */
  getNotifications() {
    return this.apiGet("/user/notifications");
  }

  /**
   * Get all applications
   */
  getApps() {
    return this.apiGet("/user/app");
  }

  /**
   * Get all waves
   */
  getWaves() {
    return this.apiGet("/user/wave");
  }

  /**
   * Get all servers
   */
  getServers() {
    return this.apiGet("/user/server");
  }

  /**
   * Get all databases
   */
  getDatabases() {
    return this.apiGet("/user/database");
  }

  /**
   * Get all pipelines
   */
  getPipelines() {
    return this.apiGet("/user/pipeline");
  }

  /**
   * Get all pipeline templates
   */
  getPipelineTemplates() {
    return this.apiGet("/user/pipeline_template");
  }

  /**
   * Get a specific pipeline template
   * @param template_id - Pipeline template ID
   */
  getPipelineTemplate(template_id: EntityId) {
    return this.apiGet(`/user/pipeline_template/${template_id}`);
  }

  /**
   * Get all pipeline template tasks
   */
  getPipelineTemplateTasks() {
    return this.apiGet("/user/pipeline_template_task");
  }

  /**
   * Get all tasks
   */
  getTasks() {
    return this.apiGet("/user/task");
  }

  /**
   * Get all task executions
   */
  getTaskExecutions() {
    return this.apiGet("/user/task_execution");
  }

  /**
   * Delete a database
   * @param database_id - Database ID
   */
  deleteDatabase(database_id: EntityId) {
    return this.apiDelete(`/user/database/${database_id}`);
  }

  /**
   * Delete an application
   * @param app_id - Application ID
   */
  deleteApp(app_id: EntityId) {
    return this.apiDelete(`/user/app/${app_id}`);
  }

  /**
   * Delete a server
   * @param server_id - Server ID
   */
  deleteServer(server_id: EntityId) {
    return this.apiDelete(`/user/server/${server_id}`);
  }

  /**
   * Delete a pipeline
   * @param pipeline_id - Pipeline ID
   */
  deletePipeline(pipeline_id: EntityId) {
    return this.apiDelete(`/user/pipeline/${pipeline_id}`);
  }

  /**
   * Delete a pipeline template
   * @param pipeline_template_id - Pipeline template ID
   */
  deletePipelineTemplate(pipeline_template_id: EntityId) {
    return this.apiDelete(`/user/pipeline_template/${pipeline_template_id}`);
  }

  /**
   * Delete a pipeline template task
   * @param pipeline_template_task_id - Pipeline template task ID
   */
  deletePipelineTemplateTask(pipeline_template_task_id: EntityId) {
    return this.apiDelete(`/user/pipeline_template_task/${pipeline_template_task_id}`);
  }

  createDataSource(dataSource: DataSource): Promise<DataSourceEntityResponse> {
    return this.postItem(dataSource, Schemas.DataSource.name);
  }

  createRule(rule: WPMRuleData): Promise<RuleEntityResponse> {
    return this.postItem(rule, Schemas.WPMRule.name);
  }

  updateDataSource(dataSource: DataSource): Promise<DataSourceEntityUpdateResponse> {
    if (!dataSource.data_source_id) {
      throw new Error("Missing data_source_id");
    }
    // if the data_source_id is part of the payload the request fails.
    const { data_source_id, ...itemWithoutId } = dataSource;
    return this.putItem(data_source_id, itemWithoutId, Schemas.DataSource.name);
  }

  deleteDataSources(dataSources: DataSource[]) {
    const dataSourceIds = dataSources.map((dataSource) => {
      if (!dataSource.data_source_id) {
        throw new Error("Missing data_source_id");
      }
      return dataSource.data_source_id;
    });
    return this.batchDeleteItems(dataSourceIds, Schemas.DataSource.name);
  }

  /**
   * Create a new item
   * @param item - Item to create
   * @param schema - Schema type
   */
  postItem(item: Entity, schema: SchemaType) {
    const path = this.buildPath(schema);
    return API.post(this.apiName, path, { body: item });
  }

  /**
   * Create multiple items
   * @param items - Items to create
   * @param schema - Schema type
   */
  postItems(items: Entity[], schema: SchemaType) {
    const path = this.buildPath(schema);
    return API.post(this.apiName, path, { body: items });
  }

  /**
   * Helper method to add type query parameter to path
   * @param path - Base path
   * @param type - Type value for composite key
   */
  private addTypeParam(path: string, type: string): string {
    return `${path}?type=${encodeURIComponent(type)}`;
  }

  /**
   * Update an item
   * @param item_id - Item ID
   * @param update - Update data
   * @param schema - Schema type
   * @param item_type - Optional type for composite key schemas
   */
  putItem(item_id: EntityId, update: Entity, schema: SchemaType, item_type?: string) {
    let path = this.buildPath(schema, item_id);
    if (item_type) {
      path = this.addTypeParam(path, item_type);
    }
    return API.put(this.apiName, path, { body: update });
  }

  /**
   * Delete an item
   * @param item_id - Item ID
   * @param schema - Schema type
   * @param item_type - Optional type for composite key schemas
   */
  deleteItem(item_id: EntityId, schema: SchemaType, item_type?: string) {
    let path = this.buildPath(schema, item_id);
    if (item_type) {
      path = this.addTypeParam(path, item_type);
    }
    return API.del(this.apiName, path, this.DEFAULT_OPTIONS);
  }

  /**
   * Get a specific item
   * @param item_id - Item ID
   * @param schema - Schema type
   * @param item_type - Optional type for composite key schemas
   */
  getItem(item_id: EntityId, schema: SchemaType, item_type?: string) {
    let path = this.buildPath(schema, item_id);
    if (item_type) {
      path = this.addTypeParam(path, item_type);
    }
    return API.get(this.apiName, path, this.DEFAULT_OPTIONS);
  }

  /**
   * Get all items of a specific schema type
   * @param schema - Schema type
   */
  getItems(schema: SchemaType) {
    const path = this.buildPath(schema);
    return API.get(this.apiName, path, this.DEFAULT_OPTIONS);
  }

  // ===== OPTIMIZED METHODS WITH CACHING =====
  // ===== TODO : Add clear cache after all update methods ========

  /**
   * Get all items of a specific schema type with caching
   * @param schema - Schema type
   */
  async getItemsWithCache(schema: SchemaType) {
    const path = this.buildPath(schema);
    return this.cachedGet<any[]>(path);
  }

  /**
   * Get all applications with caching
   */
  async getAppsWithCache() {
    return this.cachedGet<any[]>("/user/app");
  }

  /**
   * Get all servers with caching
   */
  async getServersWithCache() {
    return this.cachedGet<any[]>("/user/server");
  }

  /**
   * Get all databases with caching
   */
  async getDatabasesWithCache() {
    return this.cachedGet<any[]>("/user/database");
  }

  /**
   * Get all waves with caching
   */
  async getWavesWithCache() {
    return this.cachedGet<any[]>("/user/wave");
  }

  // ===== CACHE MANAGEMENT =====

  /**
   * Clear the entire cache
   */
  clearCache() {
    this.cache.clear();
  }

  /**
   * Clear cache for a specific path
   * @param path - API path
   */
  clearCacheForPath(path: string) {
    const cacheKey = this.getCacheKey(path);
    this.cache.delete(cacheKey);
  }

  /**
   * Invalidate cache for a specific schema
   * @param schema - Schema type
   */
  invalidateCacheForSchema(schema: SchemaType) {
    const lSchema = this.normalizeSchema(schema);
    const pathPrefix = `/user/${lSchema}`;

    for (const key of this.cache.keys()) {
      if (key.includes(pathPrefix)) {
        this.cache.delete(key);
      }
    }
  }

  // ===== BATCH OPERATIONS =====

  /**
   * Delete multiple items
   * @param ids - Item IDs
   * @param schema - Schema type
   */
  async batchDeleteItems(ids: EntityId[], schema: SchemaType) {
    return Promise.all(ids.map((id) => this.deleteItem(id, schema)));
  }

  // ===== ERROR HANDLING =====

  /**
   * Safely execute an API call with error handling
   * @param apiCall - Function that makes the API call
   * @returns Promise that resolves to the API call result or rejects with the error
   */
  async safeApiCall<T>(apiCall: () => Promise<T>): Promise<T> {
    try {
      return await apiCall();
    } catch (error) {
      console.error("API Error:", error);
      // Return the error to be handled by the consumer
      throw error;
    }
  }

  // ===== HELPER METHODS =====

  /**
   * Normalize schema name
   * @param schema - Schema type
   */
  private normalizeSchema(schema: SchemaType): string {
    return schema === "application" ? "app" : schema;
  }

  /**
   * Build API path
   * @param schema - Schema type
   * @param id - Optional item ID
   * @param subResource - Optional sub-resource
   */
  private buildPath(schema: SchemaType, id?: EntityId, subResource?: string): string {
    const lSchema = this.normalizeSchema(schema);
    let path = `/user/${lSchema}`;

    if (id) {
      path += `/${id}`;
    }

    if (subResource) {
      path += `/${subResource}`;
    }

    return path;
  }

  /**
   * Get cache key for a path
   * @param path - API path
   */
  private getCacheKey(path: string): string {
    return `${this.apiName}:${path}`;
  }

  /**
   * Make a GET request with caching
   * @param path - API path
   * @param options - Request options
   */
  private async cachedGet<T>(path: string, options = {}): Promise<T> {
    const cacheKey = this.getCacheKey(path);
    const cached = this.cache.get(cacheKey);

    if (cached && Date.now() - cached.timestamp < this.CACHE_TTL) {
      return cached.data;
    }

    const response = await this.apiGet(path, options);
    this.cache.set(cacheKey, { data: response, timestamp: Date.now() });
    return response;
  }

  /**
   * Make a GET request
   * @param path - API path
   * @param options - Request options
   */
  private apiGet(path: string, options = {}): Promise<any> {
    return API.get(this.apiName, path, { ...this.DEFAULT_OPTIONS, ...options });
  }

  /**
   * Make a POST request
   * @param path - API path
   * @param options - Request options
   */
  private apiPost(path: string, options = {}): Promise<any> {
    return API.post(this.apiName, path, { ...this.DEFAULT_OPTIONS, ...options });
  }

  /**
   * Make a DELETE request
   * @param path - API path
   * @param options - Request options
   */
  private apiDelete(path: string, options = {}): Promise<any> {
    return API.del(this.apiName, path, { ...this.DEFAULT_OPTIONS, ...options });
  }
}
