import { API } from "aws-amplify";

export default class Tools {
  constructor(session) {
    this.session = session;
  }

  postCloudEndure(ce) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: ce,
      headers: {
        Authorization: token
      }
    };
    return API.post("tools", "/cloudendure", options);
  }

  postAMSWIG(ams) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: ams,
      headers: {
        Authorization: token
      }
    };
    return API.post("tools", "/amswig", options);
  }

  postMGN(mgn) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: mgn,
      headers: {
        Authorization: token
      }
    };
    return API.post("tools", "/mgn", options);
  }

  postTool(apiPath, data) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: data,
      headers: {
        Authorization: token
      }
    };
    return API.post("tools", apiPath, options);
  }

  getTool(apiPath) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("tools", apiPath, options);
  }

  getSSMJobs() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("tools", "/ssm/jobs", options);
  }

  deleteSSMJobs(ssmid) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.del("tools", "/ssm/jobs/" + ssmid, options);
  }

  getSSMScripts() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("tools", "/ssm/scripts", options);
  }

  getSSMScript(package_uuid, version, download = false) {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    if (download){
      return API.get("tools", "/ssm/scripts/" + package_uuid + "/" + version + "/download", options);
    } else {
      return API.get("tools", "/ssm/scripts/" + package_uuid + "/" + version, options);
    }
  }

  postSSMScripts(data) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: data,
      headers: {
        Authorization: token
      }
    };
    return API.post("tools", "/ssm/scripts", options);
  }

  putSSMScripts(data) {
    const token = this.session.idToken.jwtToken;
    const options = {
      body: data,
      headers: {
        Authorization: token
      }
    };
    return API.put("tools", "/ssm/scripts/" + data.package_uuid, options);
  }
}
