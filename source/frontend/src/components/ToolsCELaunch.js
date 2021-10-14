import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Admin from "../actions/admin";
import Tools from "../actions/tools";
import ToolsCELaunchDialog from "../components/ToolsCELaunchDialog";

export default class UserListApps extends Component {
  constructor(props) {
    super(props);
    this.state = {
      waves: [],
      cloudendure_projects: [],
      isLoading: props.isLoading,
      CloudEndureData: {},
      showDialog: false,
      cloudenduremsg: '',
      waitPeriod: false,
      fieldset: 'disabled',
      isRelaunch: false
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.apiTools = await new Tools(session);
    this.apiUser = await new User(session);
    this.apiAdmin = await new Admin(session);
    this.getWaves();
    this.getSchemas();
  }

  componentWillReceiveProps(nextProps){
    if (nextProps.CloudEndureData !== this.props.CloudEndureData){
      this.setState({
        CloudEndureData: nextProps.CloudEndureData
      });
    };
    if (nextProps.showDialog !== this.props.showDialog){
      this.setState({
        showDialog: nextProps.showDialog
      });
    };
    if (nextProps.waveids !== this.props.waveids){
      this.setState({
        waveids: nextProps.waveids
      });
    };
    this.setState({
      isLoading: nextProps.isLoading
    });
  }

  async getWaves(session) {
    const response = await this.apiUser.getWaves();
    this.setState({ waves: response});
    console.log(this.state.waves)
  }catch (e) {
    console.log(e);
    if ('data' in e.response) {
      this.props.showError(e.response.data);
    }
  }

  async getSchemas(session) {
    try {
      const response = await this.apiAdmin.getSchemaApp();
      var projectlist = []
      for (var i=0; i < response['attributes'].length;i++) {
        if (response['attributes'][i]['name'] === 'cloudendure_projectname') {
          projectlist = response['attributes'][i]['listvalue'].split(",")
        }
      }
      this.setState({ cloudendure_projects: projectlist});
      console.log(this.state.cloudendure_projects)
    }catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  async LaunchServer() {
    this.setState({
      isLoading: true,
      showDialog: true,
      waitPeriod: true,
      cloudenduremsg: ''
    });

    // this.setState({
    //   cloudenduremsg: 'test response',
    //   waitPeriod: false
    // });

    try {
      const response  = await this.apiTools.postCloudEndure(this.state.CloudEndureData);
      console.log(response)
      this.setState({
        cloudenduremsg: response,
        waitPeriod: false
      });
    } catch (e) {
      console.log(e);
      if (e.response) {
        this.setState({
          cloudenduremsg: e.response.data,
          waitPeriod: false
        });
      }
    }
    this.setState({isLoading: false});
  }

  async CheckServer() {
    this.setState({
      isLoading: true,
      showDialog: true,
      waitPeriod: true,
      cloudenduremsg: ''
    });

    try {
      let checkdata = Object.assign({}, this.state.CloudEndureData);
      checkdata.statuscheck = "yes"
      const response  = await this.apiTools.postCloudEndure(checkdata);
      console.log(response)
      this.setState({
        cloudenduremsg: response,
        waitPeriod: false
      });
    } catch (e) {
      console.log(e);
      if (e.response) {
        this.setState({
          cloudenduremsg: e.response.data,
          waitPeriod: false
        });
      }
    }
    this.setState({isLoading: false});
  }

  async CleanupServer() {
    this.setState({
      isLoading: true,
      showDialog: true,
      waitPeriod: true,
      cloudenduremsg: ''
    });

    try {
      let cleanupdata = Object.assign({}, this.state.CloudEndureData);
      cleanupdata.cleanup = "yes"
      const response  = await this.apiTools.postCloudEndure(cleanupdata);
      console.log(response)
      this.setState({
        cloudenduremsg: response,
        waitPeriod: false
      });
    } catch (e) {
      console.log(e);
      if (e.response) {
        this.setState({
          cloudenduremsg: e.response.data,
          waitPeriod: false
        });
      }
    }
    this.setState({isLoading: false});
  }

  onClickUpdate = event => {
    this.setState({
      showDialog: false
    });
  }
  onClickLaunch = event => {
    event.preventDefault();
    this.LaunchServer();
      }
  onClickStatusCheck = event => {
    event.preventDefault();
    this.CheckServer();
      }
  onClickCleanup = event => {
    event.preventDefault();
    this.CleanupServer();
      }

  onChangeAttrName = type => event => {
    if (type === 'userapitoken') {
      let newAttr = Object.assign({}, this.state.CloudEndureData);
      newAttr.userapitoken = event.target.value.trim();
    this.setState({
      CloudEndureData: newAttr
    })
    }
    if (type === 'projectname') {
      let newAttr = Object.assign({}, this.state.CloudEndureData);
      newAttr.projectname = event.target.value.trim();
    this.setState({
      CloudEndureData: newAttr
    })
    }
    if (type === 'dryrun') {
      let newAttr = Object.assign({}, this.state.CloudEndureData);
      if (event.target.value.trim() === 'yes') {
      newAttr.dryrun = event.target.value.trim();
      } else {
        delete newAttr["dryrun"];
      }
    this.setState({
      CloudEndureData: newAttr
    })
    }
    if (type === 'launchtype') {
      let newAttr = Object.assign({}, this.state.CloudEndureData);
      newAttr.launchtype = event.target.value.trim();
    this.setState({
      CloudEndureData: newAttr
    })
    }
    if (type === 'relaunch') {
      let newAttr = Object.assign({}, this.state.CloudEndureData);
      newAttr.relaunch = event.target.checked;
    this.setState({
      CloudEndureData: newAttr,
      isRelaunch: event.target.checked
    })
    }
    if (type === 'waveid') {
      let newAttr = Object.assign({}, this.state.CloudEndureData);
      newAttr.waveid = event.target.value.trim();
    this.setState({
      CloudEndureData: newAttr
    })
    }
    console.log(this.state.CloudEndureData)
      }

  render() {
    return (
      <div>
        {this.state.showDialog &&
          <ToolsCELaunchDialog
            showDialog={this.state.showDialog}
            cloudenduremsg={this.state.cloudenduremsg}
            waitPeriod={this.state.waitPeriod}
            onClickUpdate={this.onClickUpdate}
          />
        }
        <div className="row px-3 pt-3"><h4>CloudEndure Launch configuration</h4></div>
        {/* { !this.state.isLoading && */}
        <form>
          <div className="row px-3 pt-3">
            <div className="col-6 px-0 pr-5">
                <div className="form-group">
                  <label htmlFor="APItoken">CloudEndure API Token:</label>
                  <input className="form-control form-control-sm"
                         onChange={this.onChangeAttrName('userapitoken')}
                         type="password"/>
                </div>
                <div className="form-group">
                  <label htmlFor="ProjectName">CloudEndure Project Name:</label>
                  <select onChange={this.onChangeAttrName('projectname')} className="form-control form-control-sm" defaultValue="none" id="waveid">
                    <option value="none" disabled> Select Project Name </option>
                    {this.state.cloudendure_projects.map((item, index) => {
                        return (
                          <option key={item} value={item}>{item}</option>
                        )
                      })}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="type">Dryrun:</label>
                  <select onChange={this.onChangeAttrName('dryrun')} className="form-control form-control-sm" defaultValue="none" id="launchType">
                   <option value="none" disabled> Select Dryrun options </option>
                    <option > yes </option>
                    <option > no </option>
                  </select>
                  </div>
                <div className="form-group">
                  <label htmlFor="type">Launch Type:</label>
                  <select onChange={this.onChangeAttrName('launchtype')} className="form-control form-control-sm" defaultValue="none" id="launchType">
                   <option value="none" disabled> Select Launch Type </option>
                    <option > test </option>
                    <option > cutover </option>
                  </select>
                  </div>
                <div className="form-group">
                  <label htmlFor="waveid">Wave Id:</label>
                  <select onChange={this.onChangeAttrName('waveid')} className="form-control form-control-sm" defaultValue="none" id="waveid">
                    <option value="none" disabled> Select Wave Id </option>
                    {this.state.waves.map((item, index) => {
                        return (
                          <option key={item.wave_name} value={item.wave_id}>{item.wave_name}</option>
                        )
                      })}
                  </select>
                  </div>
                  <div className="form-check">
                  <input
                         className="form-check-input"
                         name="isRelaunch"
                         onChange={this.onChangeAttrName('relaunch')}
                         checked={this.state.isRelaunch}
                         type="checkbox"/>
                  <label htmlFor="relaunch" >Enforce a server relaunch</label>
                  </div>
                <input className="btn btn-primary btn-outline mt-3 mr-3"
                       value="Launch Servers"
                       onClick={this.onClickLaunch}
                       type="button"/>
                <input className="btn btn-primary btn-outline mt-3 mr-3"
                       value="Status check"
                       onClick={this.onClickStatusCheck}
                       type="button"/>
                <input className="btn btn-danger btn-outline mt-3"
                       value="Remove servers from CloudEndure"
                       onClick={this.onClickCleanup}
                       type="button"/>
            </div>
          </div>
        </form>
        <br></br>
        <br></br>
      </div>
    );
  }
};
