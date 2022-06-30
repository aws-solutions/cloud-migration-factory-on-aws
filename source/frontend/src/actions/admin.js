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
    var schemastr = JSON.stringify(schema)
    var data = '{ "event":"PUT", "update_schema":' + schemastr + '}'
    var obj = JSON.parse(data)
    const options = {
      body: obj,
      headers: {
        Authorization: token
      }
    };
    return API.put('admin', '/admin/schema/' + schemaName, options);
  }

  postSchema(schemaName, schema) {
    const token = this.session.idToken.jwtToken;
    var schemastr = JSON.stringify(schema)
    var obj = JSON.parse(schemastr)
    const options = {
      body: obj,
      headers: {
        Authorization: token
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
    var attrstr = JSON.stringify(attr)
    var data = '{ "event":"PUT" , "name":"' + attr_name + '", "update":' + attrstr + '}'
    var obj = JSON.parse(data)
    const options = {
      body: obj,
      headers: {
        Authorization: token
      }
    };
    return API.put('admin', '/admin/schema/' + schemaName, options);
  }

  postSchemaAttr(schemaName, attr) {
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
    return API.put('admin', '/admin/schema/' + schemaName, options);
  }

  delSchemaAttr(schemaName, attr_name) {
    const token = this.session.idToken.jwtToken;
    var data = '{ "event":"DELETE" , "name":"' + attr_name + '"}'
    var obj = JSON.parse(data)
    const options = {
      body: obj,
      headers: {
        Authorization: token
      }
    };
    return API.put('admin', '/admin/schema/' + schemaName, options);
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

  getSchemaDatabase() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get('admin', '/admin/schema/database', options);
  }

  putPolicy(policy) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: policy,
      headers: {
        Authorization: token
      }
    };
    return API.put('admin', '/admin/policy/'+policy.policy_id, options);
  }

  postPolicy(policy) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: policy,
      headers: {
        Authorization: token
      }
    };
    return API.post('admin', '/admin/policy', options);
  }

  delPolicy(policy_id) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
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

  getDatabaseAttributes() {
    const token = this.session.idToken.jwtToken;
    const options = {
                        headers: {
                          Authorization: token
                        }
                      };
    return API.get("admin", "/admin/schema/database",options);
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

delDatabaseSchemaAttr(attr_name) {
  const token = this.session.idToken.jwtToken;
  var data = '{ "event":"DELETE" , "name":"' + attr_name + '"}'
  var obj = JSON.parse(data)
  const options = {
    body: obj,
    headers: {
      Authorization: token
    }
  };
  return API.put('admin', '/admin/schema/database', options);
}

putDatabaseSchemaAttr(attr, attr_name) {
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
  return API.put('admin', '/admin/schema/database', options);
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

postDatabaseSchemaAttr(attr) {
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
  return API.put('admin', '/admin/schema/database', options);
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
