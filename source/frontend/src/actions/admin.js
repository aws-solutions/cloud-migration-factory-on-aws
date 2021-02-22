import { API } from "aws-amplify";

export default class Admin {
  constructor(session) {
    this.session = session;
  }

  getSchemaWave() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/schema/wave", options);
  }

  getSchemaApp() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/schema/app", options);
  }

  getSchemaServer() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get('admin', '/admin/schema/server', options);
  }

  putStage(stage) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: stage,
      headers: {
        Authorization: token
      }
    };
    return API.put('admin', '/admin/stage/'+stage.stage_id, options);
  }

  postStage(stage) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: stage,
      headers: {
        Authorization: token
      }
    };
    return API.post('admin', '/admin/stage', options);
  }

  delStage(stage_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del('admin', '/admin/stage/'+stage_id, options);
  }

  getStage(stage_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/stage/"+stage_id, options);
  }

  getStages() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("admin", "/admin/stage", options);
  }

  getWaveAttributes() {
    const token = this.session.idToken.jwtToken;
    const options = {
                        headers: {
                          Authorization: token
                        }
                      };
    return API.get("admin", "/admin/schema/wave",options);
  }

  getAppAttributes() {
    const token = this.session.idToken.jwtToken;
    const options = {
                        headers: {
                          Authorization: token
                        }
                      };
    return API.get("admin", "/admin/schema/app",options);
  }

  getServerAttributes() {
    const token = this.session.idToken.jwtToken;
    const options = {
                        headers: {
                          Authorization: token
                        }
                      };
    return API.get("admin", "/admin/schema/server",options);
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
    const options = {
      body: updateRole,
      headers: {
        Authorization: token
      }
    };
    return API.put('admin', '/admin/role/'+role.role_id, options);
  }

  postRole(role) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: role,
      headers: {
        Authorization: token
      }
    };
    return API.post('admin', '/admin/role', options);
  }

  delRole(role_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del('admin', '/admin/role/'+role_id, options);
  }

delWaveSchemaAttr(attr_name) {
  const token = this.session.idToken.jwtToken;
  var data = '{ "event":"DELETE" , "name":"' + attr_name + '"}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/wave', options);
}

delAppSchemaAttr(attr_name) {
  const token = this.session.idToken.jwtToken;
  var data = '{ "event":"DELETE" , "name":"' + attr_name + '"}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/app', options);
}

delSerSchemaAttr(attr_name) {
  const token = this.session.idToken.jwtToken;
  var data = '{ "event":"DELETE" , "name":"' + attr_name + '"}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/server', options);
}

putWaveSchemaAttr(attr, attr_name) {
  const token = this.session.idToken.jwtToken;
  var attrstr = JSON.stringify(attr)
  var data = '{ "event":"PUT" , "name":"' + attr_name + '", "update":' + attrstr + '}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/wave', options);
}

putAppSchemaAttr(attr, attr_name) {
  const token = this.session.idToken.jwtToken;
  var attrstr = JSON.stringify(attr)
  var data = '{ "event":"PUT" , "name":"' + attr_name + '", "update":' + attrstr + '}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/app', options);
}

putServerSchemaAttr(attr, attr_name) {
  const token = this.session.idToken.jwtToken;
  var attrstr = JSON.stringify(attr)
  var data = '{ "event":"PUT" , "name":"' + attr_name + '", "update":' + attrstr + '}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/server', options);
}

postWaveSchemaAttr(attr) {
  const token = this.session.idToken.jwtToken;
  var attrstr = JSON.stringify(attr)
  var data = '{ "event":"POST", "new":' + attrstr + '}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/wave', options);
}

postAppSchemaAttr(attr) {
  const token = this.session.idToken.jwtToken;
  var attrstr = JSON.stringify(attr)
  var data = '{ "event":"POST", "new":' + attrstr + '}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/app', options);
}

postServerSchemaAttr(attr) {
  const token = this.session.idToken.jwtToken;
  var attrstr = JSON.stringify(attr)
  var data = '{ "event":"POST", "new":' + attrstr + '}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/server', options);
}

}
