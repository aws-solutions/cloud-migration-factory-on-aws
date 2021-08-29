import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Admin from "../actions/admin";
import UserListColDialog from "../components/UserListColDialog";
import UserListUploadDialog from "../components/UserListUploadDialog";

export default class UserListservers extends Component {
  constructor(props) {
    super(props);

    this.state = {
      waves: props.waves,
      apps: props.apps,
      servers: props.servers,
      newServerAppId: 'none',
      filteredServers: props.servers,
      searchServer: '',
      isLoading: props.isLoading,
      isLocked: false,
      showColumns: ['server_name', 'app_name', 'wave_id', 'migration_status', 'replication_status'],
      schemaServer : [],
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
      isLoading: nextProps.isLoading,
      apps: nextProps.apps,
      servers: nextProps.servers,
      filteredServers: nextProps.servers
    });
  }

  async getSchema() {
    try {
      var response = await this.apiAdmin.getSchemaServer();
      this.setState({ schemaServer : response['attributes']});

      response = await this.apiAdmin.getSchemaApp();
      this.setState({ schemaApp : response['attributes']});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  async deleteServer(server_id) {
    this.setState({isLocked: true});

    try {
      await this.apiUser.deleteServer(server_id);
      this.props.updateServerList('delete', server_id)

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLocked: false});
  }

  async createServer(server_name) {
    this.setState({isLocked: true});

    var server ={
      server_name: server_name,
      app_id: this.state.newServerAppId
    }

    try {
      await this.apiUser.postServer(server);
      this.props.updateServerList('refresh', server_name)

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLocked: false});
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

  onClickRemoveServer = server_id => event => {
    event.preventDefault();
    if (this.state.isLocked !== true){
      this.deleteServer(server_id);
    }
  }

  onClickCreateServer = event => {
    event.preventDefault();
    if (this.state.isLocked !== true && this.newServerName.value.length > 0){
      this.createServer(this.newServerName.value);
      this.newServerName.value = '';
    }
  }

  onKeyUpNewServer = event => {
    if(event.key==='Enter' && this.state.isLocked !== true && this.newServerName.value.length > 0 && this.state.newServerAppId !== 'none'){
      this.createServer(event.target.value);
      event.target.value ='';
    }
  }

  onChangenewServerAppId = event => {
    this.setState({newServerAppId: event.target.value})
  }

  onClickShowDialog = event => {
    this.setState({
      showDialog: true
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

  appAttributeLookup(app_id, attribute) {
    for (var app in this.state.apps) {
      if (this.state.apps[app].app_id === app_id){
        if (attribute in this.state.apps[app]){
          if (attribute === 'wave_id') {
          for (var wave in this.state.waves) {
            if (this.state.waves[wave].wave_id === this.state.apps[app]['wave_id']) {
              return (this.state.waves[wave].wave_name) 
            }
          }
          }
          else {
          return this.state.apps[app][attribute]
          };
        }
      }
    }
    return null
  }

  // Leveraging await causes this to be serial.  It will take a while to upload a large csv.
  // Future improvements could allow for parallel processing.  Serial processing is simple and prevents
  // api gateway or dynamodb from getting throttled.
  processUpload = async (servers) => {
    this.setState({uploadRunning: 'yes'});
    var errors = 0;
    var log = [];
    var progress = 1;
    const statusRatio = servers.length / 100;

    for (var server in servers){


      // If last line is blank server_name will not exist.
      if (parseInt(server) === (servers.length - 1) && (servers[server].server_name === undefined || servers[server].server_name === "")){
        break;
      }

      if (server > (progress * statusRatio)) {
        progress = server/servers.length * 100;
        this.setState({uploadProgress: progress});
      }

      if ((!('server_name' in servers[server]) || servers[server].server_name === undefined || servers[server].server_name === "")|| (!('app_id' in servers[server]) || servers[server].app_id === undefined || servers[server].app_id === "")){
        log.push('Missing server_name or app_id attribute for row ' + server);
      } else {
        log.push('Processing row ' + server);
        log.push(JSON.stringify(servers[server]));

        var result;
        try {
          result = await this.apiUser.postServer(servers[server]);
        } catch (e) {
          log.push('Error importing server ' + servers[server].server_name + ':');

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
        if ('server_id' in result) {
          log.push('Created server ' + result.server_name + ' with id ' + result.server_id);
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
          ref={(newServerName) => { this.newServerName = newServerName }}
          disabled={this.state.isLocked}
          type="text"
          className="form-control form-control-sm"
          onKeyUp={this.onKeyUpNewServer}
          placeholder='Create new server'
        />
      </td>)

    children.push(
      <td key='app_name'>
        <select onChange={this.onChangenewServerAppId} value={this.state.newServerAppId} className="form-control form-control-sm">
          <option value='none' disabled> -- select an application -- </option>
          {this.state.apps.map((item, index) => {
            return (
              <option key={item.app_id} value={item.app_id}>{item.app_name}</option>
            )
          })}
        </select>
      </td>
    )

    // Add an empty column for each column
    for (var i=0; i < this.state.showColumns.length-2; i++) {
      children.push(<td key={i}></td>)
    }
    children.push(<td key='action'><a href="." onClick={this.onClickCreateServer} className="pr-3">Add Server</a></td>)
    table.push(<tr key='input'>{children}</tr>)

    for (var server in this.state.filteredServers) {
      let children = []
      for (var col in this.state.showColumns) {
        var value
        if (this.state.showColumns[col] in this.state.filteredServers[server]) {
          value = this.state.filteredServers[server][this.state.showColumns[col]]
        } else {
          value = this.appAttributeLookup(this.state.filteredServers[server].app_id, this.state.showColumns[col])
        }
        if (this.state.showColumns[col] !== 'tags') {
          if (value !== null) {
            value = value.toString()
          }
      }

        // This should look up the attribute type so we can support generic objects
        if(value === Object(value)){
          var tags='';
          for (i = 0; i < value.length; i++) {
            if (value[i]['value'] === undefined) {
              tags = tags + '=\n'
            }
            else {
            tags = tags + value[i]['key'] + '=' + value[i]['value'] + '\n'
            }
          }
          value = tags.slice(0, -1)
        }

        children.push(<td key={col}>{value}</td>)


      }
      children.push(<td key='action'><a href="." disabled={this.state.isLocked} onClick={this.onClickRemoveServer(this.state.filteredServers[server].server_id)} className="pr-3 text-danger">Delete</a></td>)
      table.push(<tr key={server}>{children}</tr>)
    }

    return table
  }

  filterServerList () {
    var newServerList = [];
    for (var server in this.state.servers){
      const keys = Object.keys(this.state.servers[server])
      var appkeys
      var appindex
      var waveindex
      var wavekeys
      for (var i in this.state.apps) {
        if (this.state.servers[server].app_id === this.state.apps[i].app_id) {
          appkeys = Object.keys(this.state.apps[i])
          appindex = i
          for (var wave in this.state.waves) {
            if (this.state.apps[i].wave_id === this.state.waves[wave].wave_id) {
              wavekeys = Object.keys(this.state.waves[wave])
              waveindex = wave
            }
          }
        }
      }
      var match = false
      for (i in keys) {
        if (this.state.servers[server][keys[i]].includes(this.state.searchServer)) {
          match = true
        }
      }
      for (i in appkeys) {
        if (this.state.apps[appindex][appkeys[i]].includes(this.state.searchServer)) {
          match = true
        }
      }
      for (i in wavekeys) {
        if (this.state.waves[waveindex][wavekeys[i]].includes(this.state.searchServer)) {
          match = true
        }
      }
      if (this.state.searchServer === '' || match){
        newServerList.push(this.state.servers[server])
      }
    }
    this.setState({filteredServers: newServerList})
  }

  onChangeSearch  = event => {
    this.setState({searchServer: event.target.value}, this.filterServerList);
  }

  render() {

    return (
      <div className="container-fluid rounded">

        {this.state.showDialog &&
          <UserListColDialog
            showColumns={this.state.showColumns}
            showDialog={this.state.showDialog}
            onClickUpdateView={this.onClickUpdateView}
            type='both'
            closeDialog={this.closeDialog}
          />
        }

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
                    placeholder='Enter server name'
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
                <tr><td><i className="fa fa-spinner fa-spin"></i> Loading Servers...</td></tr>
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
