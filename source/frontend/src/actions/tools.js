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

}
