import React, { Component } from "react";
import { Auth } from "aws-amplify";
import { withRouter } from "react-router-dom";
import Routes from "./Routes";
import AppDialog from "./components/AppDialog";
import Admin from "./actions/admin";
import config from "./config";

class App extends Component {
  constructor(props) {
    super(props);

    // Time of last mousemove event, used to auto logout after x minutes of inactivity
    this.lastActivity = Date.now();

    // Default to auto logout after 30 minutes
    this.autoLogout = 30;

    // Change default if configuration exists
    if ('application' in config){
      if (config.application.AUTO_LOGOUT !== undefined){
        this.autoLogout = config.application.AUTO_LOGOUT
      }
    }

    this.state = {
      isAuthenticated: false,
      isAuthenticating: true,
      isError: false,
      error: null,
      showDialog: false,
      msg: '',
      jwt: {},
      roles: [],
      stages: [],
      allowedCreate: false,
      userGroups: []
    };
  }

  decodeJwt(token) {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace('-', '+').replace('_', '/');
    const decodedJwt = JSON.parse(window.atob(base64));
    this.setState({jwt: decodedJwt});
  }

  async componentDidMount() {
    this.timerID = setInterval(
      () => this.tick(),
      1000
    );

    try {
      if (await Auth.currentSession()) {
        this.userHasAuthenticated(true);
      }
      const session = await Auth.currentSession();
      const token = session.idToken.jwtToken;
      this.apiAdmin = await new Admin(session);
      this.decodeJwt(token);
      this.getPermissions();
    }
    catch(e) {
      if (e !== 'No current user') {
        alert(e);
      }
    }

    this.setState({ isAuthenticating: false });
  }

  componentWillUnmount() {
    clearInterval(this.timerID);
  }

  onMouseMove = event => {
    this.lastActivity = Date.now();
  }

  tick = async event => {
    if (this.state.isAuthenticated){
      const minutesSinceActivity = Math.abs(Date.now() - this.lastActivity) / 1000 / 60

      if (minutesSinceActivity > this.autoLogout){
        await Auth.signOut({ global: true });
        this.userHasAuthenticated(false);
        this.props.history.push("/login");
      }
    }
  }

  userHasAuthenticated = authenticated => {
    this.setState({ isAuthenticated: authenticated });
  }

  async getPermissions() {
    try {
      const stages = await this.apiAdmin.getStages();
      const roles = await this.apiAdmin.getRoles();

      var allowedCreate = false;
      const userGroups = this.state.jwt['cognito:groups'];
      this.setState({userGroups: userGroups});

      // Additional processing once all data has loaded
      if (stages.length > 0 &&
        roles.length > 0 &&
        Object.keys(this.state.jwt).length > 0){

        // Get list of stages user is authorized for
        for (var role in roles) {
          for (var group in roles[role].groups) {
            const role_group = roles[role].groups[group].group_name
            if (userGroups.includes(role_group)) {
              for (var stage in roles[role].stages) {
                const allowedStage = roles[role].stages[stage].stage_id;
                  if (allowedStage.toString() === '1') {
                    allowedCreate = true
                  }
              }
            }
          }
        }
        this.setState({allowedCreate: allowedCreate});
      }
    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.showError(e.response.data);
      } else{
        console.log()
        this.showError('Unknown error occured')
      }
    }
  }

  onLoadMenu = async event => {
    const session = await Auth.currentSession();
    const token = session.idToken.jwtToken;
    this.apiAdmin = await new Admin(session);
    this.decodeJwt(token);
    this.getPermissions();
  }

  onClickMenu = async event => {
    event.preventDefault();
    const action = event.currentTarget.textContent;
    switch(action) {
      case 'Pipeline':
        this.props.history.push("/");
        break;
      case 'Admin':
        if (!(this.state.userGroups.includes('admin'))) {
          this.setState({
            showDialog: true,
            msg: "You are not authorized to manage the admin page"
          });
        }
        else {
          this.props.history.push("/admin/attribute");
          }
        break;
      case 'Resource List':
        if (this.state.allowedCreate === true) {
        this.props.history.push("/waves");
        }
        else {
          this.setState({
            showDialog: true,
            msg: "You are not authorized to manage application list"
          });
        }
        break;
      case 'Tools':
      this.props.history.push("/tools/mgn");
        break;
      case 'Logout':
        await Auth.signOut({ global: true });
        this.userHasAuthenticated(false);
        this.props.history.push("/login");
        break;
      default:
        break;
    }
  }

  onClickUpdate = event => {
    this.setState({
      showDialog: false
    });
  }

  hideError = event => {
    event.preventDefault();
    this.setState({
      isError: false,
      error: null
    });
  }

  showError = message => {
    if(message === Object(message)){
      message = JSON.stringify(message);
    }

    this.setState({
      isError: true,
      error: message
    });
  }

  render() {
    const childProps = {
      isAuthenticated: this.state.isAuthenticated,
      userHasAuthenticated: this.userHasAuthenticated,
      showError: this.showError,
      onClickMenu: this.onClickMenu,
      onLoadMenu: this.onLoadMenu
    };

    return (

      !this.state.isAuthenticating &&
      <div className="container-fluid px-0" onMouseMove={this.onMouseMove}>
        {this.state.showDialog &&
              <AppDialog
                showDialog={this.state.showDialog}
                msg={this.state.msg}
                onClickUpdate={this.onClickUpdate}
              />
        }
        {this.state.isError?<div className="alert-box alert alert-danger">{this.state.error}<span onClick={this.hideError} className="alert-box-close btn">X</span></div>:null}
        <Routes childProps={childProps} />
      </div>
    );
  }
}

export default withRouter(App);
