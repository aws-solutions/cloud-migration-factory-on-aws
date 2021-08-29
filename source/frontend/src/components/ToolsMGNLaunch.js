import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Admin from "../actions/admin";
import Tools from "../actions/tools";
import ToolsMGNLaunchDialog from "../components/ToolsMGNLaunchDialog";

export default class UserListApps extends Component {
  constructor(props) {
    super(props);
    this.state = {
      waves: [],
      aws_accountid: [],
      isLoading: props.isLoading,
      MGNData: {},
      showDialog: false,
      isDanger: false,
      submitReady: false,
      mgnmsg: '',
      waitPeriod: false,
      fieldset: 'disabled',
      isConfirm: false
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
    if (nextProps.MGNData !== this.props.MGNData){
      this.setState({
        MGNData: nextProps.MGNData
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
      var accountlist = []
      for (var i=0; i < response['attributes'].length;i++) {
        if (response['attributes'][i]['name'] === 'aws_accountid') {
          accountlist = response['attributes'][i]['listvalue'].split(",")
          accountlist.push('All Accounts')
        }
      }
      this.setState({ aws_accountid: accountlist});
      console.log(this.state.aws_accountid)
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
      mgnmsg: ''
    });

    try {
      const response  = await this.apiTools.postMGN(this.state.MGNData);
      console.log(response)
      this.setState({
        mgnmsg: response,
        waitPeriod: false
      });
    } catch (e) {
      console.log(e);
      if (e.response) {
        this.setState({
          mgnmsg: e.response.data,
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

  onChangeAttrName = type => event => {

    if (type === 'accountid') {
      let newAttr = Object.assign({}, this.state.MGNData);
      newAttr.accountid = event.target.value.trim();
    this.setState({
      MGNData: newAttr
    })
    }
    if (type === 'action') {
      if (event.target.value === '- Revert to ready for testing') {
        this.setState({
          isDanger: true,
          submitReady: false,
          isConfirm: false
        })
        }
      else if (event.target.value === '- Revert to ready for cutover') {
        this.setState({
          isDanger: true,
          submitReady: false,
          isConfirm: false
        })
        }
      else if (event.target.value === '- Terminate Launched instances') {
        this.setState({
          isDanger: true,
          submitReady: false,
          isConfirm: false
        })
        }
      else if (event.target.value === '- Disconnect from AWS') {
        this.setState({
          isDanger: true,
          submitReady: false,
          isConfirm: false
        })
        }
      else if (event.target.value === '- Mark as archived') {
        this.setState({
          isDanger: true,
          submitReady: false,
          isConfirm: false
        })
        }
      else {this.setState({
        isDanger: false,
        submitReady: true
      })}
      let newAttr = Object.assign({}, this.state.MGNData);
      newAttr.action = event.target.value.trim();
    this.setState({
      MGNData: newAttr
    })
    }
    if (type === 'isConfirm') {
      if (event.target.checked === true) {
        this.setState({
          submitReady: true,
          isConfirm: event.target.checked
        })
      }
    else {
      this.setState({
        submitReady: false,
        isConfirm: event.target.checked
      })
    }
    }
    if (type === 'waveid') {
      let newAttr = Object.assign({}, this.state.MGNData);
      newAttr.waveid = event.target.value.trim();
    this.setState({
      MGNData: newAttr
    })
    }
    console.log(this.state.MGNData)
      }

  render() {
    return (
      <div>
        {this.state.showDialog &&
          <ToolsMGNLaunchDialog
            showDialog={this.state.showDialog}
            mgnmsg={this.state.mgnmsg}
            waitPeriod={this.state.waitPeriod}
            onClickUpdate={this.onClickUpdate}
          />
        }
        <div className="row px-3 pt-3"><h4>Application Migration configuration</h4></div>
        {/* { !this.state.isLoading && */}
        <form>
          <div className="row px-3 pt-3">
            <div className="col-6 px-0 pr-5">
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
                <div className="form-group">
                  <label htmlFor="AccountId">AWS Account ID:</label>
                  <select onChange={this.onChangeAttrName('accountid')} className="form-control form-control-sm" defaultValue="none" id="waveid">
                    <option value="none" disabled> Select Target AWS Account </option>
                    {this.state.aws_accountid.map((item, index) => {
                        return (
                          <option key={item} value={item}>{item}</option>
                        )
                      })}
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="type">Test and Cutover:</label>
                  <select onChange={this.onChangeAttrName('action')} className="form-control form-control-sm" defaultValue="none" id="action">
                   <option value="none" disabled> Select Action </option>
                    <option >Validate Launch Template</option>
                    <option >Launch Test Instances</option>
                    <option >Mark as Ready for Cutover</option>
                    <option >Launch Cutover Instances</option>
                    <option >Finalize Cutover</option>
                    <option value="none" disabled className='text-red'> ----- Danger Zone ----- </option>
                    <option className='text-red'>- Revert to ready for testing</option>
                    <option className='text-red'>- Revert to ready for cutover</option>
                    <option className='text-red'>- Terminate Launched instances</option>
                    <option className='text-red'>- Disconnect from AWS</option>
                    <option className='text-red'>- Mark as archived</option>
                  </select>
                  </div>
                  { this.state.isDanger &&
                  <div className="form-check">
                  <input
                         className="form-check-input"
                         name="isConfirm"
                         onChange={this.onChangeAttrName('isConfirm')}
                         checked={this.state.isConfirm}
                         type="checkbox"/>
                  <label htmlFor="isConfirm" >I confirm that I understand the danger zone actions</label>
                  </div>
                  }
                <input className="btn btn-primary btn-outline mt-3 mr-3"
                       value="Submit"
                       onClick={this.onClickLaunch}
                       disabled={!this.state.submitReady}
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
