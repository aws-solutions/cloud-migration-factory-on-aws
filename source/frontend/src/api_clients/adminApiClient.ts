/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */
import {API} from "@aws-amplify/api";
import {EntitySchema, SchemaMetaData} from "../models/EntitySchema";

export default class AdminApiClient {
  private readonly apiName = 'admin';

  getSchemas(): Promise<SchemaMetaData[]> {
    return API.get(this.apiName, "/admin/schema", {});
  }

  getSchema(schemaName: string): Promise<EntitySchema> {
    return API.get(this.apiName, "/admin/schema/" + schemaName, {});
  }

  putSchema(schemaName: string, schema: Partial<EntitySchema>) {
    const schemastr = JSON.stringify(schema)
    const data = '{ "event":"PUT", "update_schema":' + schemastr + '}'
    const obj = JSON.parse(data)
    return API.put(this.apiName, '/admin/schema/' + schemaName, {body: obj});
  }

  putSchemaAttr(schemaName: string, attr: any, attr_name: string) {
    const attrstr = JSON.stringify(attr)
    const data = '{ "event":"PUT" , "name":"' + attr_name + '", "update":' + attrstr + '}'
    const obj = JSON.parse(data)
    return API.put(this.apiName, '/admin/schema/' + schemaName, {body: obj});
  }

  postSchemaAttr(schemaName: string, attr: any) {
    const attrstr = JSON.stringify(attr)
    const data = '{ "event":"POST", "new":' + attrstr + '}'
    const obj = JSON.parse(data)
    return API.put(this.apiName, '/admin/schema/' + schemaName, {body: obj});
  }

  delSchemaAttr(schemaName: string, attr_name: string) {
    const data = '{ "event":"DELETE" , "name":"' + attr_name + '"}'
    const obj = JSON.parse(data)
    return API.put(this.apiName, '/admin/schema/' + schemaName, {body: obj});
  }

  putPolicy(policy: any) {
    return API.put(this.apiName, '/admin/policy/' + policy.policy_id, {body: policy});
  }

  postPolicy(policy: any) {
    return API.post(this.apiName, '/admin/policy', {body: policy});
  }

  delPolicy(policy_id: any) {
    return API.del(this.apiName, '/admin/policy/' + policy_id, {});
  }

  getPolicies() {
    return API.get(this.apiName, "/admin/policy", {});
  }

  getUsers() {
    return API.get(this.apiName, "/admin/users", {});
  }

  putUsers(users: any) {
    return API.put(this.apiName, "/admin/users", {body: {'users': users}});
  }

  getRoles() {
    return API.get(this.apiName, "/admin/role", {});
  }

  putRole(role: any) {
    // Remove role_id from body before PUT to meet API enforcement
    let updateRole = Object.assign({}, role);
    delete updateRole.role_id
    return API.put(this.apiName, '/admin/role/' + role.role_id, {body: updateRole});
  }

  postRole(role: any) {
    return API.post(this.apiName, '/admin/role', {body: role});
  }

  delRole(role_id: any) {
    return API.del(this.apiName, '/admin/role/' + role_id, {});
  }

  postGroups(groups: Record<'groups', Array<any>>) {
    return API.post(this.apiName, '/admin/groups', {body: groups});
  }

  delGroup(group_name: any) {
    return API.del(this.apiName, '/admin/groups/' + encodeURIComponent(group_name), {});
  }

  deleteCredential(data: any) {
    return API.del(this.apiName, "/admin/credentialmanager", {body: data});
  }

  updateCredential(data: any) {
    return API.put(this.apiName, "/admin/credentialmanager", {body: data});
  }

  addCredential(data: any) {
    return API.post(this.apiName, "/admin/credentialmanager", {body: data});
  }

}
