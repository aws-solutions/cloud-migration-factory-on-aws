// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { API } from "@aws-amplify/api";
import {Auth} from "@aws-amplify/auth";

export default class User {
  constructor(session) {
    this.session = session;
    this.apiName = 'user'
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
    return new User(session);
  }

  getNotifications() {
    return API.get(this.apiName, "/user/notifications", this.options);
  }

  getApps() {
    return API.get(this.apiName, "/user/app", this.options);
  }

  getWaves() {
    return API.get(this.apiName, "/user/wave", this.options);
  }

  postWave(wave) {
    return API.post(this.apiName, "/user/wave/", {...this.options, ...{body: wave}});
  }

  deleteWave(wave_id) {
    return API.del(this.apiName, "/user/wave/"+wave_id, this.options);
  }


  getServers() {
    return API.get(this.apiName, "/user/server", this.options);
  }

  getAppServers(app_id) {
    return API.get(this.apiName, "/user/server/appid/"+app_id, this.options);
  }

  getDatabases() {
    return API.get(this.apiName, "/user/database", this.options);
  }

  getAppDatabases(app_id) {
    return API.get(this.apiName, "/user/database/appid/"+app_id, this.options);
  }

  deleteDatabase(database_id) {
    return API.del(this.apiName, "/user/database/"+database_id, this.options);
  }

  putDatabase(database_id, update) {
    return API.put('user', '/user/database/'+database_id, {...this.options, ...{body: update}});
  }

  postDatabase(database) {
    return API.post(this.apiName, "/user/database/", {...this.options, ...{body: database}});
  }

  getApp(app_id) {
    return API.get(this.apiName, "/user/app/"+app_id, this.options);
  }

  deleteApp(app_id) {
    return API.del(this.apiName, "/user/app/"+app_id, this.options);
  }

  postApp(app) {
    return API.post(this.apiName, "/user/app/", {...this.options, ...{body: app}});
  }

  putWave(wave_id, update) {
    return API.put('user', '/user/wave/'+wave_id, {...this.options, ...{body: update}});
  }

  putApp(app_id, update) {
    return API.put('user', '/user/app/'+app_id, {...this.options, ...{body: update}});
  }

  putServer(server_id, update) {
    return API.put('user', '/user/server/'+server_id, {...this.options, ...{body: update}});
  }

  deleteServer(server_id) {
    return API.del(this.apiName, "/user/server/"+server_id, this.options);
  }

  postServer(server) {
    return API.post(this.apiName, "/user/server/", {...this.options, ...{body: server}});
  }

  postServers(servers) {
    return API.post(this.apiName, "/user/server/", {...this.options, ...{body: servers}});
  }

  postItem(item, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    return API.post(this.apiName, "/user/" + lSchema + "/", {...this.options, ...{body: item}});
  }

  postItems(items, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    return API.post(this.apiName, "/user/" + lSchema + "/" , {...this.options, ...{body: items}});
  }

  putItem(item_id, update, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    return API.put('user', "/user/" + lSchema + "/"+item_id, {...this.options, ...{body: update}});
  }

  deleteItem(server_id, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    return API.del(this.apiName, "/user/"+ lSchema +"/"+server_id, this.options);
  }

  getItem(id, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    return API.get(this.apiName, "/user/"+  lSchema + "/"+id, this.options);
  }

  getItems(schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    return API.get(this.apiName, "/user/" + lSchema, this.options);
  }
}
