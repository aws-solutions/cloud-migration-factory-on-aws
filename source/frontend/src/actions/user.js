import { API } from "aws-amplify";

export default class User {
  constructor(session) {
    this.session = session;
  }

  getApps() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/apps", options);
  }

  getWaves() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/waves", options);
  }

  postWave(wave) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: wave,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/waves/", options);
  }

  deleteWave(wave_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("user", "/user/waves/"+wave_id, options);
  }


  getServers() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/servers", options);
  }

  getAppServers(app_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/servers/appid/"+app_id, options);
  }

  getApp(app_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("user", "/user/apps/"+app_id, options);
  }

  deleteApp(app_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("user", "/user/apps/"+app_id, options);
  }

  postApp(app) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: app,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/apps/", options);
  }

  putApp(app_id, update) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: update,
      headers: {
        Authorization: token
      }
    };
    return API.put('user', '/user/apps/'+app_id, options);
  }

  putServer(server_id, update) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: update,
      headers: {
        Authorization: token
      }
    };
    return API.put('user', '/user/servers/'+server_id, options);
  }

  deleteServer(server_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("user", "/user/servers/"+server_id, options);
  }

  postServer(server) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: server,
      headers: {
        Authorization: token
      }
    };
    return API.post("user", "/user/servers/", options);
  }

}
