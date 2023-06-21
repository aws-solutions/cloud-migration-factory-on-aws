/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { API } from "@aws-amplify/api";

export default class User {
  constructor(session) {
    this.session = session;
  }

  getNotifications() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/notifications", options);
  }

  getApps() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/app", options);
  }

  getWaves() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/wave", options);
  }

  postWave(wave) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: wave,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/wave/", options);
  }

  deleteWave(wave_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("user", "/user/wave/"+wave_id, options);
  }


  getServers() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/server", options);
  }

  getAppServers(app_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/server/appid/"+app_id, options);
  }

  getDatabases() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/database", options);
  }

  getAppDatabases(app_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/database/appid/"+app_id, options);
  }

  deleteDatabase(database_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("user", "/user/database/"+database_id, options);
  }

  putDatabase(database_id, update) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: update,
      headers: {
        Authorization: token
      }
    };
    return API.put('user', '/user/database/'+database_id, options);
  }

  postDatabase(database) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: database,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/database/", options);
  }

  getApp(app_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/app/"+app_id, options);
  }

  deleteApp(app_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("user", "/user/app/"+app_id, options);
  }

  postApp(app) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: app,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/app/", options);
  }

  putWave(wave_id, update) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: update,
      headers: {
        Authorization: token
      }
    };
    return API.put('user', '/user/wave/'+wave_id, options);
  }

  putApp(app_id, update) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: update,
      headers: {
        Authorization: token
      }
    };
    return API.put('user', '/user/app/'+app_id, options);
  }

  putServer(server_id, update) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: update,
      headers: {
        Authorization: token
      }
    };
    return API.put('user', '/user/server/'+server_id, options);
  }

  deleteServer(server_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("user", "/user/server/"+server_id, options);
  }

  postServer(server) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: server,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/server/", options);
  }

  postServers(servers) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: servers,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/server/", options);
  }

  postItem(item, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    const token = this.session.idToken.jwtToken;
    const options = {
      body: item,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/" + lSchema + "/", options);
  }

  postItems(items, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    const token = this.session.idToken.jwtToken;
    const options = {
      body: items,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/" + lSchema + "/" , options);
  }

  putItem(item_id, update, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    const token = this.session.idToken.jwtToken;
    const options = {
      body: update,
      headers: {
        Authorization: token
      }
    };
    return API.put('user', "/user/" + lSchema + "/"+item_id, options);
  }

  deleteItem(server_id, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("user", "/user/"+ lSchema +"/"+server_id, options);
  }

  getItem(id, schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/"+  lSchema + "/"+id, options);
  }

  getItems(schema) {
    let lSchema = schema;
    if (lSchema === 'application') {
      lSchema = 'app';
    }
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/" + lSchema, options);
  }
}
