import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Admin from "../actions/admin";
import UserListColDialog from "../components/UserListColDialog";
import UserListUploadDialog from "../components/UserListUploadDialog";

export default class UserListApps extends Component {
  constructor(props) {
    super(props);

    this.state = {
      waves: props.waves,
      apps: props.apps,
      filteredApps: props.apps,
      searchApp: '',
      isLoading: props.isLoading,
      isLocked: false,
      selectedApp: '',
      showColumns: ['app_name', 'app_id', 'wave_id'],
      schemaApp : [],
      showDialog: false,
      showUploadDialog: false,
      uploadRunning: 'no',
      uploadProgress: 0,
      uploadErrors: 0
    };
  }

  async componentDidMount() {
    const session = await Auth.currentSession();
    this.apiAdmin = await new Admin(session);
    this.apiUser = await new User(session);
    this.getSchema();
  }

  componentWillReceiveProps(nextProps){
    this.setState({
      isLoading: nextProps.isLoading
    });

    if (nextProps.apps !== this.props.apps){
      this.setState({
        apps: nextProps.apps,
        filteredApps: nextProps.apps
      });
    };
  }

  async getSchema() {
    try {
      var response = await this.apiAdmin.getSchemaApp();
      this.setState({ schemaApp : response['attributes']});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  async deleteApp(app_id) {
    this.setState({isLocked: true});

    try {
      await this.apiUser.deleteApp(app_id);
      this.props.updateAppList('delete', app_id)

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLocked: false});
  }

  async createApp(app_name) {
    this.setState({isLocked: true});

    var app ={app_name: app_name}

    try {
      await this.apiUser.postApp(app);
      this.props.updateAppList('refresh', app_name)

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLocked: false});
  }

  onClickRemoveApp = app_id => event => {
    event.preventDefault();
    if (this.state.isLocked !== true){
      this.deleteApp(app_id);
    }
  }

  onClickCreateApp = event => {
    event.preventDefault();
    if (this.state.isLocked !== true && this.newAppName.value.length > 0){
      this.createApp(this.newAppName.value);
      this.newAppName.value = '';
    }
  }

  onKeyUpNewApp = event => {
    if(event.key==='Enter' && this.state.isLocked !== true && this.newAppName.value.length > 0){
      this.createApp(event.target.value);
      event.target.value ='';
    }
  }

  onClickShowDialog = event => {
    this.setState({
      showDialog: true,
      showColumnsFuture: this.state.showColumns.slice(0)
    });
  }

  onClickShowUploadDialog = event => {
    this.setState({
      showUploadDialog: true
    });
  }

  onClickUpdateView = cols => {
    this.setState({
      showDialog: false,
      showColumns: cols.slice(0)
    });
  }

  closeDialog = () => {
    this.setState({
      showDialog: false,
      showUploadDialog: false,
      uploadRunning: 'no',
      uploadProgress: 0,
      uploadError: 0
    });
  }

  // Leveraging await causes this to be serial.  It will take a while to upload a large csv.
  // Future improvements could allow for parallel processing.  Serial processing is simple and prevents
  // api gateway or dynamodb from getting throttled.
  processUpload = async (apps) => {
    this.setState({uploadRunning: 'yes'});
    var errors = 0;
    var log = [];
    var progress = 1;
    const statusRatio = apps.length / 100;

    for (var app in apps){


      // If last line is blank app_name will not exist.
      if (parseInt(app) === (apps.length - 1) && (apps[app].app_name === undefined || apps[app].app_name === "")){
        break;
      }

      if (app > (progress * statusRatio)) {
        progress = app/apps.length * 100;
        this.setState({uploadProgress: progress});
      }

      if (!('app_name' in apps[app]) || apps[app].app_name === undefined || apps[app].app_name === ""){
        log.push('Missing app_name attribute for row ' + app);
      } else {
        log.push('Processing row ' + app);
        log.push(JSON.stringify(apps[app]));

        var result;
        try {
          result = await this.apiUser.postApp(apps[app]);
        } catch (e) {
          log.push('Error importing application ' + apps[app].app_name + ':');

          if ('response' in e && 'data' in e.response) {
            var message;
            if (e.response.data === Object(e.response.data)) {
              message = JSON.stringify(e.response.data);
            } else {
              message = e.response.data;
            }
            log.push(message);
          } else{
            log.push('Unknown error occured');
          }

          errors = errors + 1;
          result = {};
        }
        if ('app_id' in result) {
          log.push('Created application ' + result.app_name + ' with id ' + result.app_id);
        }
      }
      log.push('\n');
    }

    for (var line in log) {
      console.log(log[line]);
    }
    this.setState({
      uploadRunning: 'complete',
      uploadProgress: 100,
      uploadErrors: errors
    })
    this.props.onClickReload()
  }

