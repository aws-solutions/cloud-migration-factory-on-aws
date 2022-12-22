/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { API } from "aws-amplify";

export default class Admin {
  constructor(session) {
    this.session = session;
  }

  getSchemas() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/schema", options);
  }

  getSchema(schemaName) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/schema/" + schemaName, options);
  }

  putSchema(schemaName, schema) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    var schemastr = JSON.stringify(schema)
    var data = '{ "event":"PUT", "update_schema":' + schemastr + '}'
    var obj = JSON.parse(data)
    const options = {
      body: obj,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.put('admin', '/admin/schema/' + schemaName, options);
  }

  postSchema(schemaName, schema) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    var schemastr = JSON.stringify(schema)
    var obj = JSON.parse(schemastr)
    const options = {
      body: obj,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.post('admin', '/admin/schema/' + schemaName, options);
  }

  delSchema(schemaName) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del('admin', '/admin/schema/' + schemaName, options);
  }

  getSchemaAttributes(schemaName) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/schema/" + schemaName,options);
  }

  putSchemaAttr(schemaName, attr, attr_name) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    var attrstr = JSON.stringify(attr)
    var data = '{ "event":"PUT" , "name":"' + attr_name + '", "update":' + attrstr + '}'
    var obj = JSON.parse(data)
    const options = {
      body: obj,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.put('admin', '/admin/schema/' + schemaName, options);
  }

  postSchemaAttr(schemaName, attr) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    var attrstr = JSON.stringify(attr)
    var data = '{ "event":"POST", "new":' + attrstr + '}'
    var obj = JSON.parse(data)
    const options = {
      body: obj,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.put('admin', '/admin/schema/' + schemaName, options);
  }

  delSchemaAttr(schemaName, attr_name) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    var data = '{ "event":"DELETE" , "name":"' + attr_name + '"}'
    var obj = JSON.parse(data)
    const options = {
      body: obj,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.put('admin', '/admin/schema/' + schemaName, options);
  }

  putPolicy(policy) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      body: policy,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.put('admin', '/admin/policy/'+policy.policy_id, options);
  }

  postPolicy(policy) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      body: policy,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.post('admin', '/admin/policy', options);
  }

  delPolicy(policy_id) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.del('admin', '/admin/policy/'+policy_id, options);
  }

  getPolicy(policy_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/policy/"+policy_id, options);
  }

  getPolicies() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/policy", options);
  }

  getUsers() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/users", options);
  }

  putUsers(users) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      body: {'users' :users},
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.put("admin", "/admin/users", options);
  }

  getRoles() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/role", options);
  }

  putRole(role) {
    // Remove role_id from body before PUT to meet API enforcement
    let updateRole = Object.assign({}, role);
    delete updateRole.role_id

    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      body: updateRole,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.put('admin', '/admin/role/'+role.role_id, options);
  }

  postRole(role) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      body: role,
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.post('admin', '/admin/role', options);
  }

  delRole(role_id) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.del('admin', '/admin/role/'+role_id, options);
  }

  postGroups(group) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      body: {'groups': group},
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.post('admin', '/admin/groups', options);
  }

  delGroup(group_name) {
    const token = this.session.idToken.jwtToken;
    const accesstoken = this.session.accessToken.jwtToken;
    const options = {
      headers: {
        Authorization: token,
        'Authorization-Access': accesstoken
      }
    };
    return API.del('admin', '/admin/groups/'+encodeURIComponent(group_name), options);
  }

}
