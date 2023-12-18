/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {API} from "@aws-amplify/api";

export default class LoginApiClient {
  private readonly apiName = 'login';
  getGroups() {
    return API.get(this.apiName, "/login/groups", {});
  }
}