  createTableData() {
    let table = []

    // First row in table data is for new item
    let children = []
    children.push(
      <td key='input'>
        <input
          ref={(newAppName) => { this.newAppName = newAppName }}
          disabled={this.state.isLocked}
          type="text"
          className="form-control form-control-sm"
          onKeyUp={this.onKeyUpNewApp}
          placeholder='Create new application'
        />
      </td>)

    // Add an empty column for each column
    for (var i=0; i < this.state.showColumns.length-1; i++) {
      children.push(<td key={i}></td>)
    }
    children.push(<td key='action'><a href="." onClick={this.onClickCreateApp} className="pr-3">Add Application</a></td>)
    table.push(<tr key='input'>{children}</tr>)

    for (var app in this.state.filteredApps) {
      let children = []
      for (var col in this.state.showColumns) {
        if (this.state.showColumns[col] === 'wave_id') {
          var check
          for (var wave in this.state.waves) {
            if (this.state.waves[wave].wave_id === this.state.filteredApps[app][this.state.showColumns[col]]) {
              check = true
              children.push(<td key={col}>{this.state.waves[wave].wave_name}</td>)
            }
          }
          if (this.state.filteredApps[app][this.state.showColumns[col]] === undefined) {
          children.push(<td key={col}>{this.state.filteredApps[app][this.state.showColumns[col]]}</td>)
          }
        }
        else {
          children.push(<td key={col}>{this.state.filteredApps[app][this.state.showColumns[col]]}</td>)
        }
      }
      children.push(<td key='action'><a href="." disabled={this.state.isLocked} onClick={this.onClickRemoveApp(this.state.filteredApps[app].app_id)} className="pr-3 text-danger">Delete</a></td>)
      table.push(<tr key={app}>{children}</tr>)
    }
    return table
  }

  filterAppList () {
    var newAppList = [];
    for (var app in this.state.apps){
      const keys = Object.keys(this.state.apps[app])
      var wavekeys
      var waveindex
      var match = false
      for (var wave in this.state.waves) {
        if (this.state.apps[app].wave_id === this.state.waves[wave].wave_id) {
          wavekeys = Object.keys(this.state.waves[wave])
          waveindex = wave
        }
      }
      for (var i in keys) {
        if (this.state.apps[app][keys[i]].includes(this.state.searchApp)) {
          match = true
        }
      }
      for (i in wavekeys) {
        if (this.state.waves[waveindex][wavekeys[i]].includes(this.state.searchApp)) {
          match = true
        }
      }
      if (this.state.searchApp === '' || match){
        newAppList.push(this.state.apps[app])
      }

    }
    this.setState({filteredApps: newAppList})
  }

  onChangeSearch  = event => {
    this.setState({searchApp: event.target.value}, this.filterAppList);
  }

  render() {

    return (
      <div className="container-fluid rounded">

        <UserListColDialog
          showColumns={this.state.showColumns}
          showDialog={this.state.showDialog}
          onClickUpdateView={this.onClickUpdateView}
          type='app'
          closeDialog={this.closeDialog}
        />

        <UserListUploadDialog
          showDialog={this.state.showUploadDialog}
          closeDialog={this.closeDialog}
          processUpload={this.processUpload}
          uploadRunning={this.state.uploadRunning}
          uploadProgress={this.state.uploadProgress}
          uploadErrors={this.state.uploadErrors}
        />

        <div className="row">
            <div className="col-6">
              <form className="form-inline">
                <label className="pr-2" htmlFor="search">Search: </label>
                <div className="form-group">
                  <input
                    id="search"
                    type="text"
                    className="form-control form-control-sm my-2"
                    onChange={this.onChangeSearch}
                    placeholder='Enter application name'
                    style={{width: '300px'}}
                  />
                </div>
              </form>
            </div>
            <div className="col-6 pt-3">
              <i onClick={this.props.onClickReload} className="fas fa-sync-alt float-right pl-1 pr-2 onhover"></i>
              <i onClick={this.onClickShowDialog} className="fas fa-cog float-right px-2 onhover"></i>
              <i onClick={this.onClickShowUploadDialog} className="fas fa-file-upload float-right px-2 onhover"></i>
            </div>
        </div>

        <div>
          <table className={"table " + (this.state.isLoading?null:'table-hover')}>
            <thead className="thead-dark">
              <tr>
                {this.state.showColumns.map((item, index) => {
                  return (
                    <th key={index}>{item}</th>
                  )
                })}
                <th scope="col">action</th>
              </tr>
            </thead>
            <tbody>
              {this.state.isLoading?
                <tr><td><i className="fa fa-spinner fa-spin"></i> Loading Applications...</td></tr>
                :
                this.createTableData()
              }
            </tbody>
          </table>
        </div>
      </div>
    );
  }
};
