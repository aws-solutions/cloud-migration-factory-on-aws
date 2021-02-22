import React, { Component } from "react";
import { Auth } from "aws-amplify";
import User from "../actions/user";
import Admin from "../actions/admin";
import UserListColDialog from "../components/UserListColDialog";

export default class UserListWaves extends Component {
  constructor(props) {
    super(props);

    this.state = {
      waves: props.waves,
      filteredWaves: props.waves,
      searchWave: '',
      isLoading: props.isLoading,
      isLocked: false,
      showColumns: ['wave_name', 'wave_id', 'wave_status'],
      schemaWave : [],
      showDialog: false
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
      waves: nextProps.waves,
      filteredWaves: nextProps.waves
    });

  }

  async getSchema() {
    try {
      var response = await this.apiAdmin.getSchemaWave();
      this.setState({ schemaWave : response['attributes']});

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
  }

  async deleteWave(wave_id) {
    this.setState({isLocked: true});

    try {
      await this.apiUser.deleteWave(wave_id);
      this.props.updateWaveList('delete', wave_id)

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLocked: false});
  }

  async createWave(wave_name) {
    this.setState({isLocked: true});

    var wave ={wave_name: wave_name}

    try {
      await this.apiUser.postWave(wave);
      this.props.updateWaveList('refresh', wave_name)

    } catch (e) {
      console.log(e);
      if ('data' in e.response) {
        this.props.showError(e.response.data);
      }
    }
    this.setState({isLocked: false});
  }

  onClickRemoveWave = wave_id => event => {
    event.preventDefault();
    if (this.state.isLocked !== true){
      this.deleteWave(wave_id);
    }
  }

  onClickCreateWave = event => {
    event.preventDefault();
    if (this.state.isLocked !== true && this.newWaveName.value.length > 0){
      this.createWave(this.newWaveName.value);
      this.newWaveName.value = '';
    }
  }

  onKeyUpNewWave = event => {
    if(event.key==='Enter' && this.state.isLocked !== true && this.newWaveName.value.length > 0){
      this.createWave(event.target.value);
      event.target.value ='';
    }
  }

  onClickShowDialog = event => {
    this.setState({
      showDialog: true,
      showColumnsFuture: this.state.showColumns.slice(0)
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
      showDialog: false
    });
  }

  createTableData() {
    let table = []

    // First row in table data is for new item
    let children = []
    children.push(
      <td key='input'>
        <input
          ref={(newWaveName) => { this.newWaveName = newWaveName }}
          disabled={this.state.isLocked}
          type="text"
          className="form-control form-control-sm"
          onKeyUp={this.onKeyUpNewWave}
          placeholder='Create new wave'
        />
      </td>)

    // Add an empty column for each column
    for (var i=0; i < this.state.showColumns.length-1; i++) {
      children.push(<td key={i}></td>)
    }
    children.push(<td key='action'><a href="." onClick={this.onClickCreateWave} className="pr-3">Add Wave</a></td>)
    table.push(<tr key='input'>{children}</tr>)

    for (var wave in this.state.filteredWaves) {
      let children = []
      for (var col in this.state.showColumns) {
          children.push(<td key={col}>{this.state.filteredWaves[wave][this.state.showColumns[col]]}</td>)
      }
      children.push(<td key='action'><a href="." disabled={this.state.isLocked} onClick={this.onClickRemoveWave(this.state.filteredWaves[wave].wave_id)} className="pr-3 text-danger">Delete</a></td>)
      table.push(<tr key={wave}>{children}</tr>)
    }
    return table
  }

  filterWaveList () {
    var newWaveList = [];
    for (var wave in this.state.waves){
      const keys = Object.keys(this.state.waves[wave])
      var match = false
      for (var i in keys) {
        if (this.state.waves[wave][keys[i]].includes(this.state.searchWave)) {
          match = true
        }
      }
      if (this.state.searchWave === '' || match){
        newWaveList.push(this.state.waves[wave])
      }

    }
    this.setState({filteredWaves: newWaveList})
  }

  onChangeSearch  = event => {
    this.setState({searchWave: event.target.value}, this.filterWaveList);
  }

  render() {

    return (
      <div className="container-fluid rounded">
        
        <UserListColDialog
          showColumns={this.state.showColumns}
          showDialog={this.state.showDialog}
          onClickUpdateView={this.onClickUpdateView}
          type='wave'
          closeDialog={this.closeDialog}
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
                    placeholder='Enter Wave name'
                    style={{width: '300px'}}
                  />
                </div>
              </form>
            </div>
            <div className="col-6 pt-3">
              <i onClick={this.props.onClickReload} className="fas fa-sync-alt float-right pl-1 pr-2 onhover"></i>
              <i onClick={this.onClickShowDialog} className="fas fa-cog float-right px-2 onhover"></i>
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
                <tr><td><i className="fa fa-spinner fa-spin"></i> Loading Waves...</td></tr>
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
