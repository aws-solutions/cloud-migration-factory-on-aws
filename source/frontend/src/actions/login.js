/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import { API } from "aws-amplify";

export default class Login {
  constructor(session) {
    this.session = session;
  }

  getGroups() {
    const token = this.session.idToken.jwtToken;
    const options = {
      headers: {
        Authorization: token
      }
    };
    return API.get("login", "/login/groups", options);
  }
}
