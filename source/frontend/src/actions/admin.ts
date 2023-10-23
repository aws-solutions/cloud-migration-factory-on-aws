// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {API} from "@aws-amplify/api";
import {Auth} from "@aws-amplify/auth";

export default class Admin {
  constructor(session) {
    this.session = session;
    this.apiName = 'admin'
    const accessToken = this.session.accessToken.jwtToken;
    // Setup default request option headers
    this.options = {
      headers: {
        Authorization: this.session.idToken.jwtToken,
        'Authorization-Access': accessToken
      }
    }
  }

  static async initializeCurrentSession() {
    const session = await Auth.currentSession();
    return new Admin(session);
  }

  getSchemas() {
    return API.get(this.apiName, "/admin/schema", this.options);
  }

  getSchema(schemaName) {
    return API.get(this.apiName, "/admin/schema/" + schemaName, this.options);
  }

  putSchema(schemaName, schema) {
    const schemastr = JSON.stringify(schema)
    const data = '{ "event":"PUT", "update_schema":' + schemastr + '}'
    const obj = JSON.parse(data)
    return API.put(this.apiName, '/admin/schema/' + schemaName, {...this.options, ...{body: obj}});
  }

  postSchema(schemaName, schema) {
    const schemastr = JSON.stringify(schema)
    const obj = JSON.parse(schemastr)
    return API.post(this.apiName, '/admin/schema/' + schemaName, {...this.options, ...{body: obj}});
  }

  delSchema(schemaName) {
    return API.del(this.apiName, '/admin/schema/' + schemaName, this.options);
  }

  putSchemaAttr(schemaName, attr, attr_name) {
    const attrstr = JSON.stringify(attr)
    const data = '{ "event":"PUT" , "name":"' + attr_name + '", "update":' + attrstr + '}'
    const obj = JSON.parse(data)
    return API.put(this.apiName, '/admin/schema/' + schemaName, {...this.options, ...{body: obj}});
  }

  postSchemaAttr(schemaName, attr) {
    const attrstr = JSON.stringify(attr)
    const data = '{ "event":"POST", "new":' + attrstr + '}'
    const obj = JSON.parse(data)
    return API.put(this.apiName, '/admin/schema/' + schemaName, {...this.options, ...{body: obj}});
  }

  delSchemaAttr(schemaName, attr_name) {
    const data = '{ "event":"DELETE" , "name":"' + attr_name + '"}'
    const obj = JSON.parse(data)
    return API.put(this.apiName, '/admin/schema/' + schemaName, {...this.options, ...{body: obj}});
  }

  putPolicy(policy) {
    return API.put(this.apiName, '/admin/policy/'+policy.policy_id, {...this.options, ...{body: policy}});
  }

  postPolicy(policy) {
    return API.post(this.apiName, '/admin/policy', {...this.options, ...{body: policy}});
  }

  delPolicy(policy_id) {
    return API.del(this.apiName, '/admin/policy/'+policy_id, this.options);
  }

  getPolicy(policy_id) {
    return API.get(this.apiName, "/admin/policy/"+policy_id, this.options);
  }

  getPolicies() {
    return API.get(this.apiName, "/admin/policy", this.options);
  }

  getUsers() {
    return API.get(this.apiName, "/admin/users", this.options);
  }

  putUsers(users) {
    return API.put(this.apiName, "/admin/users", {...this.options, ...{body: {'users' :users}}});
  }

  getRoles() {
    return API.get(this.apiName, "/admin/role", this.options);
  }

  putRole(role) {
    // Remove role_id from body before PUT to meet API enforcement
    let updateRole = Object.assign({}, role);
    delete updateRole.role_id
    return API.put(this.apiName, '/admin/role/'+role.role_id, {...this.options, ...{body: updateRole}});
  }

  postRole(role) {
    return API.post(this.apiName, '/admin/role', {...this.options, ...{body: role}});
  }

  delRole(role_id) {
    return API.del(this.apiName, '/admin/role/'+role_id, this.options);
  }

  postGroups(group) {
    return API.post(this.apiName, '/admin/groups', {...this.options, body: group});
  }

  delGroup(group_name) {
    return API.del(this.apiName, '/admin/groups/'+encodeURIComponent(group_name), this.options);
  }

  deleteCredential(data){
    return API.del(this.apiName, "/admin/credentialmanager", {...this.options, ...{body: data}});
  }

  updateCredential(data){
    return API.put(this.apiName, "/admin/credentialmanager", {...this.options, ...{body: data}});
  }

  addCredential(data){
    return API.post(this.apiName, "/admin/credentialmanager", {...this.options, ...{body: data}});
  }

}
