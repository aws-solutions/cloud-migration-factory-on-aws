import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Admin from "../actions/admin";
import Tools from "../actions/tools";
import ToolsAMSLaunchDialog from "../components/ToolsAMSLaunchDialog";

export default class UserListApps extends Component {
  constructor(props) {
    super(props);
    this.state = {
      waves: [],
      cloudendure_projects: [],
      isLoading: props.isLoading,
      AMSData: {},
      showDialog: false,
      waitPeriod: false,
      AMSmsg: ''
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
    if (nextProps.AMSData !== this.props.AMSData){
      this.setState({
        AMSData: nextProps.AMSData
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

  async SubmitRFC() {
    this.setState({
      isLoading: true,
      waitPeriod: true
    });

    try {
      const response  = await this.apiTools.postAMSWIG(this.state.AMSData);
      console.log(response)
      this.setState({
        showDialog: true,
        AMSmsg: response,
        waitPeriod: false

      });
    } catch (e) {
      console.log(e);
      if (e.response) {
        this.setState({
          showDialog: true,
          waitPeriod: false,
          AMSmsg: e.response.data
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
    this.SubmitRFC();
      }

  onChangeAttrName = type => event => {
    event.preventDefault();
    if (type === 'userapitoken') {
      let newAttr = Object.assign({}, this.state.AMSData);
      newAttr.userapitoken = event.target.value.trim();
    this.setState({
      AMSData: newAttr
    })
    }
    if (type === 'projectname') {
      let newAttr = Object.assign({}, this.state.AMSData);
      newAttr.projectname = event.target.value.trim();
    this.setState({
      AMSData: newAttr
    })
    }
    if (type === 'key_id') {
      let newAttr = Object.assign({}, this.state.AMSData);
      newAttr.key_id = event.target.value.trim();
    this.setState({
      AMSData: newAttr
    })
    }
    if (type === 'secret') {
      let newAttr = Object.assign({}, this.state.AMSData);
      newAttr.secret = event.target.value.trim();
    this.setState({
      AMSData: newAttr
    })
    }
    if (type === 'waveid') {
      let newAttr = Object.assign({}, this.state.AMSData);
      newAttr.waveid = event.target.value.trim();
    this.setState({
      AMSData: newAttr
    })
    }
    console.log(this.state.AMSData)
      }

  render() {
    return (
      <div>
        {this.state.showDialog &&
          <ToolsAMSLaunchDialog
            showDialog={this.state.showDialog}
            AMSmsg={this.state.AMSmsg}
            waitPeriod={this.state.waitPeriod}
            onClickUpdate={this.onClickUpdate}
          />
        }
        <div class="row px-3 pt-3"> <h4>AMS Workload Ingest RFC</h4></div>
        <form>
          <div class="row px-3 pt-3">
            <div class="col-6 px-0 pr-5">
                <div class="form-group">
                  <label htmlfor="APItoken">CloudEndure API Token:</label>
                  <input class="form-control form-control-sm"
                         onChange={this.onChangeAttrName('userapitoken')}
                         Value=''
                         type="password"/>
                </div>

                <div class="form-group">
                  <label htmlfor="ProjectName">CloudEndure Project Name:</label>
                  <select onChange={this.onChangeAttrName('projectname')} className="form-control form-control-sm" defaultValue="none" id="waveid">
                    <option value="none" disabled> Select Project Name </option>
                    {this.state.cloudendure_projects.map((item, index) => {
                        return (
                          <option key={item} value={item}>{item}</option>
                        )
                      })}
                  </select>
                </div>

                <div class="form-group">
                  <label htmlfor="APItoken">AMS Access Key ID:</label>
                  <input class="form-control form-control-sm"
                         onChange={this.onChangeAttrName('key_id')}
                         Value=''
                         type="text"/>
                </div>

                <div class="form-group">
                  <label htmlfor="APItoken">AMS Secret Access Key:</label>
                  <input class="form-control form-control-sm"
                         onChange={this.onChangeAttrName('secret')}
                         Value=''
                         type="password"/>
                </div>

                <div class="form-group">
                  <label htmlfor="waveid">Wave Id:</label>
                  <select onChange={this.onChangeAttrName('waveid')} className="form-control form-control-sm" defaultValue="none" id="waveid">
                    <option value="none" disabled> Select Wave Id </option>
                    {this.state.waves.map((item, index) => {
                        return (
                          <option key={item.wave_name} value={item.wave_id}>{item.wave_name}</option>
                        )
                      })}
                  </select>
                  </div>

                <input class="btn btn-primary btn-outline mt-3 mr-3"
                       value="Submit AMS RFC"
                       onClick={this.onClickLaunch}
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
