import React, { Component } from "react";
import { Auth } from "aws-amplify";
import AdminNav from "../components/AdminNav";
import AdminRoleList from "../components/AdminRoleList";
import AdminRoleTab from "../components/AdminRoleTab";
import Admin from "../actions/admin";
import NavBar from "../components/NavBar";
import AppDialog from "../components/AppDialog";

export default class AdminRole extends Component {
  constructor(props) {
    super(props);
    this.state = {
      isAuthenticated: props.isAuthenticated,
      activeNav: 'role',
      isLoading: true,
      roles: [],
      selectedRole: '',
      role: {},
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
    this.getRoles();
    this.setState({ isLoading: false });
    this.decodeJwt(token);
    this.getPermissions();
  }

  async getRoles(session) {
    try {
      const response = await this.api.getRoles();
      this.setState({ roles : response});

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
  
  onClickSetSelectedRole = role_id => async event => {
    event.preventDefault();
    this.setState({ isLoading: true });

    for ( var i = 0; i < this.state.roles.length; i++) {
      if (role_id === this.state.roles[i].role_id) {
        this.setState({
          selectedRole: role_id,
          role: this.state.roles[i]
        });
      };
    };

    this.setState({ isLoading: false });
  }

  updateRoleList = (action, role) => {
    var i = 0;

    switch(action) {
      case 'update':
        for ( i = 0; i < this.state.roles.length; i++) {
          if (role.role_id === this.state.roles[i].role_id) {
            let newRoles = Array.from(this.state.roles);
            newRoles[i] = role;
            this.setState({roles: newRoles});
          };
        };
        break;

      case 'add':
        this.getRoles();
        this.setState({
          selectedStage: role.role_id,
          role: role
        });
        break;

      case 'delete':
        for ( i = 0; i < this.state.roles.length; i++) {
          if (role.role_id === this.state.roles[i].role_id) {
            let newRoles = Array.from(this.state.roles);
            newRoles.splice(i, 1);
            this.setState({
              roles: newRoles,
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
      case 'stage':
        this.props.history.push("/admin/stage");
        break;
      default:
        break;
    }
  }

  onClickCreateNew = event => {
    event.preventDefault();
    const newRole = {
      role_name: 'New Role',
      role_id: null,
      stages: [],
      groups: []
    };

    this.setState({
      role: newRole,
      selectedRole: ''
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
              <AdminRoleList
                selectedRole={this.state.selectedRole}
                onClick={this.onClickSetSelectedRole}
                roles={this.state.roles}
                onClickCreateNew={this.onClickCreateNew}
                isLoading={this.state.isLoading}
              />
            </div>
            <div className="col-9">
              <AdminRoleTab
                role={this.state.role}
                updateRoleList={this.updateRoleList}
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
