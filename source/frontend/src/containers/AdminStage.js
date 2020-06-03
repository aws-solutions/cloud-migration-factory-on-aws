import React, { Component } from "react";
import { Auth } from "aws-amplify";
import AdminNav from "../components/AdminNav";
import AdminStageList from "../components/AdminStageList";
import AdminStageTab from "../components/AdminStageTab";
import Admin from "../actions/admin";
import NavBar from "../components/NavBar";
import AppDialog from "../components/AppDialog";

export default class AdminStage extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isAuthenticated: props.isAuthenticated,
      activeNav: 'stage',
      isLoading: true,
      stages: [],
      selectedStage: '',
      stage: {},
      jwt: {},
      allowedCreate: false,
      showDialog: false,
      msg: ''
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
    this.api = await new Admin(session);
    this.getStages();
    this.decodeJwt(token);
    this.getPermissions();
    this.setState({ isLoading: false });
  }

  async getStages(session) {
    try {
      const response = await this.api.getStages();
      this.setState({ stages : response});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  async getPermissions() {
    try {
        const userGroups = this.state.jwt['cognito:groups'];
        if (!(userGroups.includes('admin'))) {
          this.setState({
            showDialog: true,
            msg: "You are not authorized to manage the admin page"
          });
        }
        else {
          this.setState({
            allowedCreate: true
          });
          }
    } catch (e) {
      console.log(e);
      if ('response' in e && 'data' in e.response) {
        this.props.showError(e.response.data);
      } else{
        this.props.showError('Unknown error occured')
      }
    }
  }

  onClickUpdate = event => {
    this.setState({
      showDialog: false
    });
    this.props.history.push("/");
  }

  onLoadMenu = async event => {
    const session = await Auth.currentSession();
    const token = session.idToken.jwtToken;
    this.apiAdmin = await new Admin(session);
    this.decodeJwt(token);
    this.getPermissions();
  }

  onClickSetSelectedStage = stage_id => async event => {
    event.preventDefault();
    this.setState({ isLoading: true });
    try {
      const response = await this.api.getStage(stage_id);

      this.setState({
        selectedStage: stage_id,
        stage: response
      });

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({ isLoading: false });
  }

  updateStageList = (action, stage) => {
    var i = 0;

    switch(action) {
      case 'update':
        for ( i = 0; i < this.state.stages.length; i++) {
          if (stage.stage_id === this.state.stages[i].stage_id) {
            let newStages = Array.from(this.state.stages);
            newStages[i] = stage;
            this.setState({stages: newStages});
          };
        };
        break;

      case 'add':
        this.getStages();
        this.setState({
          selectedStage: stage.stage_id,
          stage: stage
        });
        break;

      case 'delete':
        for ( i = 0; i < this.state.stages.length; i++) {
          if (stage.stage_id === this.state.stages[i].stage_id) {
            let newStages = Array.from(this.state.stages);
            newStages.splice(i, 1);
            this.setState({
              stages: newStages,
              selectedStage: ''
            });
          }
        }
        break;

      default:
        break;
    }
  }

  onClickChangeActiveNav = event => {
    event.preventDefault();
    switch(event.target.id) {
      case 'attribute':
        this.props.history.push("/admin/attribute");
        break;
      case 'role':
        this.props.history.push("/admin/role");
        break;
      default:
        break;
    }
  }

  onClickCreateNew = event => {
    event.preventDefault();
    const newStage = {
      stage_name: 'New Stage',
      stage_id: null
    };

    this.setState({
      stage: newStage,
      selectedStage: ''
    });
  }

  render() {
    if (!this.state.isAuthenticated){
      this.props.history.push("/login");
    }

    if (!this.state.allowedCreate) {
      return (
        <div>
        <AppDialog
        showDialog={this.state.showDialog}
        msg={this.state.msg}
        onClickUpdate={this.onClickUpdate}
      />
      </div>
      )
    }

    else {
    return (
      <div>
        <NavBar
          onClick={this.props.onClickMenu}
          onLoad={this.props.onLoadMenu}
          selection="Admin"
        />
        <AdminNav onClick={this.onClickChangeActiveNav} active={this.state.activeNav}/>
        <div className="container-fluid">
          <div className="row">
            <div className="col-3">
              <AdminStageList
                selectedStage={this.state.selectedStage}
                onClick={this.onClickSetSelectedStage}
                stages={this.state.stages}
                onClickCreateNew={this.onClickCreateNew}
                isLoading={this.state.isLoading}
              />
            </div>
            <div className="col-9">
              <AdminStageTab
                stage={this.state.stage}
                updateStageList={this.updateStageList}
                createNew={this.state.createNew}
                isLoading={this.state.isLoading}
                showError={this.props.showError}
              />
            </div>
          </div>
        </div>
      </div>
    );
    }
  }
}
