// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { API } from "@aws-amplify/api";
import {Auth} from "@aws-amplify/auth";

export default class Tools {
  constructor(session) {
    this.session = session;
    this.apiName = 'tools'
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
    return new Tools(session);

  }

  postCloudEndure(ce) {
    return API.post(this.apiName, "/cloudendure", this.options);
  }

  postMGN(mgn) {
    return API.post(this.apiName, "/mgn", {...this.options, ...{body: mgn}});
  }

  postTool(apiPath, data) {
    return API.post(this.apiName, apiPath, {...this.options, ...{body: data}});
  }

  getTool(apiPath) {
    return API.get(this.apiName, apiPath, this.options);
  }

  getSSMJobs(maximumDays=undefined) {
    let daysToReturn = ''
    if (maximumDays !== undefined) {
      daysToReturn = '?maximumdays=' + maximumDays
    }
    return API.get(this.apiName, "/ssm/jobs" + daysToReturn, this.options);
  }

  deleteSSMJobs(ssmid) {
    return API.del(this.apiName, "/ssm/jobs/" + ssmid, this.options);
  }

  getSSMScripts() {
    return API.get(this.apiName, "/ssm/scripts", this.options);
  }

  getSSMScript(package_uuid, version, download = false) {
    if (download){
      return API.get(this.apiName, "/ssm/scripts/" + package_uuid + "/" + version + "/download", this.options);
    } else {
      return API.get(this.apiName, "/ssm/scripts/" + package_uuid + "/" + version, this.options);
    }
  }

  postSSMScripts(data) {
    return API.post(this.apiName, "/ssm/scripts", {...this.options, ...{body: data}});
  }

  putSSMScripts(data) {
    return API.put(this.apiName, "/ssm/scripts/" + data.package_uuid, {...this.options, ...{body: data}});
  }

  getCredentials(){
    return API.get(this.apiName, "/credentialmanager", this.options);
  }
}
