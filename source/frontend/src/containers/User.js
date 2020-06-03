import React, { Component } from "react";
import { Auth } from "aws-amplify";
import Admin from "../actions/admin";
import User from "../actions/user";
import UserStageNav from "../components/UserStageNav";
import UserAppList from "../components/UserAppList";
import UserTab from "../components/UserTab";
import NavBar from "../components/NavBar";
import { withCookies, Cookies } from 'react-cookie';
import { instanceOf } from 'prop-types';

class UserView extends Component {
  static propTypes = {
    cookies: instanceOf(Cookies).isRequired
  };
  constructor(props) {
    super(props);

    this.state = {
      isAuthenticated: props.isAuthenticated,
      isLoading: true,
      stages: [],
      selectedStage: null,
      apps: [],
      waves: [],
      app: {},
      appServers: [],
      roles: [],
      jwt: {},
      allowedStages: [],
      showDialog: true,
    };
  }

  decodeJwt(token) {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace('-', '+').replace('_', '/');
    const decodedJwt = JSON.parse(window.atob(base64));
    this.setState({jwt: decodedJwt});
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    const token = session.idToken.jwtToken;
    this.decodeJwt(token);

    this.apiAdmin = await new Admin(session);
    this.apiUser = await new User(session);
    this.getStages();
    this.getApps();
    this.getWaves();
    this.getRoles();
    this.setState({ isLoading: false });
  }

  componentDidUpdate() {
    var allowedStages = [];

    // Additional processing once all data has loaded
    if (this.state.stages.length > 0 &&
        this.state.roles.length > 0 &&
        Object.keys(this.state.jwt).length > 0 &&
        this.state.allowedStages.length === 0){

      // Get list of stages user is authorized for
      const userGroups = this.state.jwt['cognito:groups'];
      var isAdmin = false
      if (userGroups !== undefined) {
        if (userGroups.includes('admin')) {
          isAdmin = true
        }
      for (var role in this.state.roles) {
        for (var group in this.state.roles[role].groups) {
          const role_group = this.state.roles[role].groups[group].group_name

          if (userGroups.includes(role_group)) {
            for (var stage in this.state.roles[role].stages) {
              const allowedStage = this.state.roles[role].stages[stage].stage_id;
              if (!allowedStages.includes(allowedStage)){
                allowedStages.push(allowedStage);
              }
            }
          }
        }
      }
    }
    else {
      window.alert("You are not authorized to manage the factory, please login as a different user")
      this.props.history.push("/login")
    }

      // if cookie is set determine index value based on stage_id and set selectedStage
      var setWithCookie = false;
      const { cookies } = this.props;
      if (cookies.get('stage')){
        var cookie = cookies.get('stage');
        for (stage in this.state.stages){
          if (cookie === this.state.stages[stage].stage_id){
            this.setState({selectedStage: parseInt(stage)});
            setWithCookie = true;
          }
        }
      }

      // Set the first allowed stage to the active stage
      if (! setWithCookie){
        for (stage in this.state.stages){
          if (allowedStages.includes(this.state.stages[stage].stage_id)){
            this.setState({selectedStage: parseInt(stage)})
            break;
          }
        }
      }

      if (allowedStages.length !== 0) {
        this.setState({allowedStages: allowedStages})
        }
        else {
          window.alert("You are not authorized to manage the pipeline, please login as a different user")
          if (isAdmin) {
          this.props.history.push("/admin/attribute")
        }
        else {
          this.props.history.push("/login")
        }
        }
    }
  }

