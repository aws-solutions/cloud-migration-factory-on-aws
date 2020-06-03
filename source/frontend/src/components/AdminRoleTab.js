import React from "react";
import { Auth } from "aws-amplify";
import Admin from "../actions/admin";
import Login from "../actions/login";

export default class AdminRoleTab extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      role: props.role,
      isLoading: true,
      stages: [],
      groups: []
    };
  }

  /*
  This is the replacement for componentWillReceiveProps but it doesn't work right yet..
  static getDerivedStateFromProps(nextProps, prevState) {
    if (nextProps.role !== prevState.role){
      return({
        role: nextProps.role,
        isLoading: nextProps.isLoading
      });
    };
    return({isLoading: nextProps.isLoading});
  }
  */

  componentWillReceiveProps(nextProps){
    this.setState({
      isLoading: nextProps.isLoading
    });

    if (nextProps.role !== this.props.role){
      this.setState({
        role: nextProps.role
      });
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.api = await new Admin(session);
    this.apiLogin = await new Login(session);

    this.getStages();
    this.getGroups();
    this.setState({ isLoading: false });
  }

  async getGroups(session) {
    try {
      const response = await this.apiLogin.getGroups();
      this.setState({ groups : response});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
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

  async updateRole() {
    this.setState({isLoading: true});

    try {
      await this.api.putRole(this.state.role);
      this.props.updateRoleList('update', this.state.role);
    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLoading: false});
  }

  async createRole() {
    this.setState({isLoading: true});

    console.log('create role')
    console.log(this.state.role)

    try {
      const response = await this.api.postRole(this.state.role);

      this.setState({ role: response});
      this.props.updateRoleList('add', this.state.role);

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLoading: false});
  }

  async deleteRole() {
    this.setState({isLoading: true});

    try {
      await this.api.delRole(this.state.role.role_id);

      this.props.updateRoleList('delete', this.state.role);
      this.setState({role: {} });

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLoading: false});
  }

  getStageName(stage_id){
    for (var index in this.state.stages){
      if (this.state.stages[index].stage_id === stage_id){
        return this.state.stages[index].stage_name;
      }
    }
    return null;
  }

  onClickSaveRole = event => {
    event.preventDefault();
    if (this.state.role.role_id === null){
      this.createRole();
    } else {
      this.updateRole();
    }
  }

  onClickDeleteRole = event => {
    event.preventDefault();
    this.deleteRole();
  }

  onChangeRoleName = event => {
    let newRole = Object.assign({}, this.state.role);
    newRole.role_name = event.target.value.trim();
    this.setState({role: newRole});
  }

  onClickRemoveStage = id => event => {
    event.preventDefault();
    console.log(id)

    for (var i = 0; i < this.state.role.stages.length; i++) {
      if (id === this.state.role.stages[i].stage_id) {
        let newStages = Array.from(this.state.role.stages);
        newStages.splice(i, 1);;

        let newRole = Object.assign({}, this.state.role);
        newRole.stages = newStages;

        this.setState({role: newRole});
      }
    }
  }

  onClickRemoveGroup = id => event => {
    event.preventDefault();

    for (var i = 0; i < this.state.role.groups.length; i++) {
      if (id === this.state.role.groups[i].group_name) {
        let newGroups = Array.from(this.state.role.groups);
        newGroups.splice(i, 1);;

        let newRole = Object.assign({}, this.state.role);
        newRole.groups = newGroups;

        this.setState({role: newRole});
      }
    }
  }

  onClickAddStage = event => {
    this.refs.stage.blur();

    var alreadyExists = false;

    if ('stages' in this.state.role) {
      for (var i in this.state.role.stages) {
        if (event.target.value === this.state.role.stages[i].stage_id) {
          alreadyExists = true;
        }
      }
    }

    if (!alreadyExists) {
      const newStage = {
        stage_id: event.target.value
      }

      let newRole = Object.assign({}, this.state.role);

      if (!('stages' in newRole)){
        newRole.stages = [];
      }
      newRole.stages.push(newStage);

      this.setState({role: newRole});
    }
  }

  onClickAddGroup = event => {
    this.refs.group.blur();

    var alreadyExists = false;

    if ('groups' in this.state.role) {
      for (var i in this.state.role.groups) {
        if (event.target.value === this.state.role.groups[i].group_name) {
          alreadyExists = true;
        }
      }
    }

    if (!alreadyExists) {
      const newGroup = {
        group_name: event.target.value
      }

      let newRole = Object.assign({}, this.state.role);

      if (!('groups' in newRole)){
        newRole.groups = [];
      }
      newRole.groups.push(newGroup);

      this.setState({role: newRole});
    }
  }

  render() {
    var roleLoaded = false;
    if (Object.keys(this.state.role).length > 0){
      roleLoaded = true;
    }

    return (
      <div>
        {this.state.isLoading?<div className="block-events" ></div>:null}
        <div className="pt-3">
          <h4>> {roleLoaded?this.state.role.role_name:'No role selected'}</h4>
        </div>

        <div id="factory-tab" className="container-fluid rounded  py-3 px-0">
          <ul className="nav nav-tabs">
            <li className="nav-item">
              <span className="nav-link active">Role Configuration {this.state.isLoading?<i className="fa fa-spinner fa-spin"></i>:null}</span>
            </li>
          </ul>

          <div id="factory-tab-container" className="container-fluid rounded bg-white py-3 ">

            <div className="row px-3 pt-3"> <h3>{roleLoaded?this.state.role.role_name:'Please select role'} > Role Configuration</h3></div>
            <form>
              <div className="row px-3 pt-3">
                <div className="col-6 px-0 pr-5">
                  <div className="form-group">
                    <label htmlFor="roleName">Name:</label>
                    <input
                      disabled={!roleLoaded}
                      type="text"
                      key={this.state.role.role_id}
                      className="form-control form-control-sm"
                      onChange={this.onChangeRoleName}
                      defaultValue={this.state.role.role_name}
                      ref="roleName"
                    />
                  </div>


                  <div className="form-group">
                    <label htmlFor="attribute">Add Stage:</label>
                    <select disabled={!roleLoaded} ref="stage" onChange={this.onClickAddStage} value={'none'} className="form-control form-control-sm" id="stage">
                      <option value="none" disabled>Select stage to add</option>
                      {this.state.stages.map((item, index) => {
                        return (
                          <option key={item.stage_id} value={item.stage_id}>{item.stage_name}</option>
                        )
                      })}
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="attribute">Add Group:</label>
                    <select disabled={!roleLoaded} ref="group" onChange={this.onClickAddGroup} value={'none'} className="form-control form-control-sm" id="group">
                      <option value="none" disabled>Select group to add</option>
                      {this.state.groups.map((item, index) => {
                        return (
                          <option key={item} value={item}>{item}</option>
                        )
                      })}
                    </select>
                  </div>

                  <input
                    disabled={!roleLoaded}
                    className="btn btn-primary btn-outline mt-3 mr-3"
                    type="button"
                    value="Save Role"
                    onClick={this.onClickSaveRole}
                  />
                  <input
                    disabled={!roleLoaded || this.state.role.role_id === null}
                    className="btn btn-danger btn-outline mt-3"
                    type="button"
                    value="Delete Role"
                    onClick={this.onClickDeleteRole}
                  />
                </div>
                <div className="col-6 px-0 pr-5">

                  <div className="pb-2">
                    Stages linked to current role:
                  </div>
                  <table className="table table-hover">
                    <tbody>
                      {'stages' in this.state.role &&
                          this.state.role.stages.map((item, index) => {
                          var stageName = this.getStageName(item.stage_id);
                          return (
                            <tr key={item.stage_id}>
                              <td><span onClick={this.onClickRemoveStage(item.stage_id)} className="pr-3 text-danger">x</span> {stageName}</td>
                            </tr>
                          )
                        })
                      }

                      {(!('stages' in this.state.role)|| (this.state.role.stages.length === 0)) &&
                        <tr>
                          <td>No stages linked to role</td>
                        </tr>
                      }
                    </tbody>
                  </table>

                  <div className="pb-2 mt-5">
                    Groups linked to current role:
                  </div>
                  <table className="table table-hover">
                    <tbody>
                      {'groups' in this.state.role &&
                          this.state.role.groups.map((item, index) => {
                          return (
                            <tr key={item.group_name}>
                              <td><span onClick={this.onClickRemoveGroup(item.group_name)} className="pr-3 text-danger">x</span> {item.group_name}</td>
                            </tr>
                          )
                        })
                      }

                      {(!('groups' in this.state.role)|| (this.state.role.groups.length === 0)) &&
                        <tr>
                          <td>No groups linked to role</td>
                        </tr>
                      }

                    </tbody>
                  </table>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>

    );
  }
};
