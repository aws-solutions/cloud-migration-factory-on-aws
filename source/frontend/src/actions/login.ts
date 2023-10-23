// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { API } from "@aws-amplify/api";
import {Auth} from "@aws-amplify/auth";

export default class Login {
  constructor(session) {
    this.session = session;
    this.apiName = 'login'
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
    return new Login(session);
  }

  getGroups() {
    return API.get(this.apiName, "/login/groups", this.options);
  }
}