  async getRoles() {
    try {
      const response = await this.apiAdmin.getRoles();
      this.setState({ roles : response});
    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.props.showError(e.response.data);
      } else{
        this.props.showError('Unknown error occured')
      }
    }
  }

  async getStages() {
    try {
      const response = await this.apiAdmin.getStages();
      this.setState({ stages : response});

    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.props.showError(e.response.data);
      } else{
        this.props.showError('Unknown error occured')
      }
    }
  }

  closeDialog = () => {
    this.setState({
      showDialog: false
    });
  }

  async getApps() {
    try {
      const response = await this.apiUser.getApps();
      this.setState({ apps : response});

    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.props.showError(e.response.data);
      } else{
        this.props.showError('Unknown error occured')
      }
    }
  }

  async getWaves() {
    try {
      const response = await this.apiUser.getWaves();
      this.setState({ waves : response});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  updateServerList = (action, server) => {

    if (action === 'update') {
      for (var i in this.state.appServers){
        if (this.state.appServers[i].server_id === server.server_id) {
          let newState = Array.from(this.state.appServers);
          newState[i] = server;
          this.setState({appServers: newState});
        }
      }
    }

    if (action === 'delete') {
      var newState = []
      for (i in this.state.appServers){
        if (this.state.appServers[i].server_id !== server.server_id) {
          newState.push(this.state.appServers[i]);
        }
      }
      this.setState({appServers: newState});
    }

    if (action === 'add') {
      let newState = Array.from(this.state.appServers);
      newState.push(server);
      this.setState({appServers: newState});
    }

  }

  async getAppServers(app) {
    try {
      const response = await this.apiUser.getAppServers(app.app_id);
      return response;
    // API returns error if app has no servers instead of empty list.
    // Just return empty list if error occurs until fixed.
    } catch (e) {
      return [];
    }
  }

  updateAppList = (action, app) => {
    var i;

    switch(action) {
      case 'add':
        let newApps = Array.from(this.state.apps);
        newApps.push(app);
        this.setState({
          app: app,
          apps: newApps
        });
        break;
      case 'update':
        for (i in this.state.apps) {
          if (app.app_id === this.state.apps[i].app_id) {
            let newApps = Array.from(this.state.apps);
            newApps[i] = app;
            this.setState({
              app: app,
              apps: newApps
            });
          }
        }
        break;
      case 'delete':
        var newApps = [];
        for (i in this.state.apps) {
          if (app.app_id !== this.state.apps[i].app_id) {
            newApps.push(this.state.apps[i]);
          }
        }
        this.setState({
          app: {},
          apps: newApps
        });
        break;

      default:
    }
  }

  onClickCreateNew = event => {
    event.preventDefault();

    const newApp = {
      app_name: 'New application',
      app_id: null
    }

    this.setState({
      app: newApp
    })
  }

  onClickChangeStage = index => event => {
    event.preventDefault();

    if(this.state.allowedStages.includes(this.state.stages[index].stage_id)){
      this.setState({selectedStage: index});
      this.handleCookieChange(this.state.stages[index].stage_id);
    }else{
      var allowedStages = ''
      for (var stage in this.state.stages){
        if (this.state.allowedStages.includes(this.state.stages[stage].stage_id)){
          allowedStages = allowedStages+'- '+this.state.stages[stage].stage_name+'\n'
        }
      }

      alert('You are not authorized to work on '+
      this.state.stages[index].stage_name+
      '\n\nYou are currently authorized for:\n'+
      allowedStages);
    }
  }

  onClickSetSelectedApp = app_id => async event => {
    event.preventDefault();
    this.setState({ isLoading: true });

    try {
      const response = await this.apiUser.getApp(app_id);
      const servers = await this.getAppServers(response);

      this.setState({
        selectedApp: app_id,
        app: response,
        appServers: servers
      });

    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.props.showError(e.response.data);
      } else{
        this.props.showError('Unknown error occured')
      }
    }
    this.setState({ isLoading: false });
  }

  handleCookieChange(stage_id) {
     const { cookies } = this.props;
     cookies.set('stage', stage_id , { path: '/' });
   }
  render() {
    if (!this.state.isAuthenticated){
      this.props.history.push("/login");
    }
    console.log(this.state.selectedStage)

    return (
      <div>

        <NavBar
          onLoad={this.props.onLoadMenu}
          onClick={this.props.onClickMenu}
          selection="Pipeline"
        />

        <UserStageNav
          stages={this.state.stages}
          selectedStage={this.state.selectedStage}
          isLoading={this.state.isLoading}
          onClick={this.onClickChangeStage}
        />

        <div className="container-fluid">
          <div className="row">
            <div className="col-3">

                <UserAppList
                  apps={this.state.apps}
                  waves={this.state.waves}
                  isLoading={this.state.isLoading}
                  selectedApp={this.state.selectedApp}
                  onClick={this.onClickSetSelectedApp}
                  onClickCreateNew={this.onClickCreateNew}
                  allowCreate={(parseInt(this.state.selectedStage) === 0)? true: false}
                />

            </div>
            <div className="col-9">

              <UserTab
                isLoading={this.state.isLoading}
                app={this.state.app}
                waves={this.state.waves}
                stage={this.state.stages[this.state.selectedStage]}
                showError={this.props.showError}
                updateAppList={this.updateAppList}
                appServers={this.state.appServers}
                updateServerList={this.updateServerList}
                allowCreate={(parseInt(this.state.selectedStage) === 0)? true: false}
              />

            </div>
          </div>
        </div>
      </div>
    );
  }
}
export default withCookies(UserView);
